"""Bounded worst-pair penalty; original mean-repulsion objective is unchanged."""
import torch
from .anchored_geometry import JointObjective


def tail_penalty(x,pairs,radii,k=16,chunk_size=65536):
    if k<1 or chunk_size<1:raise ValueError('positive k and chunk size required')
    largest=x.new_empty(0)
    for pair in pairs.split(chunk_size):
        depth=radii[pair[:,0]]+radii[pair[:,1]]-(x[pair[:,0]]-x[pair[:,1]]).norm(dim=-1)
        candidates=torch.cat((largest,depth))
        largest=torch.topk(candidates,min(k,len(candidates)),sorted=False).values
    if not len(largest):return x.sum()*0
    return (torch.relu(largest-1.9)/.1).square().mean()


class TailObjective(JointObjective):
    def forward(self,x,values,rho):
        loss,terms=super().forward(x,values,rho)
        tail=tail_penalty(x,self.pairs,self.radii)
        return loss+rho*tail,dict(terms,tail=tail)
