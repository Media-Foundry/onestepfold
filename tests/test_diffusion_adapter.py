import copy
import torch
from torch import nn
from fastglycan.models.diffusion_adapter import attach_diffusion_adapter, merge_diffusion_adapter


def test_diffusion_adapter():
    # Actual nested names, a frozen external trunk, direct native weight access.
    block=nn.Module();block.attention_pair_bias=nn.Module();block.attention_pair_bias.attention=nn.Module()
    for k in ['q','k','v','o']:setattr(block.attention_pair_bias.attention,'linear_'+k,nn.Linear(4,4))
    block.conditioned_transition_block=nn.Module()
    for k in ['a1','a2','b']:setattr(block.conditioned_transition_block,'linear_nobias_'+k,nn.Linear(4,4,bias=False))
    model=nn.Module();model.trunk=nn.Linear(4,4);model.diffusion_module=nn.Module()
    model.diffusion_module.diffusion_transformer=nn.Module()
    model.diffusion_module.diffusion_transformer.blocks=nn.ModuleList([block])
    model.double().requires_grad_(False);baseline=copy.deepcopy(model.state_dict())
    rng=torch.get_rng_state().clone()
    adapters=attach_diffusion_adapter(model,rank=2,expected_blocks=1)
    assert torch.equal(rng,torch.get_rng_state()) and len(adapters)==7
    params=[p for a in adapters.values() for p in a.parameters()]
    assert {id(p) for p in params}=={id(p) for p in model.parameters() if p.requires_grad}
    x=torch.randn(3,4,dtype=torch.float64,requires_grad=True)
    loss=0
    for name,a in adapters.items():
        m=model.get_submodule(name)
        assert torch.equal(m.weight,baseline[name+'.weight'])
        y=torch.nn.functional.linear(x,m.weight,m.bias)
        loss=loss+y.square().mean()
    loss.backward()
    assert torch.isfinite(x.grad).all() and x.grad.norm()>0
    assert all(a.up.grad.norm()>0 and a.down.grad.count_nonzero()==0 for a in adapters.values())
    assert all(p.grad is None for p in model.parameters() if not p.requires_grad)
    torch.optim.SGD(params,lr=.01).step()
    effective={name:model.get_submodule(name).weight.detach().clone() for name in adapters}
    for name in adapters:assert torch.equal(model.get_submodule(name).parametrizations.weight.original,baseline[name+'.weight'])
    merge_diffusion_adapter(model,adapters)
    assert set(model.state_dict())==set(baseline)
    for name,w in effective.items():assert torch.equal(model.get_submodule(name).weight,w)
    for name in ['trunk.weight','trunk.bias']:assert torch.equal(model.state_dict()[name],baseline[name])
