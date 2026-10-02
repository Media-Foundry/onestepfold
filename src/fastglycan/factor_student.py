"""WT-only discrete-query global node propagator with channel-specific pair factors."""
import math
import numpy as np
import torch
from torch import nn
from scipy.spatial import cKDTree


class FactorNodeBlock(nn.Module):
    def __init__(self,width=128,heads=4):
        super().__init__();self.heads=heads;self.width=width
        self.norm=nn.LayerNorm(width);self.qkv=nn.Linear(width,3*width);self.output=nn.Linear(width,width)
        self.ff=nn.Sequential(nn.LayerNorm(width),nn.Linear(width,4*width),nn.GELU(),nn.Linear(4*width,width))

    def forward(self,h,pair_bias):
        b,l,d=h.shape;q,k,v=self.qkv(self.norm(h)).reshape(b,l,3,self.heads,d//self.heads).permute(2,0,3,1,4).unbind(0)
        p=torch.softmax((q@k.transpose(-1,-2))/math.sqrt(d//self.heads)+pair_bias[None],dim=-1)
        h=h+self.output((p@v).transpose(1,2).reshape(b,l,d));return h+self.ff(h)


class FactorStudent(nn.Module):
    """No target states enter forward. WT AA query has exactly zero response.

    Shared generator, channel-specific U/V. Dense target s belongs solely to the
    explicit oracle-s decoder experiment, never to this predictor's inputs.
    """
    def __init__(self,single_channels=384,pair_channels=128,rank=32,width=128):
        super().__init__();self.rank=rank;self.pair_channels=pair_channels
        self.single=nn.Sequential(nn.LayerNorm(single_channels),nn.Linear(single_channels,width))
        self.site_pair=nn.Sequential(nn.LayerNorm(2*pair_channels),nn.Linear(2*pair_channels,width))
        self.global_pair=nn.Sequential(nn.LayerNorm(2*pair_channels),nn.Linear(2*pair_channels,width))
        self.query=nn.Embedding(20,width);self.offset=nn.Embedding(65,width);self.mix=nn.Sequential(nn.LayerNorm(width),nn.Linear(width,width),nn.GELU())
        self.bias=nn.Sequential(nn.LayerNorm(pair_channels),nn.Linear(pair_channels,4,bias=False))
        self.blocks=nn.ModuleList([FactorNodeBlock(width,4) for _ in range(2)])
        self.u=nn.Linear(width,pair_channels*rank);self.v=nn.Linear(width,pair_channels*rank)
        nn.init.normal_(self.u.weight,std=.02);nn.init.zeros_(self.u.bias);nn.init.zeros_(self.v.weight);nn.init.zeros_(self.v.bias)

    def forward(self,wt_s,wt_z,position,wt_aa,candidate_aa):
        if wt_s.ndim!=2 or wt_z.shape[:2]!=(len(wt_s),len(wt_s)):raise ValueError('WT context shape mismatch')
        aa=torch.as_tensor(candidate_aa,device=wt_s.device,dtype=torch.long).reshape(-1)
        if not 0<=position<len(wt_s) or not 0<=wt_aa<20 or torch.any((aa<0)|(aa>=20)):raise ValueError('invalid discrete query')
        p=torch.arange(len(wt_s),device=wt_s.device);offset=(p-position).clamp(-32,32)+32
        s=self.single(wt_s);context=s+s[position]+self.site_pair(torch.cat([wt_z[position],wt_z[:,position]],-1))+self.global_pair(torch.cat([wt_z.mean(0),wt_z.mean(1)],-1))+self.offset(offset)
        q=self.query(aa)-self.query.weight[wt_aa];h=self.mix(context[None]+q[:,None]);bias=self.bias(wt_z).permute(2,0,1)
        for block in self.blocks:h=block(h,bias)
        shape=(len(aa),len(wt_s),self.pair_channels,self.rank)
        u=self.u(h).reshape(shape);v=self.v(h).reshape(shape)*(aa!=wt_aa)[:,None,None,None]
        return u,v


def expand_pair_factors(u,v):
    if u.shape!=v.shape or u.ndim!=4:raise ValueError('expected matching [candidate,L,C,R] factors')
    return torch.einsum('ajcr,akcr->ajkc',u,v)/math.sqrt(u.shape[-1])


def factor_geometry_penalties(x,labels):
    """Same checked centres/exclusions as evaluation; penalties are not guarantees."""
    zero=x[:0].sum();centres=labels['centres'].to(x.device);ref=labels['volumes'].to(x)
    if len(centres):
        a,b,c,d=centres.T;vol=(torch.linalg.cross(x[b]-x[a],x[c]-x[a],dim=-1)*(x[d]-x[a])).sum(-1)
        chirality=torch.relu(.2-vol*ref.sign()/ref.abs()).square().mean()
    else:chirality=zero
    local=cKDTree(x.detach().cpu().double().numpy()).query_pairs(4.,output_type='ndarray');local=local[~np.isin(local[:,0]*len(x)+local[:,1],labels['excluded'])]
    if len(local):
        p=torch.as_tensor(local,device=x.device);r=labels['radii'].to(x);depth=r[p[:,0]]+r[p[:,1]]-torch.linalg.vector_norm(x[p[:,0]]-x[p[:,1]],dim=-1)
        k=min(16,labels['allowed_pair_count']);clash=torch.relu(depth-1.5).square().sum()/len(x)+(torch.relu(torch.topk(depth,min(k,len(depth))).values-1.9)/.1).square().sum()/k
    else:clash=zero
    return clash,chirality
