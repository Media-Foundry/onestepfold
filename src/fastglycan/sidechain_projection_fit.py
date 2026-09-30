"""Bounded raw-coordinate sidechain fit with immutable local backbone and pose."""
import numpy as np
import torch

from .anchored_geometry import PoseVariables


def fit_sidechain_projection(adapter, raw, atom_names, *, max_iter=60, max_eval=90):
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
    def objective(x):
        return (x[side]-target[side]).square().sum(-1).mean() if bool(side.any()) else x.sum()*0
    start_mse=float(objective(initial));calls=0;iterations=0;gradient_norm=0.
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
    return dict(initial=initial,coordinates=final.detach(),values=values,
        masks=tuple(m.detach().clone() for m in masks),mobile=mobile,eligible=eligible,
        initial_mse=start_mse,final_mse=float(loss.detach()),iterations=iterations,
        closure_calls=calls,final_gradient_norm=gradient_norm,eligible_dof=sum(int(m.sum()) for m in masks),
        improved=float(loss.detach())<start_mse)
