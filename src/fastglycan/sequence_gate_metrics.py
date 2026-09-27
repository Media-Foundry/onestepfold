"""Numerical and optimization gates. A failed gate stays failed in the report."""
from __future__ import annotations
import torch


def directional_finite_differences(objective, logits, *, directions=3,
                                  steps=(.3,.1,.03,.01,.003), seed=731,
                                  relative_tolerance=.05, absolute_tolerance=1e-6):
    q=logits.detach().clone().requires_grad_(True)
    value=objective(q)
    gradient,=torch.autograd.grad(value,q)
    repeat=logits.detach().clone().requires_grad_(True)
    repeated,=torch.autograd.grad(objective(repeat),repeat)
    generator=torch.Generator(device=q.device).manual_seed(seed)
    records=[]
    for _ in range(directions):
        v=torch.randn(q.shape,device=q.device,dtype=q.dtype,generator=generator)
        # Logit shift is a softmax null direction; remove it from each residue.
        v=v-v.mean(-1,keepdim=True);v=v/v.norm()
        analytic=(gradient.double()*v.double()).sum().item()
        rows=[]
        with torch.no_grad():
            for h in steps:
                plus=objective(q+h*v).double().item()
                minus=objective(q-h*v).double().item()
                estimate=(plus-minus)/(2*h)
                error=abs(estimate-analytic)
                scale=max(abs(estimate),abs(analytic))
                rows.append(dict(h=h,analytic=analytic,finite_difference=estimate,
                                 absolute_error=error,relative_error=error/max(scale,1e-12),
                                 pass_tolerance=error <= absolute_tolerance+relative_tolerance*scale))
        # Require two neighboring h values, not a lucky best-of-h match.
        plateau=any(a['pass_tolerance'] and b['pass_tolerance'] for a,b in zip(rows,rows[1:]))
        records.append(dict(rows=rows,plateau_pass=plateau))
    finite=bool(torch.isfinite(gradient).all())
    repeat_error=float((gradient-repeated).abs().max())
    report=dict(finite=finite,norm=float(gradient.norm()),max_abs=float(gradient.abs().max()),
                zero_fraction=float((gradient==0).float().mean()),repeat_max_abs=repeat_error,
                directions=records,passed=finite and gradient.norm().item()>0 and repeat_error==0
                and all(r['plateau_pass'] for r in records))
    return gradient,report


def contact_objective(coordinates, ca_indices):
    """Monomer contact proxy with chain/clash guards; not interface or binding loss."""
    ca=coordinates[0,ca_indices]
    distance=torch.cdist(ca,ca)
    idx=torch.arange(len(ca),device=ca.device)
    nonlocal_pair=(idx[:,None]-idx[None,:]).abs()>8
    nonadjacent=(idx[:,None]-idx[None,:]).abs()>1
    contacts=torch.sigmoid((8-distance)/1.5)[nonlocal_pair].double().mean()
    clashes=torch.relu(3-distance[nonadjacent]).square().double().mean()
    chain=(torch.linalg.vector_norm(ca[1:]-ca[:-1],dim=-1)-3.8).square().double().mean()
    loss=-contacts+clashes+0.1*chain
    return loss,dict(contact=float(contacts.detach()),clash=float(clashes.detach()),chain=float(chain.detach()))


def atom_geometry(coordinates, atoms, reference_positions):
    """CPU geometric diagnostics against native bond topology/reference conformers."""
    import numpy as np
    x=np.asarray(coordinates,dtype=np.float64)
    if x.ndim==3:x=x[0]
    reference=np.asarray(reference_positions,dtype=np.float64)
    bonds=atoms.bonds.as_array()[:,:2].astype(int)
    length=np.linalg.norm(x[bonds[:,0]]-x[bonds[:,1]],axis=-1)
    same_res=atoms.res_id[bonds[:,0]]==atoms.res_id[bonds[:,1]]
    reference_length=np.linalg.norm(reference[bonds[:,0]]-reference[bonds[:,1]],axis=-1)
    cn=np.array([{str(atoms.atom_name[i]),str(atoms.atom_name[j])}=={'C','N'} for i,j in bonds]) & ~same_res
    ideal=np.where(same_res,reference_length,1.33)
    valid=same_res|cn
    lookup={(int(r),str(n)):i for i,(r,n) in enumerate(zip(atoms.res_id,atoms.atom_name))}
    chirality=[]
    for residue in np.unique(atoms.res_id):
        names=['CA','N','C','CB']
        if not all((int(residue),n) in lookup for n in names):continue
        ca,n,c,cb=[lookup[(int(residue),v)] for v in names]
        def signed(y):return float(np.dot(np.cross(y[n]-y[ca],y[c]-y[ca]),y[cb]-y[ca]))
        ref=signed(reference);observed=signed(x)
        if abs(ref)>1e-4:chirality.append(observed*ref>0)
    dist=np.linalg.norm(x[:,None]-x[None,:],axis=-1)
    nonbond=np.triu(np.ones(dist.shape,dtype=bool),1)
    nonbond[bonds[:,0],bonds[:,1]]=False;nonbond[bonds[:,1],bonds[:,0]]=False
    return dict(bond_rmse=float(np.sqrt(np.mean((length[valid]-ideal[valid])**2))),
                cn_mae=float(np.mean(abs(length[cn]-1.33))) if cn.any() else None,
                chirality_fraction=float(np.mean(chirality)) if chirality else None,
                heavy_atom_pairs_below_1A=int(np.sum((dist<1)&nonbond)))
