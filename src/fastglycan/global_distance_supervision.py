"""Observed experimental long-separation CA distances, with no spatial cutoff."""
import numpy as np
import torch
import torch.nn.functional as F


MINIMUM_SEQUENCE_SEPARATION = 24
HUBER_BETA_ANGSTROM = 10.0


def build_global_ca_distance_labels(mapping):
    """Mask before distance construction; labels stay detached on CPU."""
    xyz=np.asarray(mapping['coordinates'],dtype=np.float64)
    mask=np.asarray(mapping['mask']);names=np.asarray(mapping['atom_names'])
    residues=np.asarray(mapping['residue_ids']);chains=np.asarray(mapping['chain_ids'])
    n=len(xyz)
    if xyz.shape!=(n,3) or any(a.shape!=(n,) for a in [mask,names,residues,chains]):
        raise ValueError('inconsistent inventory shapes')
    if mask.dtype!=np.bool_ or not np.issubdtype(residues.dtype,np.integer):
        raise ValueError('invalid mask or residue IDs')
    selected=np.flatnonzero(mask&(names=='CA'))
    identities=list(zip(chains[selected].tolist(),residues[selected].tolist()))
    if len(set(identities))!=len(identities) or np.any(residues[selected]<1):
        raise ValueError('duplicate or invalid observed CA identity')
    if not np.isfinite(xyz[selected]).all():raise ValueError('nonfinite observed CA')
    i,j=np.triu_indices(len(selected),1);a,b=selected[i],selected[j]
    keep=(chains[a]==chains[b])&(np.abs(residues[a]-residues[b])>=MINIMUM_SEQUENCE_SEPARATION)
    pairs=np.column_stack((a[keep],b[keep])).astype(np.int64)
    distance=np.linalg.norm(xyz[pairs[:,0]]-xyz[pairs[:,1]],axis=1)
    return dict(pairs=torch.from_numpy(pairs),target_distance=torch.from_numpy(distance),
                ca_indices=torch.from_numpy(selected),atoms=n,minimum_sequence_separation=MINIMUM_SEQUENCE_SEPARATION,
                huber_beta_angstrom=HUBER_BETA_ANGSTROM)


def global_ca_distance_loss(prediction, labels):
    """Mean smooth-L1 distance error in Å, beta=10 Å; finite tail gradients.

    No external alignment or upper distance cutoff. Empty support contributes a
    connected zero without reading invalid unobserved coordinates. Pair chunking
    changes memory use only; reduction divides by the total number of pairs.
    """
    if prediction.shape!=(labels['atoms'],3) or not prediction.is_floating_point():
        raise ValueError('invalid prediction shape or dtype')
    pairs=labels['pairs'].to(prediction.device);target=labels['target_distance'].to(prediction)
    if pairs.ndim!=2 or pairs.shape[1]!=2 or target.shape!=(len(pairs),):
        raise ValueError('invalid pair labels')
    if labels['huber_beta_angstrom']!=HUBER_BETA_ANGSTROM or labels['minimum_sequence_separation']!=MINIMUM_SEQUENCE_SEPARATION:
        raise ValueError('unlocked global-distance definition')
    total=prediction[:0].sum()
    for first in range(0,len(pairs),65536):
        p=pairs[first:first+65536];delta=prediction[p[:,0]]-prediction[p[:,1]]
        if not torch.isfinite(delta).all():raise ValueError('nonfinite scored prediction')
        distance=torch.linalg.vector_norm(delta,dim=-1)
        total=total+F.smooth_l1_loss(distance,target[first:first+65536],beta=HUBER_BETA_ANGSTROM,reduction='sum')
    return total/len(pairs) if len(pairs) else total
