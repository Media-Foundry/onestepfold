#!/usr/bin/env python3
"""Select a deterministic stratified/stress Stage B materialization pilot."""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import io
import json
from pathlib import Path
from typing import Any


def _open_gzip_text(path: Path) -> io.TextIOWrapper:
    compressed = gzip.GzipFile(filename=str(path), mode="wb", mtime=0)
    return io.TextIOWrapper(compressed, encoding="utf-8")


def _bucket(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    release = "pre" if str(row.get("initial_release_date", "9999")) <= "2021-09-30" else "post"
    length = int(row["sequence_length"])
    length_bin = (
        "20-128"
        if length <= 128
        else "128-256"
        if length <= 256
        else "256-512"
        if length <= 512
        else "512-1024"
    )
    methods = {str(value).upper() for value in row.get("experimental_methods", [])}
    method = (
        "xray"
        if "X-RAY DIFFRACTION" in methods
        else "em"
        if "ELECTRON MICROSCOPY" in methods
        else "neutron"
    )
    resolution = row.get("resolution_high_angstrom")
    resolution_bin = (
        "missing"
        if resolution is None
        else "lt2"
        if float(resolution) < 2
        else "2-2.5"
        if float(resolution) < 2.5
        else "2.5-3"
        if float(resolution) < 3
        else "ge3"
    )
    context = "apo_like" if "monomer_apo_like" in row.get("views", []) else "bound_or_context"
    return release, length_bin, method, resolution_bin, context


def _stress_score(features: dict[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if int(features.get("altloc_atom_count", 0)) > 0:
        score += 4
        reasons.append("altloc")
    occupancy = features.get("occupancy_min")
    if occupancy is not None and float(occupancy) < 0.5:
        score += 3
        reasons.append("low_occupancy")
    if int(features.get("modified_residue_count", 0)) > 0:
        score += 3
        reasons.append("modified_residue")
    if float(features.get("observed_residue_fraction_min", 1.0)) < 0.9:
        score += 3
        reasons.append("missing_residues")
    if int(features.get("assembly_count", 0)) > 1:
        score += 1
        reasons.append("assembly_ambiguity")
    if int(features.get("sequence_length", 0)) > 512:
        score += 2
        reasons.append("long_chain")
    return score, reasons


def select(
    catalog_dir: Path,
    candidates_path: Path,
    output: Path,
    summary_path: Path,
    stratified_count: int = 8000,
    stress_count: int = 2000,
) -> None:
    candidates: dict[str, dict[str, Any]] = {}
    with gzip.open(candidates_path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            candidates[str(row["pdb_id"])] = row

    catalog_by_id: dict[str, dict[str, Any]] = {}
    for shard in sorted(catalog_dir.glob("shard-*.jsonl.gz")):
        with gzip.open(shard, "rt", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                pdb_id = str(record["pdb_id"])
                if pdb_id not in candidates:
                    continue
                selected_source = candidates[pdb_id]["source_label_asym_id"]
                chain = next(
                    chain
                    for chain in record.get("chains", [])
                    if chain.get("is_protein")
                    and chain.get("source_label_asym_id") == selected_source
                )
                observations = record.get("asu_observations", {})
                modified_count = sum(
                    1
                    for comp_id in chain.get("observed_comp_ids", [])
                    if comp_id
                    not in {
                        "ALA",
                        "ARG",
                        "ASN",
                        "ASP",
                        "CYS",
                        "GLN",
                        "GLU",
                        "GLY",
                        "HIS",
                        "ILE",
                        "LEU",
                        "LYS",
                        "MET",
                        "PHE",
                        "PRO",
                        "SER",
                        "THR",
                        "TRP",
                        "TYR",
                        "VAL",
                    }
                )
                catalog_by_id[pdb_id] = {
                    "chain_record": chain,
                    "asu_observations": observations,
                    "stress_features": {
                        "altloc_atom_count": observations.get("altloc_atom_count", 0),
                        "occupancy_min": observations.get("occupancy_min"),
                        "modified_residue_count": modified_count,
                        "observed_residue_fraction_min": chain.get("residue_observation_fraction")
                        or 0.0,
                        "assembly_count": len(record.get("assemblies", [])),
                        "sequence_length": chain.get("sequence_length", 0),
                    },
                    "source_mmcif_filename": record.get("source_mmcif_filename"),
                    "assemblies": record.get("assemblies", []),
                    "assembly_compositions": record.get("assembly_compositions", []),
                    "experimental": record.get("experimental", {}),
                }

    buckets: dict[tuple[str, str, str, str, str], list[str]] = collections.defaultdict(list)
    for pdb_id, row in candidates.items():
        buckets[_bucket(row)].append(pdb_id)
    for values in buckets.values():
        values.sort(key=lambda pdb_id: hashlib.sha256(pdb_id.encode("ascii")).hexdigest())
    ordered_bucket_keys = sorted(buckets)
    stratified: list[str] = []
    cursor = 0
    while len(stratified) < min(stratified_count, len(candidates)) and any(buckets.values()):
        key = ordered_bucket_keys[cursor % len(ordered_bucket_keys)]
        if buckets[key]:
            stratified.append(buckets[key].pop(0))
        cursor += 1

    ranked_stress = []
    for pdb_id, catalog in catalog_by_id.items():
        if pdb_id in stratified:
            continue
        score, reasons = _stress_score(catalog["stress_features"])
        ranked_stress.append(
            (score, hashlib.sha256(pdb_id.encode("ascii")).hexdigest(), pdb_id, reasons)
        )
    ranked_stress.sort(reverse=True)
    stress = [
        item[2] for item in ranked_stress[: min(stress_count, len(candidates) - len(stratified))]
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    selected = []
    with _open_gzip_text(output) as handle:
        for component, pdb_ids in (("stratified", stratified), ("stress", stress)):
            for pdb_id in sorted(pdb_ids):
                row = dict(candidates[pdb_id])
                catalog = catalog_by_id[pdb_id]
                stress_score, reasons = _stress_score(catalog["stress_features"])
                row.update(
                    {
                        "pilot_component": component,
                        "pilot_stratum": "|".join(_bucket(row)),
                        "pilot_stress_score": stress_score,
                        "pilot_stress_reasons": reasons,
                        **catalog,
                    }
                )
                handle.write(json.dumps(row, sort_keys=True) + "\n")
                selected.append(row)
    summary = {
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "stratified_count": len(stratified),
        "stress_count": len(stress),
        "strata_count": len(buckets),
        "strata_population": {
            "|".join(key): len(values) for key, values in sorted(buckets.items())
        },
        "output": str(output),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--stratified-count", type=int, default=8000)
    parser.add_argument("--stress-count", type=int, default=2000)
    args = parser.parse_args()
    select(
        args.catalog_dir,
        args.candidates,
        args.output,
        args.summary,
        args.stratified_count,
        args.stress_count,
    )


if __name__ == "__main__":
    main()
