import pytest
import torch
from fastglycan.backbone_sequence_task import backbone_target_pairs, backbone_target_loss, backbone_candidate_accept


def test_target_mask_and_rigid_invariance():
    xyz = torch.randn(8, 3, dtype=torch.double)
    mask = torch.ones(8, dtype=torch.bool); mask[2] = False
    xyz[2] = float('nan')
    pairs, distances = backbone_target_pairs(xyz, mask)
    assert not (pairs == 2).any() and ((pairs[:, 1]-pairs[:, 0]) >= 3).all()
    x = torch.nan_to_num(xyz)
    rotation = torch.linalg.qr(torch.randn(3, 3, dtype=torch.double))[0]
    loss = backbone_target_loss(x @ rotation + 7, torch.arange(8), pairs, distances)
    assert loss < 1e-28
    with pytest.raises(ValueError): backbone_target_pairs(xyz, torch.ones(8, dtype=torch.bool))


def test_task_gradient_and_expansion_not_compaction_reward():
    x = torch.arange(8, dtype=torch.double)[:, None] * torch.tensor([[1., .2, .1]], dtype=torch.double)
    pairs, distances = backbone_target_pairs(x, torch.ones(8, dtype=torch.bool))
    y = (x * 1.2).requires_grad_()
    assert torch.autograd.gradcheck(lambda z: backbone_target_loss(z, torch.arange(8), pairs, distances), (y,))
    assert backbone_target_loss(x*.5, torch.arange(8), pairs, distances) > 0


def test_task_gain_cannot_hide_geometry_failure():
    g = dict(bond_rmse=.1, peptide_mae=.05, severe_pairs_per_atom=0., max_penetration=1., chirality_fraction=1.)
    parent = dict(task=1., chemistry=dict(legacy_geometry=g, zero_severe=True, strict_checked_chirality=True))
    candidate = dict(task=.9, chemistry=dict(parent['chemistry']))
    assert backbone_candidate_accept(candidate, parent)['accepted']
    candidate['chemistry']['strict_checked_chirality'] = False
    assert not backbone_candidate_accept(candidate, parent)['accepted']
    candidate['chemistry']['strict_checked_chirality'] = True
    candidate['chemistry']['zero_severe'] = False
    assert not backbone_candidate_accept(candidate, parent)['accepted']
