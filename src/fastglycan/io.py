"""JSONL persistence for small, inspectable research records."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .types import Conformer, GlycanEnsemble, SimulationCondition


def _condition(data: dict[str, Any]) -> SimulationCondition:
    return SimulationCondition(**data)


def ensemble_from_dict(data: dict[str, Any]) -> GlycanEnsemble:
    payload = dict(data)
    conformers = tuple(Conformer(**item) for item in payload.pop("conformers"))
    payload["condition"] = _condition(payload["condition"])
    return GlycanEnsemble(conformers=conformers, **payload)


def load_ensembles(path: str | Path) -> list[GlycanEnsemble]:
    records: list[GlycanEnsemble] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                payload = json.loads(line)
                records.append(ensemble_from_dict(payload))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid ensemble record at line {line_number}: {exc}") from exc
    return records


def save_ensembles(path: str | Path, ensembles: Iterable[GlycanEnsemble]) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        for ensemble in ensembles:
            handle.write(json.dumps(ensemble.as_dict(), sort_keys=True) + "\n")
