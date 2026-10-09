import pytest
import torch
from fastglycan.pair_split import pair_split_conditioning


def test_pair_split_preserves_endpoints_and_candidate_inputs():
    base = (torch.tensor([7.]), torch.tensor([3.]), torch.tensor([[1., 2.]]))
    adapted = (base[0], torch.tensor([9.]), torch.tensor([[5., 8.]]))
    mean = torch.tensor([[1., 2.]])
    assert pair_split_conditioning(base, adapted, mean, 'disabled') is base
    assert pair_split_conditioning(base, adapted, mean, 'full') is adapted
    for mode in ('pair', 'common', 'aa'):
        out = pair_split_conditioning(base, adapted, mean, mode)
        assert out[0] is base[0] and out[1] is base[1]
    assert pair_split_conditioning(base, adapted, mean, 'pair')[2] is adapted[2]
    assert torch.equal(pair_split_conditioning(base, adapted, mean, 'common')[2], torch.tensor([[2., 4.]]))
    assert torch.equal(pair_split_conditioning(base, adapted, mean, 'aa')[2], torch.tensor([[4., 6.]]))
    assert torch.equal(base[2], torch.tensor([[1., 2.]]))
    with pytest.raises(ValueError): pair_split_conditioning(base, adapted, mean, 'bad')
