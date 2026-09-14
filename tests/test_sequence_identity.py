import pytest

from onestepfold.data.sequence_identity import (
    calculate_pairwise_identity,
    exact_sequence_digest,
    group_exact_identity,
)


def test_pairwise_identity_uses_global_alignment_columns():
    identical = calculate_pairwise_identity("ACDE", "ACDE")
    assert identical.matches == 4
    assert identical.alignment_length == 4
    assert identical.gap_columns == 0
    assert identical.identity == 1.0

    insertion = calculate_pairwise_identity("ACDE", "ACDEx")
    assert insertion.matches == 4
    assert insertion.alignment_length == 5
    assert insertion.gap_columns == 1
    assert insertion.identity == pytest.approx(0.8)

    mutation = calculate_pairwise_identity("ACDE", "ACXE")
    assert mutation.matches == 3
    assert mutation.alignment_length == 4
    assert mutation.identity == pytest.approx(0.75)


def test_exact_identity_groups_verify_with_biopython():
    records = {"z": "ACDE", "a": "ACDE", "b": "ACDF", "c": "ACDEFG"}
    assert group_exact_identity(records) == {
        "a": ("a", "z"),
        "b": ("b",),
        "c": ("c",),
    }


def test_sequence_digest_rejects_empty_sequences():
    with pytest.raises(ValueError):
        exact_sequence_digest("")
