"""Reference-conditioned task-delta predictors; never generate mutant structures."""
import numpy as np
import torch
from torch import nn
from fastglycan.deep_response_student import DeepResponseStudent


def reference_node_features(coordinates, observed, position):
    """20 rigid-invariant features from an explicitly supplied reference backbone.

    Only observed Cα pairs separated by >=3 residues contribute to summaries.
    Missing coordinates are replaced before any distance calculation and masked.
    This is a task input, not an experimental mutant structure or target latent.
    """
    x=np.asarray(coordinates,dtype=np.float64);mask=np.asarray(observed,dtype=bool)
    if x.shape!=(len(mask),3) or not 0<=position<len(x) or not np.isfinite(x[mask]).all():
        raise ValueError('invalid observed reference backbone')
    x=np.where(mask[:,None],x,0.)
    dist=np.linalg.norm(x[:,None]-x[None],axis=-1)
    p=np.arange(len(x));valid=mask[:,None]&mask[None,:]&(abs(p[:,None]-p[None,:])>=3)
    centers=np.array([0,4,8,12,16,24,32.]);rbf=np.exp(-((dist[...,None]-centers)/8)**2)
    count=valid.sum(1)
    average=(rbf*valid[...,None]).sum(1)/np.maximum(count[:,None],1)
    sitevalid=mask&mask[position];site=rbf[:,position]*sitevalid[:,None]
    result=np.column_stack([average,site,mask,np.repeat(mask[position],len(x)),count/len(x),
                            np.clip(p-position,-32,32)/32,np.repeat(np.log(len(x))/8,len(x)),
                            np.minimum(dist[:,position]/32,2)*sitevalid])
    assert result.shape==(len(x),20) and np.isfinite(result).all()
    return result.astype(np.float32)


class ContextTaskReadout(DeepResponseStudent):
    """Same large WT node encoder; reference-aware pooling replaces dense Δz."""
    def __init__(self,single_channels=384,pair_channels=128):
        super().__init__(size='large',content=False,single_channels=single_channels,pair_channels=pair_channels)
        del self.u,self.v
        self.reference=nn.Sequential(nn.Linear(20,128),nn.GELU(),nn.LayerNorm(128))
        self.fusion=nn.Sequential(nn.LayerNorm(384),nn.Linear(384,256),nn.GELU())
        self.pool_weight=nn.Linear(256,1)
        self.score=nn.Sequential(nn.LayerNorm(768),nn.Linear(768,256),nn.GELU(),nn.Linear(256,1))
        nn.init.zeros_(self.score[-1].weight);nn.init.zeros_(self.score[-1].bias)

    def forward(self,wt_s,wt_z,position,wt_aa,reference):
        if reference.shape!=(len(wt_s),20):raise ValueError('explicit reference task input required')
        h,aa=self.node_response(wt_s,wt_z,position,wt_aa,list(range(20)))
        r=self.reference(reference)[None].expand(20,-1,-1)
        mixed=self.fusion(torch.cat([h,r],-1))
        pool=(self.pool_weight(mixed).softmax(1)*mixed).sum(1)
        query=self.query(aa)-self.query.weight[wt_aa]
        raw=self.score(torch.cat([pool,mixed[:,position],query],-1)).squeeze(-1)
        return raw-raw[wt_aa]


class AATaskReadout(nn.Module):
    """Context-free source/target-AA preference control; no reference or WT tensors."""
    def __init__(self):
        super().__init__();self.embedding=nn.Embedding(20,32)
        self.score=nn.Sequential(nn.Linear(96,128),nn.GELU(),nn.Linear(128,64),nn.GELU(),nn.Linear(64,1))
        nn.init.zeros_(self.score[-1].weight);nn.init.zeros_(self.score[-1].bias)

    def forward(self,wt_aa):
        q=self.embedding.weight;w=q[wt_aa].expand_as(q)
        raw=self.score(torch.cat([w,q,q-w],-1)).squeeze(-1)
        return raw-raw[wt_aa]
