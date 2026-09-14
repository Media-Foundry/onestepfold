"""A transparent weighted empirical baseline for smoke tests and calibration."""

from __future__ import annotations

import random
from collections.abc import Sequence
from math import log

from ..types import GlycanEnsemble
from .base import JointEnsembleModel


class WeightedEmpiricalModel(JointEnsembleModel):
    """Resamples reference conformer representatives according to stored weights."""

    def __init__(self, ensembles: Sequence[GlycanEnsemble]) -> None:
        self._ensembles = {item.glycan_id: item for item in ensembles}

    def sample(self, glycan_id: str, n: int, *, seed: int | None = None) -> list[tuple[float, ...]]:
        if n < 1:
            raise ValueError("n must be positive")
        ensemble = self._ensembles[glycan_id]
        rng = random.Random(seed)
        conformers = ensemble.conformers
        return [
            rng.choices(conformers, weights=[x.weight for x in conformers], k=1)[0].torsions_deg
            for _ in range(n)
        ]

    def log_prob(self, glycan_id: str, torsions_deg: Sequence[float]) -> float:
        ensemble = self._ensembles[glycan_id]
        target = tuple(float(value) for value in torsions_deg)
        for conformer in ensemble.conformers:
            if conformer.torsions_deg == target:
                return log(conformer.weight)
        return float("-inf")
