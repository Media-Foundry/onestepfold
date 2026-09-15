"""Stage B coordinate-quality policy and record classification."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class QualityThresholds:
    max_resolution_angstrom: float
    min_frame_coverage: float
    min_heavy_atom_coverage: float
    max_internal_missing_fraction: float
    require_finite_coordinates: bool
    max_ca_chain_break_count: int
    max_chirality_violation_count: int
    max_bond_length_outlier_count: int
    max_peptide_bond_outlier_count: int


@dataclass(frozen=True)
class GTQualityPolicy:
    version: str
    date_cutoff: str
    train: QualityThresholds
    hq_eval: QualityThresholds

    @classmethod
    def from_toml(cls, path: Path) -> GTQualityPolicy:
        with path.open("rb") as handle:
            data = tomllib.load(handle)

        def load(section: Mapping[str, Any]) -> QualityThresholds:
            return QualityThresholds(
                max_resolution_angstrom=float(section["max_resolution_angstrom"]),
                min_frame_coverage=float(section["min_frame_coverage"]),
                min_heavy_atom_coverage=float(section["min_heavy_atom_coverage"]),
                max_internal_missing_fraction=float(section["max_internal_missing_fraction"]),
                require_finite_coordinates=bool(section["require_finite_coordinates"]),
                max_ca_chain_break_count=int(section["max_ca_chain_break_count"]),
                max_chirality_violation_count=int(section["max_chirality_violation_count"]),
                max_bond_length_outlier_count=int(section["max_bond_length_outlier_count"]),
                max_peptide_bond_outlier_count=int(section["max_peptide_bond_outlier_count"]),
            )

        policy = data["policy"]
        return cls(
            version=str(policy["version"]),
            date_cutoff=str(policy["date_cutoff"]),
            train=load(data["train"]),
            hq_eval=load(data["hq_eval"]),
        )


def classify_quality(
    row: Mapping[str, Any], policy: GTQualityPolicy
) -> dict[str, Any]:
    """Return deterministic Train/HQ-Eval/Reject flags and reasons.

    Clashes are deliberately recorded but do not reject a record in v1. The
    caller may use ``clash_density`` for reporting or a future policy tier.
    """
    qa = row.get("qa", {})
    reasons: list[str] = []
    resolution = row.get("resolution_high_angstrom")
    if resolution is None:
        reasons.append("missing_resolution")
    else:
        try:
            resolution_value = float(resolution)
        except (TypeError, ValueError):
            resolution_value = None
            reasons.append("invalid_resolution")
        if resolution_value is not None and resolution_value > policy.train.max_resolution_angstrom:
            reasons.append("resolution")

    def count(name: str) -> int:
        try:
            return int(qa.get(name, 0) or 0)
        except (TypeError, ValueError):
            return 1

    finite_bad = count("finite_coordinate_violation_count") > 0
    if policy.train.require_finite_coordinates and finite_bad:
        reasons.append("nonfinite_coordinates")
    if count("chain_break_count") > policy.train.max_ca_chain_break_count:
        reasons.append("ca_chain_break")
    if count("chirality_violation_count") > policy.train.max_chirality_violation_count:
        reasons.append("chirality")
    if count("bond_length_outlier_count") > policy.train.max_bond_length_outlier_count:
        reasons.append("bond_length")
    if count("peptide_bond_outlier_count") > policy.train.max_peptide_bond_outlier_count:
        reasons.append("peptide_bond")

    def value(name: str) -> float:
        try:
            return float(qa.get(name, 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    if value("frame_coverage") < policy.train.min_frame_coverage:
        reasons.append("frame_coverage")
    if value("heavy_atom_coverage") < policy.train.min_heavy_atom_coverage:
        reasons.append("heavy_atom_coverage")
    if value("internal_missing_fraction") > policy.train.max_internal_missing_fraction:
        reasons.append("internal_missing")

    train_valid = not reasons
    hq_reasons: list[str] = []
    if train_valid:
        if resolution is None or float(resolution) > policy.hq_eval.max_resolution_angstrom:
            hq_reasons.append("resolution")
        if value("frame_coverage") < policy.hq_eval.min_frame_coverage:
            hq_reasons.append("frame_coverage")
        if value("heavy_atom_coverage") < policy.hq_eval.min_heavy_atom_coverage:
            hq_reasons.append("heavy_atom_coverage")
        if value("internal_missing_fraction") > policy.hq_eval.max_internal_missing_fraction:
            hq_reasons.append("internal_missing")
        # Geometry and finite-coordinate constraints are identical for both tiers.
        if finite_bad:
            hq_reasons.append("nonfinite_coordinates")
        for name, limit, reason in (
            ("chain_break_count", policy.hq_eval.max_ca_chain_break_count, "ca_chain_break"),
            (
                "chirality_violation_count",
                policy.hq_eval.max_chirality_violation_count,
                "chirality",
            ),
            (
                "bond_length_outlier_count",
                policy.hq_eval.max_bond_length_outlier_count,
                "bond_length",
            ),
            (
                "peptide_bond_outlier_count",
                policy.hq_eval.max_peptide_bond_outlier_count,
                "peptide_bond",
            ),
        ):
            if count(name) > limit:
                hq_reasons.append(reason)

    return {
        "quality_class": (
            "hq_eval" if train_valid and not hq_reasons else "train" if train_valid else "reject"
        ),
        "train_valid": train_valid,
        "hq_eval_valid": train_valid and not hq_reasons,
        "train_reject_reasons": sorted(set(reasons)),
        "hq_eval_reasons": sorted(set(hq_reasons)),
        "clash_density": value("clash_density"),
    }


__all__ = ["GTQualityPolicy", "QualityThresholds", "classify_quality"]
