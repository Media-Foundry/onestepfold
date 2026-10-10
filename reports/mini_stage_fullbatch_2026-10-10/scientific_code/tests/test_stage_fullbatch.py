import copy

import pytest
import torch

from fastglycan.stage_fullbatch import BoundedLBFGS, FullBatchStageTrainer


def test_bounded_lbfgs_descends_and_restores_interrupted_history():
    value = torch.nn.Parameter(torch.tensor([3., -2.], dtype=torch.float64))
    optimizer = BoundedLBFGS([value])

    def closure():
        optimizer.optimizer.zero_grad(set_to_none=True)
        loss = (value * torch.tensor([1., 20.])).square().sum()
        loss.backward()
        return dict(raw=float(loss.detach()), parameter_sha256='caller metadata is independently checked')

    step = optimizer.step(closure, 16)
    assert step['changed'] and step['after'] < step['before']
    assert 1 <= step['calls'] <= 16
    initial = value.detach().clone()
    history = copy.deepcopy(optimizer.optimizer.state_dict())
    stopped = optimizer.step(closure, 1)
    assert stopped['status'] == 'budget_rollback' and stopped['calls'] == 1
    assert torch.equal(value, initial)
    after = optimizer.optimizer.state_dict()
    assert after['param_groups'] == history['param_groups']
    for key, row in history['state'].items():
        for name, before in row.items():
            actual = after['state'][key][name]
            if torch.is_tensor(before):
                assert torch.equal(before, actual)
            elif isinstance(before, list):
                for a, b in zip(before, actual):
                    assert torch.equal(a, b) if torch.is_tensor(a) else a == b
            else:
                assert before == actual


def test_lbfgs_restores_parameters_after_closure_exception():
    parameter = torch.nn.Parameter(torch.tensor([4.]))
    optimizer = BoundedLBFGS([parameter])
    calls = 0

    def closure():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError('injected failure at trial parameters')
        optimizer.optimizer.zero_grad(set_to_none=True)
        loss = parameter.square().sum()
        loss.backward()
        return dict(raw=float(loss.detach()))

    with pytest.raises(ValueError, match='injected failure'):
        optimizer.step(closure, 16)
    assert calls == 2 and float(parameter.detach()) == 4.
    assert not optimizer.optimizer.state


def test_fullbatch_site_weights_and_aa_decomposition_match_direct_autograd():
    class Toy(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor(0.7))

        def forward(self, base, boundary, reference, position, old, aa):
            z = self.weight * boundary + aa * .1
            return (base[0], base[1], z), (z, z)

    model = Toy()
    sites = [dict(site_key=str(i), parent_index=i, position_zero_based=0,
                  original_aa='A', candidates=['B', 'C']) for i in range(2)]
    scales = {'0': 2., '1': 5.}

    def fetch(site, aa):
        n = site['parent_index'] + 1
        x = torch.full((n, n, 2), 1. + .5 * (aa == 'C'))
        target = torch.full_like(x, float(n))
        return (torch.zeros(1), torch.zeros(1), torch.zeros_like(x)), x, target

    trainer = FullBatchStageTrainer(model, sites, fetch, {0: None, 1: None}, 'ABC', scales)
    result = trainer.objective()
    gradient = trainer.last_gradient.clone()
    model.zero_grad(set_to_none=True)
    direct = []
    for site in sites:
        row = []
        for aa in site['candidates']:
            _, x, target = fetch(site, aa)
            row.append((model.weight * x + 'ABC'.index(aa)*.1-target).square().mean()/scales[site['site_key']])
        direct.append(torch.stack(row).mean())
    loss = torch.stack(direct).mean()
    loss.backward()
    assert torch.allclose(gradient, model.weight.grad.detach().double().reshape(-1), atol=1e-7)
    assert abs(result['raw']-float(loss.detach())) < 1e-7
    assert abs(result['raw']-result['common']-result['centered']) < 1e-10
    assert result['centered'] > 0
    assert trainer.counts == dict(forwards=4, backwards=4, gradient_passes=1)
