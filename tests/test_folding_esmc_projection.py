import pytest
import torch
from torch import nn
from fastglycan.folding_esmc_projection import temporary_folding_esmc_projection


def test_projection_change_is_frozen_exact_and_reversible_on_failure():
    model=nn.Module();model.input_embedder=nn.Module();model.input_embedder.linear_esm=nn.Linear(2560,449,bias=False)
    model.other=nn.Linear(3,3);model.eval().requires_grad_(False)
    original=model.input_embedder.linear_esm;before={n:p.clone() for n,p in model.state_dict().items()}
    bridge=dict(weight=torch.randn(449,1152),bias=torch.randn(449));x=torch.randn(2,1152)
    with pytest.raises(RuntimeError,match='intentional'):
        with temporary_folding_esmc_projection(model,bridge) as layer:
            assert model.input_embedder.linear_esm is layer and not any(p.requires_grad for p in model.parameters())
            torch.testing.assert_close(layer(x),x@bridge['weight'].T+bridge['bias'])
            assert torch.equal(model.other.weight,before['other.weight'])
            raise RuntimeError('intentional')
    assert model.input_embedder.linear_esm is original
    assert all(torch.equal(p,before[n]) for n,p in model.state_dict().items())
    with pytest.raises(ValueError,match='shape'):
        with temporary_folding_esmc_projection(model,dict(weight=torch.ones(1,1),bias=torch.ones(1))):pass
