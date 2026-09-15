from pathlib import Path

from onestepfold.data.quality_policy import GTQualityPolicy, classify_quality


def _row(**qa):
    return {
        "resolution_high_angstrom": 2.0,
        "qa": {
            "frame_coverage": 0.98,
            "heavy_atom_coverage": 0.96,
            "internal_missing_fraction": 0.01,
            "finite_coordinate_violation_count": 0,
            "chain_break_count": 0,
            "chirality_violation_count": 0,
            "bond_length_outlier_count": 0,
            "peptide_bond_outlier_count": 0,
            "clash_density": 0.02,
            **qa,
        },
    }


def test_quality_policy_has_train_and_hq_tiers():
    policy = GTQualityPolicy.from_toml(
        Path(__file__).parents[1] / "configs" / "gt_quality_v1.toml"
    )
    result = classify_quality(_row(), policy)
    assert result["quality_class"] == "hq_eval"
    assert result["train_valid"] is True
    assert result["hq_eval_valid"] is True


def test_quality_policy_rejects_train_geometry_and_records_clash_only():
    policy = GTQualityPolicy.from_toml(
        Path(__file__).parents[1] / "configs" / "gt_quality_v1.toml"
    )
    result = classify_quality(_row(chain_break_count=1, steric_clash_count=50), policy)
    assert result["quality_class"] == "reject"
    assert "ca_chain_break" in result["train_reject_reasons"]


def test_quality_policy_allows_train_but_not_hq_for_coverage():
    policy = GTQualityPolicy.from_toml(
        Path(__file__).parents[1] / "configs" / "gt_quality_v1.toml"
    )
    result = classify_quality(_row(frame_coverage=0.85, heavy_atom_coverage=0.80), policy)
    assert result["quality_class"] == "train"
    assert result["train_valid"] is True
    assert result["hq_eval_valid"] is False
