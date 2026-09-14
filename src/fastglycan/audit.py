"""Dataset checks that should run before model training."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import isclose

from .types import GlycanEnsemble


@dataclass(frozen=True, slots=True)
class AuditReport:
    ensemble_count: int
    scaffold_count: int
    source_count: int
    conformer_count: int
    missing_effective_sample_size: int
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.warnings

    def as_dict(self) -> dict[str, object]:
        return {
            "ensemble_count": self.ensemble_count,
            "scaffold_count": self.scaffold_count,
            "source_count": self.source_count,
            "conformer_count": self.conformer_count,
            "missing_effective_sample_size": self.missing_effective_sample_size,
            "warnings": list(self.warnings),
            "ok": self.ok,
        }


def audit_ensembles(ensembles: list[GlycanEnsemble]) -> AuditReport:
    warnings: list[str] = []
    duplicate_ids = [
        item for item, count in Counter(x.glycan_id for x in ensembles).items() if count > 1
    ]
    if duplicate_ids:
        warnings.append(f"duplicate glycan_id values: {', '.join(sorted(duplicate_ids))}")
    for ensemble in ensembles:
        total = sum(item.weight for item in ensemble.conformers)
        if not isclose(total, 1.0, rel_tol=2e-3, abs_tol=2e-3):
            warnings.append(f"{ensemble.glycan_id}: weights sum to {total:.6f}")
        if ensemble.effective_sample_size is None:
            warnings.append(f"{ensemble.glycan_id}: missing effective sample size")
    return AuditReport(
        ensemble_count=len(ensembles),
        scaffold_count=len({x.scaffold_id for x in ensembles}),
        source_count=len({x.source for x in ensembles}),
        conformer_count=sum(len(x.conformers) for x in ensembles),
        missing_effective_sample_size=sum(x.effective_sample_size is None for x in ensembles),
        warnings=tuple(warnings),
    )
