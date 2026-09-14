"""Interfaces shared by direct predictors and joint generators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence


class JointEnsembleModel(ABC):
    """Minimal interface for models evaluated on a fixed glycan graph."""

    @abstractmethod
    def sample(self, glycan_id: str, n: int, *, seed: int | None = None) -> list[tuple[float, ...]]:
        """Draw torsion vectors in degrees."""

    @abstractmethod
    def log_prob(self, glycan_id: str, torsions_deg: Sequence[float]) -> float:
        """Return a model log-density or a documented proxy."""
