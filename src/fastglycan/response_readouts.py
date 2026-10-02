"""Shared nonlinear readouts and a free-node diagnostic, with no target inputs."""
import copy
import torch
from torch import nn
from fastglycan.deep_response_student import DeepResponseStudent
from fastglycan.factor_student import expand_pair_factors


class FreeNodeReadout(nn.Module):
    """One-site diagnostic: free candidate/node states, original shared U/V heads."""
    def __init__(self,base,wt_s,wt_z,position,wt_aa):
        super().__init__();self.position=position;self.wt_aa=wt_aa
        self.rank=base.rank;self.channels=base.pair_channels
        with torch.no_grad():h,_=base.node_response(wt_s,wt_z,position,wt_aa,list(range(20)))
        self.hidden=nn.Parameter(h.detach().clone());self.u=copy.deepcopy(base.u);self.v=copy.deepcopy(base.v)

    def forward(self,wt_s,wt_z,position,wt_aa,candidate_aa):
        if position!=self.position or wt_aa!=self.wt_aa or len(wt_s)!=self.hidden.shape[1]:raise ValueError('free hidden belongs to one site only')
        aa=torch.as_tensor(candidate_aa,device=self.hidden.device,dtype=torch.long);h=self.hidden[aa];shape=(*h.shape[:2],self.channels,self.rank)
        u=self.u(h).reshape(shape);v=self.v(h).reshape(shape)*(aa!=wt_aa)[:,None,None,None]
        return expand_pair_factors(u,v)


class NonlinearResponseReadout(DeepResponseStudent):
    """Same large WT encoder, length-independent pair or channel-query readout."""
    def __init__(self,kind='pair',single_channels=384,pair_channels=128,rank=32,
                 readout_width=128):
        if kind not in ('pair','channel'):raise ValueError('unknown shared readout')
        super().__init__(size='large',content=False,single_channels=single_channels,pair_channels=pair_channels,rank=rank)
        self.kind=kind;del self.u,self.v
        width=256;d=readout_width
        self.aa_readout=nn.Linear(width,d,bias=False)
        if kind=='pair':
            self.left=nn.Linear(width,d);self.right=nn.Linear(width,d,bias=False)
            self.pair_content=nn.Sequential(nn.LayerNorm(pair_channels),nn.Linear(pair_channels,d,bias=False))
            self.readout=nn.Sequential(nn.GELU(),nn.Linear(d,d),nn.GELU(),nn.Linear(d,pair_channels))
            nn.init.zeros_(self.readout[-1].weight);nn.init.zeros_(self.readout[-1].bias)
        else:
            self.node=nn.Linear(width,d);self.channel=nn.Embedding(pair_channels,d)
            self.readout=nn.Sequential(nn.GELU(),nn.Linear(d,d),nn.GELU(),nn.Linear(d,2*rank))
            nn.init.normal_(self.readout[-1].weight[:rank],std=.02)
            with torch.no_grad():self.readout[-1].weight[rank:].zero_();self.readout[-1].bias.zero_()

    def forward(self,wt_s,wt_z,position,wt_aa,candidate_aa):
        h,aa=self.node_response(wt_s,wt_z,position,wt_aa,candidate_aa)
        query=self.aa_readout(self.query(aa)-self.query.weight[wt_aa])
        if self.kind=='pair':
            # All pairs share the same nonlinear function; no fixed-length row readout.
            edge=self.left(h)[:,:,None]+self.right(h)[:,None,:]+query[:,None,None]+self.pair_content(wt_z)[None]
            return self.readout(edge)*(aa!=wt_aa)[:,None,None,None]
        field=self.node(h)[:,:,None]+query[:,None,None]+self.channel.weight[None,None]
        u,v=self.readout(field).split(self.rank,dim=-1)
        return expand_pair_factors(u,v*(aa!=wt_aa)[:,None,None,None])


def oracle_matrix_target(delta,rank=32):
    """Matrix target only, never expose singular vectors/factors to the generator."""
    with torch.no_grad():
        x=delta.double().permute(0,3,1,2);u,s,v=torch.linalg.svd(x,full_matrices=False)
        k=min(rank,x.shape[-1]);return ((u[...,:k]*s[...,None,:k])@v[...,:k,:]).permute(0,2,3,1).float()
