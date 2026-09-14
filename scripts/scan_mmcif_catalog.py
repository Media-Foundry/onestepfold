#!/usr/bin/env python3
"""Stage A: scan raw mmCIF metadata into an entry/chain/assembly catalog."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import multiprocessing as mp
import os
from pathlib import Path
from typing import Any

from onestepfold.data.gt_catalog import load_sifts_chain_map, scan_entry

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


def _shard_for(pdb_id: str, shard_count: int) -> int:
    digest = hashlib.sha256(pdb_id.encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big") % shard_count


def _shard_path(path: Path, shard_id: int, shard_count: int) -> Path:
    if shard_count == 1:
        return path
    suffix = "".join(path.suffixes)
    return path.with_name(f"shard-{shard_id:03d}{suffix}")


def _manifest_paths(raw_dir: Path, pdb_list: Path | None) -> list[Path]:
    if pdb_list is None:
        paths = list(raw_dir.rglob("*.cif.gz"))
    else:
        paths = []
        for line in pdb_list.read_text(encoding="utf-8").splitlines():
            pdb_id = line.strip().lower()
            if not pdb_id:
                continue
            if len(pdb_id) != 4 or not pdb_id.isalnum():
                raise ValueError(f"invalid PDB ID in manifest: {pdb_id!r}")
            paths.append(raw_dir / pdb_id[1:3] / f"{pdb_id}.cif.gz")
    return sorted(set(paths), key=lambda path: path.name)


def _open_gzip_text(path: Path) -> io.TextIOWrapper:
    """Open deterministic UTF-8 gzip text with a stable timestamp header."""
    compressed = gzip.GzipFile(filename=str(path), mode="wb", mtime=0)
    return io.TextIOWrapper(compressed, encoding="utf-8")


def scan(
    raw_dir: Path,
    sifts_csv: Path,
    output: Path,
    errors: Path,
    workers: int,
    pdb_list: Path | None = None,
    shard_id: int = 0,
    shard_count: int = 1,
    limit: int | None = None,
    resume: bool = False,
) -> None:
    if shard_count < 1 or not 0 <= shard_id < shard_count:
        raise ValueError("shard_id must be in [0, shard_count)")
    if workers < 1:
        raise ValueError("workers must be positive")
    chain_map = load_sifts_chain_map(sifts_csv)
    paths = [
        path
        for path in _manifest_paths(raw_dir, pdb_list)
        if _shard_for(path.name.removesuffix(".cif.gz").lower(), shard_count) == shard_id
    ]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        paths = paths[:limit]
    output = _shard_path(output, shard_id, shard_count)
    errors = _shard_path(errors, shard_id, shard_count)
    output.parent.mkdir(parents=True, exist_ok=True)
    errors.parent.mkdir(parents=True, exist_ok=True)
    if resume and output.exists() and errors.exists():
        print(f"resume: output already complete: {output}", flush=True)
        return
    output_part = Path(f"{output}.part")
    errors_part = Path(f"{errors}.part")
    output_part.unlink(missing_ok=True)
    errors_part.unlink(missing_ok=True)
    context = mp.get_context("fork")
    with _open_gzip_text(output_part) as out, errors_part.open(
        "w", encoding="utf-8"
    ) as error_handle:
        with context.Pool(
            processes=workers,
            initializer=_init_worker,
            initargs=(chain_map,),
        ) as pool:
            for index, result in enumerate(pool.imap(_scan_path, paths, chunksize=8), 1):
                if result.get("error"):
                    error_handle.write(json.dumps(result, sort_keys=True) + "\n")
                else:
                    out.write(json.dumps(result, sort_keys=True) + "\n")
                if index % 1000 == 0:
                    out.flush()
                    error_handle.flush()
                    print(f"scanned={index}/{len(paths)}", flush=True)
    os.replace(output_part, output)
    os.replace(errors_part, errors)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--sifts-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--errors", type=Path, required=True)
    parser.add_argument("--pdb-list", type=Path)
    parser.add_argument("--shard-id", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2)
    )
    args = parser.parse_args()
    scan(
        args.raw_dir,
        args.sifts_csv,
        args.output,
        args.errors,
        args.workers,
        pdb_list=args.pdb_list,
        shard_id=args.shard_id,
        shard_count=args.num_shards,
        limit=args.limit,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
