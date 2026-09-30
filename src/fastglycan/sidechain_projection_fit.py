"""Bounded raw-coordinate sidechain fit with immutable local backbone and pose."""
import numpy as np
import torch

from .anchored_geometry import PoseVariables
from .sidechain_repulsion import sidechain_pair_mask, sidechain_repulsion


def fit_sidechain_projection(adapter, raw, atom_names, *, max_iter=60, max_eval=90, collision_pairs=None, collision_radii=None):
    """Fit legal bridge angles only; not a differentiable optimizer layer.

    The target is the raw prediction, never experimental GT. Return final iterate
    without candidate selection. N/CA/C/O/OXT and all nonmobile atoms remain exactly
    at the initial local construction; full zero-pose angle vectors are retained
    for independent pose replay and a possible later joint-start experiment.
    """
    names=np.asarray(atom_names)
    if raw.shape!=(adapter.atom_count,3) or names.shape!=(adapter.atom_count,):
        raise ValueError('coordinate/atom inventory mismatch')
    if not torch.isfinite(raw).all():raise ValueError('nonfinite input')
    if max_iter<1 or max_eval<max_iter:raise ValueError('invalid optimization budget')
    target=raw.detach().clone();pose=PoseVariables(adapter,target)
    initial=pose.initial.detach().clone();masks=[];mobile=torch.zeros(len(raw),dtype=torch.bool,device=raw.device)
    eligible=[]
    for group,q in zip(pose.groups,pose.variables,strict=True):
        mask=torch.zeros_like(q);local_names=names[group.indices[0].cpu().numpy()]
        selected=[]
        for j,rotation in enumerate(group.rotations):
            if not set(local_names[list(rotation.moving)]).intersection({'N','CA','C','O','OXT'}):
                mask[:,6+j]=1;mobile[group.indices[:,list(rotation.moving)].flatten()]=True;selected.append(j)
        masks.append(mask);eligible.append(selected)
    side=torch.tensor(~np.isin(names,['N','CA','C','O','OXT']),device=raw.device)
    def coordinates():
        x=pose.coordinates(tuple(q*m for q,m in zip(pose.variables,masks,strict=True)))
        return torch.where(mobile[:,None],x,initial)
    def mse(x):
        return (x[side]-target[side]).square().sum(-1).mean() if bool(side.any()) else x.sum()*0
    coupled=collision_pairs is not None
    if coupled != (collision_radii is not None):raise ValueError('pairs and radii must be provided together')
    pair_mask=None
    if coupled:
        pair_mask=sidechain_pair_mask(adapter,names,collision_pairs.detach().cpu().numpy())
        active_pairs=collision_pairs.to(device=raw.device,dtype=torch.long)[torch.as_tensor(pair_mask,device=raw.device)]
        radii=collision_radii.to(raw)
        if radii.shape!=(len(raw),) or not torch.isfinite(radii).all() or not bool((radii>0).all()):raise ValueError('invalid collision radii')
    def objective(x):
        return mse(x)+sidechain_repulsion(x,active_pairs,radii)[0] if coupled else mse(x)
    start_mse=float(mse(initial));calls=0;iterations=0;gradient_norm=0.
    initial_collision=None
    if coupled:
        _,terms=sidechain_repulsion(initial,active_pairs,radii)
        initial_collision={k:float(v) for k,v in terms.items()}

    if bool(mobile.any()):
        optimizer=torch.optim.LBFGS(pose.parameters(),lr=1.,max_iter=max_iter,max_eval=max_eval,
            history_size=20,line_search_fn='strong_wolfe',tolerance_grad=1e-8,tolerance_change=1e-12)
        def closure():
            nonlocal calls
            optimizer.zero_grad();loss=objective(coordinates())
            if not torch.isfinite(loss):raise FloatingPointError('nonfinite fit objective')
            loss.backward()
            if any(q.grad is None or not torch.isfinite(q.grad).all() for q in pose.parameters()):
                raise FloatingPointError('nonfinite or missing fit gradient')
            calls+=1;return loss
        optimizer.step(closure)
        final=coordinates();loss=objective(final)
        grad=torch.autograd.grad(loss,tuple(pose.parameters()))
        if not all(torch.isfinite(g).all() for g in grad):raise FloatingPointError('nonfinite final gradient')
        gradient_norm=float(torch.cat([g.flatten() for g in grad]).norm())
        iterations=int(optimizer.state[next(pose.parameters())].get('n_iter',0))
    else:final=initial;loss=objective(final)
    if not torch.isfinite(final).all():raise FloatingPointError('nonfinite final coordinates')
    values=tuple((q*m).detach().clone() for q,m in zip(pose.variables,masks,strict=True))
    assert all(torch.count_nonzero(q[m==0])==0 for q,m in zip(values,masks,strict=True))
    assert torch.equal(final[~mobile],initial[~mobile])
    result=dict(initial=initial,coordinates=final.detach(),values=values,
        masks=tuple(m.detach().clone() for m in masks),mobile=mobile,eligible=eligible,
        initial_mse=start_mse,final_mse=float(mse(final).detach()),iterations=iterations,
        closure_calls=calls,final_gradient_norm=gradient_norm,eligible_dof=sum(int(m.sum()) for m in masks),
        improved=float(mse(final).detach())<start_mse)
    if coupled:
        _,terms=sidechain_repulsion(final,active_pairs,radii)
        result['collision_pair_mask']=pair_mask
        result['collision']=dict(initial=initial_collision,final={k:float(v.detach()) for k,v in terms.items()},
            pairs=int(pair_mask.sum()),excluded_pairs=int((~pair_mask).sum()),weight=1.,
            initial_objective=start_mse+sum(initial_collision.values()),final_objective=float(loss.detach()))
    return result
