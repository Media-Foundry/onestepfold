"""Native bridge parity, state ownership and target initialization checks."""
from types import SimpleNamespace
import pytest
import torch
from torch import nn
from fastglycan.models.differentiable_mini import full_recycle_pairformer
from fastglycan.models.prefix_recycle import prefix_recycle_pairformer


class Input(nn.Module):
    def forward(self,f,**kw):return f['x']


class Relative(nn.Module):
    def forward(self,x):return x


class Template(nn.Module):
    n_blocks=1
    def forward(self,f,z,**kw):return .03*z + f['template']


class MSA(nn.Module):
    def forward(self,f,z,s,**kw):return z + .1*s[:,None,:] + f['msa']


class Stack(nn.Module):
    def forward(self,s,z,**kw):return torch.tanh(s+z.mean(1)),torch.tanh(z+s[None,:,:])


class Toy(nn.Module):
    def __init__(self):
        super().__init__();self.train_confidence_only=False
        self.configs=SimpleNamespace(triangle_multiplicative='torch',triangle_attention='torch')
        self.input_embedder=Input();self.relative_position_encoding=Relative();self.template_embedder=Template();self.msa_module=MSA();self.pairformer_stack=Stack()
        for n in ['linear_no_bias_sinit','linear_no_bias_zinit1','linear_no_bias_zinit2','linear_no_bias_z_cycle','linear_no_bias_s']:
            setattr(self,n,nn.Linear(4,4,bias=False))
        self.linear_no_bias_token_bond=nn.Linear(1,4,bias=False)
        self.layernorm_z_cycle=nn.LayerNorm(4);self.layernorm_s=nn.LayerNorm(4)


def example():
    torch.manual_seed(11);m=Toy().eval()
    f=dict(x=torch.randn(5,4),relp=torch.randn(5,5,4),token_bonds=torch.zeros(5,5),template=torch.randn(5,5,4),msa=torch.randn(5,5,4))
    return m,f


@pytest.mark.parametrize('depth',[2,3])
def test_segmented_bridge_matches_native_and_preserves_prefix(depth):
    m,f=example();snapshots={}
    with torch.no_grad():
        exact=full_recycle_pairformer(m,f,4)
        capture=prefix_recycle_pairformer(m,f,4,capture_cycles=(2,3),snapshots=snapshots)
        saved=tuple(x.clone() for x in snapshots[depth])
        result=prefix_recycle_pairformer(m,f,4-depth,initial_state=snapshots[depth])
    assert all(torch.equal(x,y) for x,y in zip(exact,capture))
    assert all(torch.equal(x,y) for x,y in zip(exact,result))
    assert all(torch.equal(x,y) for x,y in zip(saved,snapshots[depth]))
    assert all(a.data_ptr()!=b.data_ptr() for a,b in zip(result[1:],snapshots[depth]))


def test_target_features_reinjected_and_candidate_order_independent():
    m,f=example();snapshots={};prefix_recycle_pairformer(m,f,4,capture_cycles=(2,),snapshots=snapshots)
    target=dict(f,x=f['x']+.7,msa=f['msa']-.2)
    a=prefix_recycle_pairformer(m,target,2,initial_state=snapshots[2])
    b=prefix_recycle_pairformer(m,f,2,initial_state=snapshots[2])
    again=prefix_recycle_pairformer(m,target,2,initial_state=snapshots[2])
    assert torch.equal(a[0],target['x'])
    assert not torch.equal(a[2],b[2])
    assert all(torch.equal(x,y) for x,y in zip(a,again))


def test_invalid_state_and_stochastic_mode_fail_closed():
    m,f=example()
    with pytest.raises(ValueError,match='shape'):prefix_recycle_pairformer(m,f,2,initial_state=(torch.zeros(3,4),torch.zeros(3,3,4)))
    with pytest.raises(ValueError,match='dtype'):prefix_recycle_pairformer(m,f,2,initial_state=(torch.zeros(5,4,dtype=torch.float64),torch.zeros(5,5,4)))
    with pytest.raises(ValueError,match='eval'):prefix_recycle_pairformer(m,f,2,mc_dropout=True)
    with pytest.raises(ValueError,match='cycle'):prefix_recycle_pairformer(m,f,0)


class StochasticMSA(nn.Module):
    def forward(self,f,z,s,**kw):
        import random
        import numpy as np
        # Consume all CPU RNG families and make their continuation affect output.
        return z + torch.rand_like(z)*.1 + random.random()*.01 + np.random.random()*.01


@pytest.mark.parametrize('depth',[2,3])
def test_rng_restoration_recovers_true_segment_even_with_interleaved_work(depth):
    from fastglycan.models.prefix_recycle import capture_rng_state,restore_rng_state
    m,f=example();m.msa_module=StochasticMSA();initial=capture_rng_state()
    exact=full_recycle_pairformer(m,f,4);expected_rng=capture_rng_state()
    restore_rng_state(initial);snapshots={};rng={}
    prefix_recycle_pairformer(m,f,4,capture_cycles=(2,3),snapshots=snapshots,snapshot_rng=rng)
    torch.rand(71)
    restored=prefix_recycle_pairformer(m,f,4-depth,initial_state=snapshots[depth],initial_rng=rng[depth])
    assert all(torch.equal(x,y) for x,y in zip(exact,restored))
    actual_rng=capture_rng_state()
    assert torch.equal(actual_rng['cpu'],expected_rng['cpu'])
    assert actual_rng['python']==expected_rng['python']
    assert all((x==y).all() if hasattr(x,'shape') else x==y for x,y in zip(actual_rng['numpy'],expected_rng['numpy']))
