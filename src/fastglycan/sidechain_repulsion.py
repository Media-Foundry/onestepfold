"""Topology-defined variable-distance pairs for fixed-pose sidechain fitting."""
import numpy as np
import torch
from .anchored_tail import tail_penalty


def sidechain_pair_mask(adapter, atom_names, pairs):
    """Mark pairs separated by at least one allowed rotation, excluding its axis.

    Pairs on the same rigid side, or involving an axis endpoint and the rotating
    side, have invariant distance for that angle. The union over all angles is a
    conservative structural support, not a claim of nonzero local sensitivity.
    """
    names=np.asarray(atom_names);pairs=np.asarray(pairs,dtype=int)
    if pairs.ndim!=2 or pairs.shape[1]!=2 or (len(pairs) and (pairs.min()<0 or pairs.max()>=len(names))):
        raise ValueError('invalid pair inventory')
    result=np.zeros(len(pairs),bool)
    for group in adapter.groups:
        nn=names[group.indices[0].cpu().numpy()]
        for rotation in group.rotations:
            if set(nn[list(rotation.moving)]).intersection({'N','CA','C','O','OXT'}):continue
            for indices in group.indices.cpu().numpy():
                state=np.zeros(len(names),np.int8);state[indices[list(rotation.moving)]]=1
                state[indices[[rotation.parent,rotation.child]]]=2
                a,b=state[pairs[:,0]],state[pairs[:,1]]
                result|=((a==1)&(b==0))|((a==0)&(b==1))
    return result


def sidechain_repulsion(x,pairs,radii):
    """Reuse frozen mean/tail shapes, weight one, over variable-distance pairs."""
    if not len(pairs):return x.sum()*0,dict(mean=x.sum()*0,tail=x.sum()*0)
    depth=radii[pairs[:,0]]+radii[pairs[:,1]]-torch.linalg.vector_norm(x[pairs[:,0]]-x[pairs[:,1]],dim=-1)
    mean=torch.relu(depth-1.5).square().sum()/len(x)/.25
    tail=tail_penalty(x,pairs,radii,k=16)
    return mean+tail,dict(mean=mean,tail=tail)
