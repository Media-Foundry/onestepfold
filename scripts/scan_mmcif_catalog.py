#!/usr/bin/env python3
"""Stage A: scan raw mmCIF metadata into an entry/chain/assembly catalog."""

from __future__ import annotations

import argparse
import gzip
import json
import multiprocessing as mp
import os
from pathlib import Path
from typing import Any

from fastglycan.gt_catalog import load_sifts_chain_map, scan_entry

_CHAIN_MAP: dict[str, list[dict[str, str]]] = {}


def _init_worker(chain_map: dict[str, list[dict[str, str]]]) -> None:
    global _CHAIN_MAP
    _CHAIN_MAP = chain_map


def _scan_path(path: Path) -> dict[str, Any]:
    pdb_id = path.name.removesuffix(".cif.gz").lower()
    try:
        return scan_entry(path, _CHAIN_MAP.get(pdb_id, ()))
    except Exception as exc:  # noqa: BLE001 - preserve per-entry failures
        return {
            "schema_version": "gt_catalog_v1_error",
            "pdb_id": pdb_id,
            "source_mmcif_filename": path.name,
            "error": f"{type(exc).__name__}: {exc}",
        }


def scan(raw_dir: Path, sifts_csv: Path, output: Path, errors: Path, workers: int) -> None:
    chain_map = load_sifts_chain_map(sifts_csv)
    paths = sorted(raw_dir.rglob("*.cif.gz"))
    output.parent.mkdir(parents=True, exist_ok=True)
    errors.parent.mkdir(parents=True, exist_ok=True)
    context = mp.get_context("fork")
    with gzip.open(output, "wt", encoding="utf-8") as out, errors.open(
        "w", encoding="utf-8"
    ) as error_handle:
        with context.Pool(
            processes=workers,
            initializer=_init_worker,
            initargs=(chain_map,),
        ) as pool:
            for index, result in enumerate(
                pool.imap_unordered(_scan_path, paths, chunksize=8), 1
            ):
                if result.get("error"):
                    error_handle.write(json.dumps(result, sort_keys=True) + "\n")
                else:
                    out.write(json.dumps(result, sort_keys=True) + "\n")
                if index % 1000 == 0:
                    out.flush()
                    error_handle.flush()
                    print(f"scanned={index}/{len(paths)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--sifts-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--errors", type=Path, required=True)
    parser.add_argument(
        "--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2)
    )
    args = parser.parse_args()
    scan(args.raw_dir, args.sifts_csv, args.output, args.errors, args.workers)


if __name__ == "__main__":
    main()
