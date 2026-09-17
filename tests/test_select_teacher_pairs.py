import importlib.util
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "select_teacher_pairs", Path(__file__).parents[1] / "scripts" / "select_teacher_pairs.py"
)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
filter_supported_sequences = _MODULE.filter_supported_sequences


def test_filter_supported_sequences_preserves_valid_rows_and_reasons_invalid() -> None:
    valid = {"group_id": "g1", "sample_id": "s1", "sequence": "ACDEFGHIKLMNPQRSTVWY"}
    invalid = {"group_id": "g2", "sample_id": "s2", "sequence": "ACXU"}

    supported, excluded = filter_supported_sequences([valid, invalid])

    assert supported == [valid]
    assert excluded == [
        {
            "group_id": "g2",
            "sample_id": "s2",
            "sequence_length": 4,
            "unsupported_symbols": ["U", "X"],
            "reason": "protenix_canonical_protein_alphabet",
        }
    ]
