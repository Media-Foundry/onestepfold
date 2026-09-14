"""Model protocols and small baselines."""

from .base import JointEnsembleModel
from .empirical import WeightedEmpiricalModel

__all__ = ["JointEnsembleModel", "WeightedEmpiricalModel"]

