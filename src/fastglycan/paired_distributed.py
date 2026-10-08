"""Two-sample synchronous updates and atomic handoff, independent of native model."""
import os
from pathlib import Path
import tempfile

import torch
from torch import nn


def configure_torchrun_worker(devices):
    """Select one HIP device before torch HIP initialization; isolate native runner.

Torchrun launches processes, but native runner must initialize as single-device.
Rendezvous is explicit after native model load. No CUDA/ROCR selectors are used.
"""
    if len(set(devices))!=len(devices) or any(d not in range(6) for d in devices):
        raise ValueError('distinct authorized HIP0..5 devices required')
    rank=int(os.environ['RANK']);world=int(os.environ['WORLD_SIZE'])
    local=int(os.environ['LOCAL_RANK'])
    if world!=len(devices) or rank!=local: raise ValueError('single-host launcher required')
    address=f"tcp://{os.environ['MASTER_ADDR']}:{os.environ['MASTER_PORT']}"
    os.environ['HIP_VISIBLE_DEVICES']=str(devices[local])
    os.environ['FASTGLYCAN_AUTHORIZED_HIP_0_5']='1'
    for key in ('RANK','WORLD_SIZE','LOCAL_RANK','LOCAL_WORLD_SIZE','GROUP_RANK','ROLE_RANK','ROLE_WORLD_SIZE'):
        os.environ.pop(key,None)
    return rank,world,address


def atomic_checkpoint(path,payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            torch.save(payload,stream);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def paired_local_index(rank,world_size):
    if world_size!=2 or rank not in (0,1):
        raise ValueError('locked global batch has exactly two candidates')
    return rank


class CandidateStructureLoss(nn.Module):
    """DDP owns only trainable bank; frozen runtime remains outside module tree."""
    def __init__(self,bank,runtime,objective):
        super().__init__();self.bank=bank;self.runtime=runtime;self.objective=objective

    def forward(self,site,aa):
        item,c=self.runtime.conditioning(self.bank,site,aa)
        x=self.runtime.base.decode(item,c,0)
        loss,values=self.objective(x,item['teacher'][0],item['ca'],item['labels'])
        self.last_components=values
        return loss
