import torch
import numpy as np
from torch import nn
from fastglycan.models.pair_recovery import PairRecovery


class MockPairBlock(nn.Module):
    def __init__(self,c_z=4,c_s=0,dropout=0.):
        super().__init__();self.linear=nn.Linear(c_z,c_z)
    def forward(self,s,z,**kwargs):return None,z+torch.tanh(self.linear(z))


def test_recovery_identity_independent_weights_and_paired_initialization():
    native=[MockPairBlock(),MockPairBlock()]
    args=dict(input_channels=3,single_channels=2,pair_channels=4,width=8)
    p=PairRecovery(native,'pretrained',71,**args);r=PairRecovery(native,'random',71,**args)
    for name,value in p.state_dict().items():
        if not name.startswith('blocks.'):assert torch.equal(value,r.state_dict()[name])
    assert p.blocks[0].linear.weight.data_ptr()!=native[0].linear.weight.data_ptr()
    assert torch.equal(p.blocks[0].linear.weight,native[0].linear.weight)
    base=(torch.randn(5,3),torch.randn(5,2),torch.randn(5,5,4));ref=torch.randn(5,5,4)
    before=base[2].clone()
    for net in (p,r):
        out=net(base,ref,2,0,1)
        assert out[0] is base[0] and out[1] is base[1]
        assert torch.equal(out[2],base[2])
        assert net(base,ref,2,0,0) is base
        opt=torch.optim.SGD(net.parameters(),lr=.1);target=torch.randn_like(base[2])
        (out[2]-target).square().mean().backward()
        assert net.out.weight.grad.abs().sum()>0
        assert net.blocks[0].linear.weight.grad.abs().sum()==0
        opt.step();opt.zero_grad()
        (net(base,ref,2,0,1)[2]-target).square().mean().backward()
        assert net.blocks[0].linear.weight.grad.abs().sum()>0
        a=net(base,ref,2,0,1);net(base,ref,2,0,3);again=net(base,ref,2,0,1)
        assert torch.equal(a[2],again[2])
    assert torch.equal(base[2],before)


def test_native_numpy_initialization_is_seeded_and_restores_rng():
    class NumpyPairBlock(MockPairBlock):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            with torch.no_grad():
                self.linear.weight.copy_(torch.as_tensor(np.random.randn(*self.linear.weight.shape)))

    native=[NumpyPairBlock(),NumpyPairBlock()]
    args=dict(input_channels=3,single_channels=2,pair_channels=4,width=8)
    np.random.seed(17)
    state=np.random.get_state()
    first=PairRecovery(native,'random',71,**args)
    after=np.random.get_state()
    assert state[0]==after[0] and np.array_equal(state[1],after[1]) and state[2:]==after[2:]
    np.random.randn(1000)
    second=PairRecovery(native,'random',71,**args)
    for name,value in first.state_dict().items():
        assert torch.equal(value,second.state_dict()[name]),name
