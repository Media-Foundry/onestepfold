#!/usr/bin/env python3
"""Summarize deterministic Stage A catalog shards without materializing GT."""

from __future__ import annotations

import argparse
import collections
import gzip
import json
from pathlib import Path
from typing import Any


def _quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p05": None, "p25": None, "p50": None, "p75": None, "p95": None}
    ordered = sorted(values)

    def percentile(fraction: float) -> float:
        index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
        return ordered[index]

    return {
        f"p{int(fraction * 100):02d}": percentile(fraction)
        for fraction in (0.05, 0.25, 0.5, 0.75, 0.95)
    }


def summarize(catalog_dir: Path, pattern: str = "shard-*.jsonl.gz") -> dict[str, Any]:
    paths = sorted(catalog_dir.glob(pattern))
    method_counts: collections.Counter[str] = collections.Counter()
    model_counts: collections.Counter[str] = collections.Counter()
    assembly_counts: collections.Counter[str] = collections.Counter()
    protein_chain_counts: collections.Counter[str] = collections.Counter()
    lengths: list[float] = []
    resolutions: list[float] = []
    missing_resolution = 0
    missing_dates = collections.Counter()
    context_nonzero = collections.Counter()
    total = 0
    unique_ids: set[str] = set()
    unresolved_sifts = 0
    assembly_composition_missing = 0
    for path in paths:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                total += 1
                unique_ids.add(record["pdb_id"])
                experimental = record.get("experimental", {})
                method_counts.update(experimental.get("methods", []))
                model_counts[str(experimental.get("model_count", 0))] += 1
                date_fields = (
                    "initial_deposition_date",
                    "initial_release_date",
                    "latest_revision_date",
                )
                missing_dates.update(
                    field for field in date_fields if not experimental.get(field)
                )
                resolution = experimental.get("resolution_high_angstrom")
                if resolution is None:
                    missing_resolution += 1
                else:
                    resolutions.append(float(resolution))
                assembly_counts[str(len(record.get("assemblies", [])))] += 1
                protein_chains = [
                    chain for chain in record.get("chains", []) if chain.get("is_protein")
                ]
                protein_chain_counts[str(len(protein_chains))] += 1
                lengths.extend(
                    float(chain["sequence_length"])
                    for chain in protein_chains
                    if chain.get("sequence_length")
                )
                if not record.get("assembly_compositions"):
                    assembly_composition_missing += 1
                unresolved_sifts += len(record.get("unresolved_sifts_rows", []))
                observations = record.get("asu_observations", {})
                for field in (
                    "water_atom_count",
                    "ion_atom_count",
                    "small_molecule_atom_count",
                    "other_polymer_atom_count",
                    "other_nonprotein_atom_count",
                    "nucleic_acid_atom_count",
                ):
                    if observations.get(field, 0):
                        context_nonzero[field] += 1
    return {
        "catalog_pattern": pattern,
        "shard_count": len(paths),
        "entry_count": total,
        "unique_pdb_id_count": len(unique_ids),
        "duplicate_pdb_id_count": total - len(unique_ids),
        "method_counts": dict(sorted(method_counts.items())),
        "model_count_counts": dict(
            sorted(model_counts.items(), key=lambda item: int(item[0]))
        ),
        "assembly_count_counts": dict(
            sorted(assembly_counts.items(), key=lambda item: int(item[0]))
        ),
        "protein_chain_count_counts": dict(
            sorted(protein_chain_counts.items(), key=lambda item: int(item[0]))
        ),
        "protein_sequence_length_quantiles": _quantiles(lengths),
        "resolution_quantiles_angstrom": _quantiles(resolutions),
        "missing_resolution_count": missing_resolution,
        "missing_date_counts": dict(sorted(missing_dates.items())),
        "context_nonzero_entry_counts": dict(sorted(context_nonzero.items())),
        "unresolved_sifts_row_count": unresolved_sifts,
        "assembly_composition_missing_count": assembly_composition_missing,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pattern", default="shard-*.jsonl.gz")
    args = parser.parse_args()
    summary = summarize(args.catalog_dir, args.pattern)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
