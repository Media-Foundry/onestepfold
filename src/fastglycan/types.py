"""Versioned, serialization-friendly contracts for reference glycan ensembles.

The contracts intentionally describe what is known about a dataset rather than
silently inferring missing physics. In particular, weights are population
weights under a declared protocol, not universal equilibrium probabilities.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from math import isclose
from typing import Any


def _tuple_float(values: tuple[float, ...] | list[float]) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result:
        raise ValueError("torsions must contain at least one angle")
    if any(value < -360.0 or value > 360.0 for value in result):
        raise ValueError("torsion angles must be reported in degrees")
    return result


@dataclass(frozen=True, slots=True)
class SimulationCondition:
    """Conditions needed to interpret a weighted conformer ensemble."""

    temperature_k: float
    pressure_bar: float | None = None
    solvent: str = "explicit_water"
    force_field: str = "unspecified"
    protocol: str = "unspecified"
    replicas: int | None = None

    def __post_init__(self) -> None:
        if self.temperature_k <= 0:
            raise ValueError("temperature_k must be positive")
        if self.pressure_bar is not None and self.pressure_bar <= 0:
            raise ValueError("pressure_bar must be positive when provided")
        if self.replicas is not None and self.replicas < 1:
            raise ValueError("replicas must be at least one")


@dataclass(frozen=True, slots=True)
class Conformer:
    """A representative structure and its population weight within one ensemble."""

    conformer_id: str
    torsions_deg: tuple[float, ...]
    weight: float
    structure_path: str | None = None
    effective_samples: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.conformer_id:
            raise ValueError("conformer_id cannot be empty")
        object.__setattr__(self, "torsions_deg", _tuple_float(self.torsions_deg))
        if self.weight < 0:
            raise ValueError("conformer weight cannot be negative")
        if self.effective_samples is not None and self.effective_samples <= 0:
            raise ValueError("effective_samples must be positive")


@dataclass(frozen=True, slots=True)
class GlycanEnsemble:
    """Weighted conformers for one fixed chemical glycan graph."""

    glycan_id: str
    sequence: str
    scaffold_id: str
    conformers: tuple[Conformer, ...]
    condition: SimulationCondition
    source: str
    topology_hash: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.glycan_id or not self.sequence or not self.scaffold_id:
            raise ValueError("glycan_id, sequence, and scaffold_id are required")
        if not self.conformers:
            raise ValueError("an ensemble needs at least one conformer")
        ids = [item.conformer_id for item in self.conformers]
        if len(ids) != len(set(ids)):
            raise ValueError("conformer_id values must be unique within an ensemble")
        total = sum(item.weight for item in self.conformers)
        if total <= 0 or not isclose(total, 1.0, rel_tol=2e-3, abs_tol=2e-3):
            raise ValueError(f"conformer weights must sum to 1 (got {total:.6f})")

    @property
    def effective_sample_size(self) -> float | None:
        values = [item.effective_samples for item in self.conformers]
        if any(value is None for value in values):
            return None
        return sum(values)  # type: ignore[arg-type]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GlycanEdit:
    """A legal, chemically explicit edit used for paired evaluation."""

    edit_id: str
    parent_glycan_id: str
    edited_glycan_id: str
    position: str
    from_residue: str
    to_residue: str
    topology_preserved: bool = True
    common_atom_mapping: Mapping[str, str] = field(default_factory=dict)
    allowed_by_protocol: bool = True

    def __post_init__(self) -> None:
        required = (
            self.edit_id,
            self.parent_glycan_id,
            self.edited_glycan_id,
            self.position,
            self.from_residue,
            self.to_residue,
        )
        if any(not value for value in required):
            raise ValueError("edit identifiers and residue fields are required")
        if not self.topology_preserved and not self.common_atom_mapping:
            raise ValueError("non-preserved topology edits require an atom mapping")


@dataclass(frozen=True, slots=True)
class GeometryQuery:
    """A fixed target event, independent of the model used to estimate it."""

    query_id: str
    description: str
    torsion_indices: tuple[int, ...]
    lower_deg: tuple[float, ...] | None = None
    upper_deg: tuple[float, ...] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.query_id or not self.description:
            raise ValueError("query_id and description are required")
        if not self.torsion_indices or any(index < 0 for index in self.torsion_indices):
            raise ValueError("torsion_indices must contain non-negative indices")
        if (self.lower_deg is None) != (self.upper_deg is None):
            raise ValueError("lower_deg and upper_deg must be provided together")
        if self.lower_deg is not None and len(self.lower_deg) != len(self.torsion_indices):
            raise ValueError("query bounds must match torsion_indices")


@dataclass(frozen=True, slots=True)
class ReferenceEditEffect:
    """Paired reference estimate with uncertainty for one legal edit and query."""

    edit_id: str
    query_id: str
    parent_probability: float
    edited_probability: float
    delta: float
    standard_error: float | None = None
    effective_samples_parent: float | None = None
    effective_samples_edited: float | None = None

    def __post_init__(self) -> None:
        for name in ("parent_probability", "edited_probability"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        expected = self.edited_probability - self.parent_probability
        if not isclose(self.delta, expected, abs_tol=1e-6):
            raise ValueError("delta must equal edited_probability - parent_probability")
        if self.standard_error is not None and self.standard_error < 0:
            raise ValueError("standard_error cannot be negative")
