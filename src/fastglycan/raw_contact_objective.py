"""Frozen-raw contact preservation for a diagnostic coordinate solver."""
import torch
from torch import nn

from .calibrated_connection_objective import CalibratedConnectionObjective


class RawContactPreservation(nn.Module):
    """One fixed raw-only pair graph, not a soft-sequence graph construction.

    Only native allowed pairs with residue separation>=5 and raw distance in
    [4,15) Angstrom enter. Atom-neighbour normalization avoids uniform-pair bias.
    Raw tensors are detached; only output coordinates receive gradients here.
    """
    def __init__(self, raw, residues, allowed_pairs):
        super().__init__()
        target=raw.detach()
        residues=torch.as_tensor(residues,device=raw.device,dtype=torch.long)
        pairs=allowed_pairs.detach().to(device=raw.device,dtype=torch.long)
        if raw.ndim!=2 or raw.shape[1]!=3 or residues.shape!=(len(raw),):
            raise ValueError('invalid coordinate/residue shape')
        if not torch.isfinite(target).all() or pairs.ndim!=2 or pairs.shape[1]!=2:
            raise ValueError('invalid coordinates/pairs')
        if len(pairs) and (bool((pairs<0).any()) or bool((pairs>=len(raw)).any()) or bool((pairs[:,0]>=pairs[:,1]).any())):
            raise ValueError('pairs must be valid, unique-oriented i<j')
        if len(torch.unique(pairs,dim=0))!=len(pairs):raise ValueError('duplicate pairs')
        distances=(target[pairs[:,0]]-target[pairs[:,1]]).norm(dim=-1)
        keep=((residues[pairs[:,0]]-residues[pairs[:,1]]).abs()>=5)&(distances>=4)&(distances<15)
        pairs=pairs[keep];distances=distances[keep]
        degree=torch.bincount(pairs.flatten(),minlength=len(raw));active=int((degree>0).sum())
        weights=(degree[pairs[:,0]].to(raw).reciprocal()+degree[pairs[:,1]].to(raw).reciprocal())/active if active else raw.new_empty(0)
        self.register_buffer('contact_pairs',pairs)
        self.register_buffer('contact_target',distances.clone())
        self.register_buffer('contact_weights',weights)
        self.register_buffer('contact_degree',degree)

    def forward(self, coordinates):
        pairs=self.contact_pairs
        if not len(pairs):return coordinates.sum()*0
        error=(coordinates[pairs[:,0]]-coordinates[pairs[:,1]]).norm(dim=-1)-self.contact_target
        # delta=1 Angstrom; stable equivalent of 2*(sqrt(1+error**2)-1).
        penalty=2*error.square()/(torch.sqrt(1+error.square())+1)
        return (self.contact_weights*penalty).sum()


class RawContactObjective(CalibratedConnectionObjective):
    """Add weight-one raw-contact cost outside the chemistry rho multiplier."""
    def __init__(self, raw, anchors, sequence, pairs, radii, calibration, residues):
        super().__init__(raw,anchors,sequence,pairs,radii,calibration)
        self.contacts=RawContactPreservation(raw,residues,pairs)

    def forward(self, x, values, rho):
        loss,terms=super().forward(x,values,rho)
        contact=self.contacts(x)
        return loss+contact,dict(terms,raw_contact=contact)
