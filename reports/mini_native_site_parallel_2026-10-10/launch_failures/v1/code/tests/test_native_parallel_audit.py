"""Audit evidence must own its state and distinguish optimizer-only changes."""
import pytest
import torch

from fastglycan.native_parallel_audit import assert_tree_equal, cpu_snapshot


def test_snapshot_is_not_mutated_by_another_adam_step():
    parameter = torch.nn.Parameter(torch.tensor([1., -2.]))
    optimizer = torch.optim.AdamW([parameter], lr=.01)
    parameter.grad = torch.tensor([.2, -.1]); optimizer.step()
    saved = cpu_snapshot(optimizer.state_dict())
    copy = cpu_snapshot(saved)
    parameter.grad = torch.tensor([-.4, .7]); optimizer.step()
    assert_tree_equal(saved, copy)
    with pytest.raises(AssertionError):
        assert_tree_equal(cpu_snapshot(optimizer.state_dict()), saved)


@pytest.mark.parametrize('field', ['gradient', 'exp_avg', 'exp_avg_sq', 'step'])
def test_equal_parameters_cannot_hide_gradient_or_optimizer_change(field):
    expected = {'model': {'weight': torch.ones(2)}, 'gradient': torch.ones(2),
                'optimizer': {'exp_avg': torch.ones(2), 'exp_avg_sq': torch.ones(2),
                              'step': torch.tensor(3.)}}
    actual = cpu_snapshot(expected)
    target = actual['gradient'] if field == 'gradient' else actual['optimizer'][field]
    target.add_(1.)
    assert torch.equal(actual['model']['weight'], expected['model']['weight'])
    with pytest.raises(AssertionError):
        assert_tree_equal(actual, expected)


def test_bitwise_check_distinguishes_signed_zero():
    with pytest.raises(AssertionError):
        assert_tree_equal(torch.tensor([-0.]), torch.tensor([0.]))
