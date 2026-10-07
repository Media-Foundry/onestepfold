import torch
import pytest

from fastglycan.reference_editor_intervention import (
    fixed_candidate_derangement, mean_candidate_conditioning, intervention_conditioning,
)


def fixture_conditioning():
    reference = (torch.full((3, 2), 1000.), torch.ones(3, 4), torch.full((3, 3, 2), -100.))
    predictions = [tuple(x + (i-9)*.125 + j for j, x in enumerate(reference)) for i in range(19)]
    return reference, predictions


def test_fixed_bijection_no_self_and_order_invariance():
    aas = 'CDEFGHIKLMNPQRSTVWY'
    a = fixed_candidate_derangement('p1_s3', aas)
    assert sorted(a) == list(range(19))
    assert all(i != j for i, j in enumerate(a))
    b = fixed_candidate_derangement('p1_s3', aas[::-1])
    assert {x: aas[j] for x, j in zip(aas, a)} == {x: aas[::-1][j] for x, j in zip(aas[::-1], b)}
    assert a == fixed_candidate_derangement('p1_s3', aas)


def test_common_preserves_mean_and_removes_only_candidate_variation():
    reference, predictions = fixture_conditioning()
    common, stats = mean_candidate_conditioning(reference, predictions)
    for j in range(3):
        assert torch.equal(common[j], reference[j]+j)
    for s in stats.values():
        assert abs(s['decomposition_residual']) < 1e-12
        assert s['centered_delta_mse'] > 0
    assert stats['s_inputs']['mean_delta_mse'] == 0


def test_correct_and_shuffled_are_bitwise_original_blocks_without_mutation():
    ref, predictions = fixture_conditioning()
    before = [[x.clone() for x in p] for p in predictions]
    common, _ = mean_candidate_conditioning(ref, predictions)
    donors = fixed_candidate_derangement('p1_s3', 'CDEFGHIKLMNPQRSTVWY')
    for i in range(19):
        assert intervention_conditioning(predictions, common, donors, 'correct', i) is predictions[i]
        assert intervention_conditioning(predictions, common, donors, 'common', i) is common
        assert intervention_conditioning(predictions, common, donors, 'shuffled', i) is predictions[donors[i]]
    assert all(torch.equal(a,b) for p,q in zip(before,predictions) for a,b in zip(p,q))
    with pytest.raises(ValueError, match='derangement'):
        intervention_conditioning(predictions, common, list(range(19)), 'shuffled', 0)


def test_reject_nonfinite_wrong_count_and_no_hidden_chemical_input():
    ref, predictions = fixture_conditioning()
    with pytest.raises(ValueError, match='nineteen'):
        mean_candidate_conditioning(ref, predictions[:18])
    predictions[0][2][0, 0, 0] = float('nan')
    with pytest.raises(ValueError, match='nonfinite'):
        mean_candidate_conditioning(ref, predictions)
    same = [tuple(x.clone() for x in ref) for _ in range(19)]
    common, stats = mean_candidate_conditioning(ref, same)
    assert all(torch.equal(a,b) for a,b in zip(common,ref))
    assert all(s['centered_energy_fraction'] is None for s in stats.values())
