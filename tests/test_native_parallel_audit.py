"""Audit evidence must own its state and distinguish optimizer-only changes."""
import pytest
import torch
import os

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


@pytest.mark.parametrize('rank', range(6))
def test_native_loader_is_isolated_from_six_rank_rendezvous(monkeypatch, rank):
    from fastglycan.paired_distributed import configure_torchrun_worker
    env = dict(RANK=str(rank), LOCAL_RANK=str(rank), WORLD_SIZE='6',
               LOCAL_WORLD_SIZE='6', GROUP_RANK='0', ROLE_RANK=str(rank),
               ROLE_WORLD_SIZE='6', MASTER_ADDR='127.0.0.1', MASTER_PORT='29607',
               HIP_VISIBLE_DEVICES='0,1,2,3,4,5', FASTGLYCAN_AUTHORIZED_HIP_0_5='1')
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    identity = configure_torchrun_worker(list(range(6)))
    # The actual native wrapper consumes the environment at construction.
    # It must see a one-device runner while our explicit Gloo identity survives.
    from protenix.utils.distributed import DistWrapper
    native = DistWrapper()
    assert (native.rank, native.local_rank, native.world_size,
            native.local_world_size) == (0, 0, 1, 1)
    assert identity == (rank, 6, 'tcp://127.0.0.1:29607')
    assert os.environ['HIP_VISIBLE_DEVICES'] == str(rank)
