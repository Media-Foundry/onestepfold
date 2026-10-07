import copy
import json
from collections import Counter
from pathlib import Path

import pytest
import torch

from fastglycan.reference_editor_multiref import (
    paired_reference_editor, editor_state_digest, shared_parameter_name,
    validate_multiref_plan, multiref_update,
)


CONFIG = dict(input_channels=12, single_channels=8, pair_channels=4, width=16,
              workspace=3, blocks=2, heads=4, pair_width=8, pair_chunk=2,
              direct_hidden=64)


def test_paired_initialization_and_rng_isolation():
    state = torch.random.get_rng_state().clone()
    workspace = paired_reference_editor('workspace', 73, CONFIG)
    direct = paired_reference_editor('direct_global', 73, CONFIG)
    assert torch.equal(state, torch.random.get_rng_state())
    assert editor_state_digest(workspace, True) == editor_state_digest(direct, True)
    assert editor_state_digest(workspace) == editor_state_digest(paired_reference_editor('workspace', 73, CONFIG))
    assert editor_state_digest(direct) != editor_state_digest(paired_reference_editor('direct_global', 74, CONFIG))
    for name, value in workspace.state_dict().items():
        if shared_parameter_name(name):
            assert torch.equal(value, direct.state_dict()[name])


@pytest.mark.parametrize('architecture', ['workspace', 'direct_global'])
def test_full_conditioning_global_response_invariants_and_gradients(architecture):
    model = paired_reference_editor(architecture, 41, CONFIG)
    raw = (torch.randn(6, 12), torch.randn(6, 8), torch.randn(6, 6, 4))
    sequence = [0, 1, 2, 3, 4, 5]
    queries = [[], [(1, 1, 7)], [(4, 4, 8)], [(1, 1, 7), (4, 4, 8)]]
    ref = model.prepare_reference(raw, sequence)
    out = model(ref, queries)
    reverse = model(ref, queries[::-1])
    fresh = model(model.prepare_reference(raw, sequence), queries)
    for a, b, c, r in zip(out, reverse, fresh, raw):
        assert torch.equal(a[0], r)
        assert torch.equal(a, b.flip(0)) and torch.equal(a, c)
        assert torch.isfinite(a).all()
    assert all(torch.equal(x[3], y[0]) for x, y in zip(out, model(ref, [queries[3][::-1]])))
    assert (out[1][1, 3:] - raw[1][3:]).abs().max() > 0
    assert (out[2][1, 3:, 3:] - raw[2][3:, 3:]).abs().max() > 0
    loss = sum((x[1:] - r - .1).square().mean() for x, r in zip(out, raw))
    loss.backward()
    names = ['inputs.1.weight', 'aa.weight', 'pair_base.1.weight', 'input_out.weight',
             'single_out.weight', 'pair_out.3.weight']
    names.append('node_blocks.0.1.weight' if architecture == 'direct_global' else 'blocks.0.read.q.weight')
    for name in names:
        grad = dict(model.named_parameters())[name].grad
        assert grad is not None and torch.isfinite(grad).all() and grad.abs().sum() > 0
    torch.optim.SGD(model.parameters(), lr=.001).step()
    with pytest.raises(RuntimeError, match='parameter version'):
        model(ref, [[]])
    ref = model.prepare_reference(raw, sequence)
    raw[2].add_(1)
    with pytest.raises(RuntimeError, match='modified'):
        model(ref, [[]])


def test_protocol_membership_exposure_and_holdout_rejection():
    path = Path(__file__).resolve().parents[1] / 'reports/mini_reference_editor_multiref_plan_2026-10-07/plan.json'
    plan = json.loads(path.read_text())
    sites = validate_multiref_plan(plan)
    for run in plan['runs']:
        seen = Counter()
        for step in range(run['updates']):
            site, aas = multiref_update(run, sites, step)
            for aa in aas:
                seen[site['site_key'], aa] += 1
        assert set(seen.values()) == {64}
        assert len(seen) == 19 * len(run['train_site_keys'])
    wrong = copy.deepcopy(plan)
    wrong['runs'][0]['train_site_keys'][0] = 'p3_s84'
    with pytest.raises(ValueError, match='membership'):
        validate_multiref_plan(wrong)
    wrong = copy.deepcopy(plan)
    wrong['sites'][0]['candidates'] += wrong['sites'][0]['original_aa']
    with pytest.raises(ValueError, match='inventory'):
        validate_multiref_plan(wrong)
