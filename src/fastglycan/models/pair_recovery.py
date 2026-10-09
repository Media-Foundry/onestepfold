"""Post-recycle dense pair recovery; candidate inputs/single remain read-only."""
import numpy as np
import torch
from torch import nn


class PairRecovery(nn.Module):
    def __init__(self, native_blocks, initialization, seed, input_channels=449,
                 single_channels=384, pair_channels=128, width=128):
        super().__init__()
        if len(native_blocks) != 2 or initialization not in ('pretrained','random'):
            raise ValueError('two matched native blocks and known initialization required')
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            self.aa=nn.Embedding(20,16)
            n=input_channels+single_channels+2*pair_channels+33
            self.node=nn.Sequential(nn.LayerNorm(n),nn.Linear(n,width),nn.SiLU(),nn.Linear(width,width))
            self.left=nn.Linear(width,pair_channels,bias=False)
            self.right=nn.Linear(width,pair_channels,bias=False)
            nn.init.normal_(self.left.weight,std=1e-3);nn.init.normal_(self.right.weight,std=1e-3)
            self.norm=nn.LayerNorm(pair_channels)
            self.out=nn.Linear(pair_channels,pair_channels,bias=False);nn.init.zeros_(self.out.weight)
            torch.manual_seed(seed+100003)
            # Native Linear initializes through scipy.stats.truncnorm/NumPy.
            # Torch's RNG fork alone does not isolate that independent stream.
            numpy_state=np.random.get_state()
            try:
                np.random.seed(seed+100003)
                self.blocks=nn.ModuleList([type(b)(c_z=pair_channels,c_s=0,dropout=0.) for b in native_blocks])
            finally:
                np.random.set_state(numpy_state)
            if initialization=='pretrained':
                for source,block in zip(native_blocks,self.blocks):
                    state=source.state_dict();block.load_state_dict({k:state[k] for k in block.state_dict()},strict=True)
        self.requires_grad_(True)
        self.config=dict(initialization=initialization,seed=seed,input_channels=input_channels,
                         single_channels=single_channels,pair_channels=pair_channels,width=width)

    def forward(self, base, reference_pair, position, old, target):
        if old==target:return base
        inputs,single,pair=base
        length=len(single)
        if not 0<=position<length or reference_pair.shape!=pair.shape:
            raise ValueError('reference/position mismatch')
        aa=self.aa(torch.tensor([old,target],device=pair.device)).flatten().expand(length,-1)
        flag=pair.new_zeros(length,1);flag[position]=1
        h=self.node(torch.cat((inputs,single,reference_pair[position],reference_pair[:,position],aa,flag),dim=-1))
        z=pair+self.left(h)[:,None,:]+self.right(h)[None,:,:]
        for block in self.blocks:
            _,z=block(None,z,pair_mask=None,triangle_multiplicative='torch',triangle_attention='torch',inplace_safe=False,chunk_size=None)
        return inputs,single,pair+self.out(self.norm(z))
