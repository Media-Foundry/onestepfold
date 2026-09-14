#!/usr/bin/env python3
"""Select catalog-only monomer views; Stage B quality remains separate."""

from __future__ import annotations

import argparse
import gzip
import io
import json
from pathlib import Path

from onestepfold.data.monomer_filter import MonomerPolicy, classify_catalog_record


def _open_gzip_text(path: Path) -> io.TextIOWrapper:
    compressed = gzip.GzipFile(filename=str(path), mode="wb", mtime=0)
    return io.TextIOWrapper(compressed, encoding="utf-8")


def select(catalog_dir: Path, policy_path: Path, output: Path, summary_output: Path) -> None:
    policy = MonomerPolicy.from_toml(policy_path)
    counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    output.parent.mkdir(parents=True, exist_ok=True)
    with _open_gzip_text(output) as out:
        for path in sorted(catalog_dir.glob("shard-*.jsonl.gz")):
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line)
                    decision = classify_catalog_record(record, policy)
                    classification = decision["classification"]
                    counts[classification] = counts.get(classification, 0) + 1
                    reason = decision.get("reason", "unknown")
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
                    if classification != "monomer_clean":
                        continue
                    chain = next(
                        chain for chain in record["chains"] if chain.get("is_protein")
                    )
                    row = {
                        "pdb_id": record["pdb_id"],
                        "assembly_id": decision["assembly_id"],
                        "assembly_definition_source": decision["assembly_definition_source"],
                        "source_label_asym_id": chain.get("source_label_asym_id"),
                        "entity_id": chain.get("entity_id"),
                        "sequence": decision["sequence"],
                        "sequence_length": decision["sequence_length"],
                        "experimental_methods": decision["experimental_methods"],
                        "model_count": decision["model_count"],
                        "resolution_high_angstrom": record["experimental"].get(
                            "resolution_high_angstrom"
                        ),
                        "initial_release_date": record["experimental"].get(
                            "initial_release_date"
                        ),
                        "views": [
                            "monomer_clean",
                            *(
                                ["monomer_apo_like"]
                                if decision["apo_like_eligible"]
                                else []
                            ),
                        ],
                    }
                    out.write(json.dumps(row, sort_keys=True) + "\n")
    summary = {
        "policy": str(policy_path),
        "catalog_dir": str(catalog_dir),
        "classification_counts": dict(sorted(counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
    }
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    select(args.catalog_dir, args.policy, args.output, args.summary)


if __name__ == "__main__":
    main()
