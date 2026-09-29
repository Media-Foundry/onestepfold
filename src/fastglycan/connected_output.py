"""Fixed-graph all-trans chain reconstruction; no optimizer or learned weights.

Local chemical reconstruction is reused from ArticulatedOutput. Sequential global
pose drift and long-range clashes are deliberately measured, not hidden by fitting.
"""
import numpy as np
import torch
from torch import nn
from .articulated_output import ArticulatedOutput, _frame


def unit(x):
    norm = torch.linalg.vector_norm(x, dim=-1, keepdim=True)
    if bool((norm < 1e-6).any()):
        raise ValueError('degenerate connected geometry')
    return x / norm


def phase(a, b, c, d):
    axis = unit(c-b)
    u = a-b; u = unit(u-(u*axis).sum(-1, keepdim=True)*axis)
    v = d-c; v = unit(v-(v*axis).sum(-1, keepdim=True)*axis)
    return (u*v).sum(-1), (torch.linalg.cross(u, v)*axis).sum(-1)


def place(a, b, c, length, cosine, torsion):
    axis = unit(c-b)
    u = a-b; u = unit(u-(u*axis).sum(-1, keepdim=True)*axis)
    co, si = torsion
    radial = co[..., None]*u + si[..., None]*torch.linalg.cross(axis, u)
    return c + length*(-cosine*axis + torch.sqrt(1-cosine**2)*radial)


class ConnectedOutput(nn.Module):
    def __init__(self, reference, names, residues, sequence, variants):
        super().__init__()
        if any(n == 'OXT' and r != len(sequence) for n, r in zip(names, residues)):
            raise ValueError('OXT is supported only on the terminal residue')
        self.local = ArticulatedOutput(reference, names, residues, sequence, variants)
        self.indices = [np.flatnonzero(np.asarray(residues)==i+1).tolist() for i in range(len(sequence))]
        self.anchors = [[indices[list(np.asarray(names)[indices]).index(n)] for n in ('N','CA','C','O')]
                        for indices in self.indices]
        self.sequence = sequence
        ref = torch.as_tensor(reference, dtype=torch.float64)
        def length(a,b): return torch.linalg.vector_norm(ref[a]-ref[b])
        def cosine(a,b,c): return (unit(ref[a]-ref[b])*unit(ref[c]-ref[b])).sum()
        self.register_buffer('geometry', torch.stack([torch.stack((length(n,ca),length(ca,c),
            cosine(n,ca,c),length(c,o),cosine(ca,c,o))) for n,ca,c,o in self.anchors]))

    def forward(self, raw):
        if raw.ndim != 2 or not torch.isfinite(raw).all():
            raise ValueError('expected one finite fixed-graph structure')
        # Reject instead of inheriting non-equivariant fallbacks.
        for n,ca,c,o in self.anchors:
            unit(raw[c]-raw[ca]); unit(torch.linalg.cross(raw[n]-raw[ca],raw[c]-raw[ca]))
        local = self.local(raw)
        if bool(local['fallback_counts'].any()):
            raise ValueError('degenerate local projection')
        projected = local['coordinate']
        first = self.anchors[0]
        backbone = [projected[first[:3]]]
        one = raw.new_tensor(1.); zero = raw.new_tensor(0.)
        for i in range(1,len(self.anchors)):
            pn,pa,pc,_ = self.anchors[i-1]; n,ca,c,_ = self.anchors[i]
            prev = backbone[-1]
            psi = phase(raw[pn],raw[pa],raw[pc],raw[n])
            phi = phase(raw[pc],raw[n],raw[ca],raw[c])
            xn = place(*prev,raw.new_tensor(1.341 if self.sequence[i]=='P' else 1.329),raw.new_tensor(-.4473),psi)
            xa = place(prev[1],prev[2],xn,self.geometry[i,0],raw.new_tensor(-.5203),(-one,zero))
            xc = place(prev[2],xn,xa,self.geometry[i,1],self.geometry[i,2],phi)
            backbone.append(torch.stack((xn,xa,xc)))
        pieces=[];order=[]
        for i,indices in enumerate(self.indices):
            n,ca,c,o = self.anchors[i]
            old_frame,_,_ = _frame(projected,n,ca,c)
            new_frame,_,_ = _frame(backbone[i],0,1,2)
            moved = (projected[indices]-projected[ca]) @ old_frame @ new_frame.T + backbone[i][1]
            if i+1<len(backbone):
                xo=place(backbone[i+1][0],backbone[i][1],backbone[i][2],self.geometry[i,3],self.geometry[i,4],(-one,zero))
                selector = torch.tensor([j==o for j in indices],device=raw.device)[:,None]
                moved=torch.where(selector,xo,moved)
            pieces.append(moved);order.extend(indices)
        return torch.cat(pieces)[torch.argsort(torch.tensor(order,device=raw.device))]
