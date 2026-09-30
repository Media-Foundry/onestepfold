import copy
import pytest
import torch
from torch import nn
from fastglycan.models.diffusion_scope import select_diffusion_scope


def test_explicit_scopes_preserve_values_and_exclude_trunk():
    block=nn.Module();block.attention_pair_bias=nn.Module();block.attention_pair_bias.attention=nn.Module()
    for k in ['q','k','v','o']:setattr(block.attention_pair_bias.attention,'linear_'+k,nn.Linear(4,4))
    block.conditioned_transition_block=nn.Module()
    for k in ['a1','a2','b']:setattr(block.conditioned_transition_block,'linear_nobias_'+k,nn.Linear(4,4,bias=False))
    m=nn.Module();m.trunk=nn.Linear(4,4);m.diffusion_module=nn.Module();m.diffusion_module.diffusion_transformer=nn.Module()
    m.diffusion_module.diffusion_transformer.blocks=nn.ModuleList([copy.deepcopy(block) for _ in range(8)])
    m.diffusion_module.atom_attention_decoder=nn.Linear(4,3)
    m.diffusion_module.fixed_fourier=nn.Parameter(torch.ones(4),requires_grad=False)
    original=copy.deepcopy(m.state_dict())
    eligible={n for n,p in m.named_parameters() if p.requires_grad}
    with pytest.raises(ValueError):select_diffusion_scope(m,'token_dense',native_trainable_names=eligible)
    m.requires_grad_(False);token=select_diffusion_scope(m,'token_dense',native_trainable_names=eligible);assert len(token)==56
    assert all(not p.requires_grad for p in m.trunk.parameters())
    assert all(not p.requires_grad for p in m.diffusion_module.atom_attention_decoder.parameters())
    assert {id(p) for p in token.values()}=={id(p) for p in m.parameters() if p.requires_grad}
    m.requires_grad_(False);full=select_diffusion_scope(m,'diffusion_dense',native_trainable_names=eligible)
    assert set(token)<set(full) and all(n.startswith('diffusion_module.') for n in full)
    assert all(torch.equal(v,original[n]) for n,v in m.state_dict().items())
    assert all(not p.requires_grad for p in m.trunk.parameters())
    assert not m.diffusion_module.fixed_fourier.requires_grad
