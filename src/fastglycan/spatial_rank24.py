"""Explicitly authorized R24 extension; previous spatial protocol stays frozen."""
import torch

RANK24_GRID=(24,'full')
RANK24_VARIANTS=('channel',)


class ChannelRank24Basis:
    """Per-channel FP64 matrix SVD, no AA mixing and no shared spatial basis."""
    def __init__(self,wt_z,target_z):
        if wt_z.ndim!=3 or wt_z.shape!=target_z.shape or wt_z.shape[0]!=wt_z.shape[1]:raise ValueError('square pair states required')
        if not torch.isfinite(wt_z).all() or not torch.isfinite(target_z).all():raise ValueError('nonfinite input')
        self.wt=wt_z;self.delta=target_z.double()-wt_z.double();self.length,_,self.channels=wt_z.shape
        self.u,self.sigma,self.vh=torch.linalg.svd(self.delta.permute(2,0,1),full_matrices=False)

    def reconstruct(self,variant,rank):
        if variant!='channel' or rank not in RANK24_GRID:raise ValueError('outside locked extension')
        r=self.length if rank=='full' else min(rank,self.length)
        d=((self.u[:,:,:r]*self.sigma[:,None,:r])@self.vh[:,:r]).permute(1,2,0)
        return (self.wt.double()+d).to(self.wt.dtype)

    def evidence(self):
        energy=float(self.delta.square().sum());ce=self.sigma.square().sum(-1);rows=[]
        for rank in RANK24_GRID:
            r=self.length if rank=='full' else min(rank,self.length);kept=self.sigma[:,:r].square().sum(-1);n=2*self.length*r*self.channels
            rows.append(dict(variant='channel',rank=rank,effective_rank=r,energy_retained=float(kept.sum())/energy if energy else None,
                channel_energy_retained=[float(x/y) if y>0 else None for x,y in zip(kept,ce)],factor_elements=n,dense_elements=self.wt.numel(),factor_to_dense=n/self.wt.numel()))
        return dict(shape=list(self.wt.shape),response_energy=energy,rows=rows)
