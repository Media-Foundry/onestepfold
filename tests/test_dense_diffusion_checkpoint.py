import copy
import pytest
import torch
from torch import nn
from fastglycan.models.diffusion_scope import load_dense_diffusion_checkpoint


def test_native_dense_terminal_loading_is_scoped_and_validated_before_mutation():
    model=nn.Module();model.trunk=nn.Linear(2,2);model.diffusion_module=nn.Linear(2,3)
    model.requires_grad_(False);initial=copy.deepcopy(model.state_dict())
    names=['diffusion_module.weight','diffusion_module.bias']
    state=dict(schema='native_dense_diffusion_v1',arm='diffusion_dense',update=512,exposures=2048,
        trained={n:initial[n]+.2 for n in names})
    for kind in ['missing','nonfinite','shape','dtype','nonterminal']:
        bad=copy.deepcopy(state)
        if kind=='missing':bad['trained'].pop(names[1])
        if kind=='nonfinite':bad['trained'][names[1]][0]=float('nan')
        if kind=='shape':bad['trained'][names[1]]=torch.ones(4)
        if kind=='dtype':bad['trained'][names[1]]=bad['trained'][names[1]].double()
        if kind=='nonterminal':bad['update']=128
        with pytest.raises(ValueError):load_dense_diffusion_checkpoint(model,bad,arm='diffusion_dense',expected_names=names)
        assert all(torch.equal(v,initial[n]) for n,v in model.state_dict().items())
    load_dense_diffusion_checkpoint(model,state,arm='diffusion_dense',expected_names=names)
    assert all(torch.equal(model.get_parameter(n),state['trained'][n]) for n in names)
    assert torch.equal(model.trunk.weight,initial['trunk.weight']) and torch.equal(model.trunk.bias,initial['trunk.bias'])
    assert not any(p.requires_grad for p in model.parameters())
    assert torch.allclose(model.diffusion_module(torch.tensor([1.,2.])),
        torch.nn.functional.linear(torch.tensor([1.,2.]),state['trained'][names[0]],state['trained'][names[1]]))
