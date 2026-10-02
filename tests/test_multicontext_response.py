import numpy as np
import pytest

from fastglycan.multicontext_response import (
    context_role, exposure_counts, score_fidelity, noise_selection, chirality_trace,
)


def test_fixed_exposure_and_holdout_partition():
    assert exposure_counts(8192) == [2048]*4
    assert exposure_counts(16384) == [4096]*4
    assert exposure_counts(32768) == [8192]*4
    assert sum(exposure_counts(257)) == 257
    assert context_role(4, 1) == 'train'
    assert context_role(4, 24) == 'unseen_site'
    assert context_role(6, 9) == 'unseen_protein'
    with pytest.raises(ValueError):
        context_role(3, 0)


def test_perfect_ranking_does_not_imply_score_calibration():
    y = np.arange(19, dtype=float)
    result = score_fidelity(y, 10*y+4, list('ABCDEFGHIJKLMNOPQRS'))
    assert result['spearman'] == pytest.approx(1)
    assert result['top1_match'] and result['top1_regret'] == 0
    assert result['task_mae'] > 10
    assert result['centered_scale_ratio'] == pytest.approx(10)


def test_cross_noise_choice_cannot_peek_at_new_noise():
    names = list('ABCDE')
    y = np.array([[0, 1, 2, 3, 4], [0, 1, 2, 3, 4], [9, 0, 2, 3, 4], [9, 0, 2, 3, 4]])
    result = noise_selection(y, y, names)
    assert result['aggregate']['old']['student_choice'] == 'A'
    assert result['aggregate']['new']['student_choice'] == 'B'
    assert result['cross_noise']['student_old_choice'] == 'A'
    assert result['cross_noise']['regret_to_new_best'] == 9
    assert result['cross_noise']['extra_regret_vs_teacher_old_choice'] == 0


def test_chirality_identity_volume_sign_and_rigid_invariance():
    x = np.array([[0., 0, 0], [1., 0, 0], [0, 1., 0], [0, 0, 1.]])
    labels = dict(centres=np.array([[0, 1, 2, 3]]), volumes=np.array([1.]))
    inv = dict(atom_names=np.array(['CA', 'N', 'C', 'CB']), residue_ids=np.repeat(17, 4))
    positive = chirality_trace(x+12, labels, inv, keep_all=True)
    assert positive['wrong'] == []
    assert positive['all_centres'][0]['reference_volume_ratio'] == pytest.approx(1)
    x[3, 2] = -1
    negative = chirality_trace(x, labels, inv)
    assert negative['wrong'][0]['atoms'][0]['residue'] == 17
    assert negative['minimum_oriented_normalized'] == pytest.approx(-1)
