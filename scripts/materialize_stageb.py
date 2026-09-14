#!/usr/bin/env python3
"""Materialize a Stage B pilot into NPZ/JSON tar shards."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from onestepfold.data.gt_materializer import materialize_entry


def _raw_path(raw_root: Path, pdb_id: str) -> Path:
    return raw_root / pdb_id[:2] / f"{pdb_id}.cif.gz"


def _add_bytes(archive: tarfile.TarFile, name: str, payload: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mtime = 0
    info.mode = 0o644
    archive.addfile(info, io.BytesIO(payload))


def _npz_bytes(arrays: dict[str, np.ndarray]) -> bytes:
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    return buffer.getvalue()


def materialize(
    pilot_path: Path,
    raw_root: Path,
    output_root: Path,
    worker_index: int = 0,
    worker_count: int = 1,
    shard_size: int = 256,
) -> dict[str, Any]:
    with gzip.open(pilot_path, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    rows = sorted(
        (
            row
            for row in rows
            if int.from_bytes(
                hashlib.sha256(row["pdb_id"].encode("ascii")).digest()[:4], "big"
            )
            % worker_count == worker_index
        ),
        key=lambda row: str(row["pdb_id"]),
    )
    shard_dir = output_root / "shards"
    error_dir = output_root / "errors"
    shard_dir.mkdir(parents=True, exist_ok=True)
    error_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_root / f"index-worker-{worker_index:03d}.jsonl.gz"
    errors_path = error_dir / f"worker-{worker_index:03d}.jsonl"
    counts: Counter[str] = Counter()
    index_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    archive: tarfile.TarFile | None = None
    archive_part: Path | None = None
    shard_number = -1
    shard_items = 0

    def open_shard() -> None:
        nonlocal archive, archive_part, shard_number, shard_items
        shard_number += 1
        shard_items = 0
        final_path = shard_dir / f"worker-{worker_index:03d}-shard-{shard_number:04d}.tar"
        archive_part = final_path.with_suffix(".tar.part")
        archive = tarfile.open(archive_part, mode="w")

    def close_shard() -> None:
        nonlocal archive, archive_part
        if archive is not None:
            archive.close()
            assert archive_part is not None
            archive_part.replace(archive_part.with_suffix(""))
            archive = None
            archive_part = None

    for row in rows:
        pdb_id = str(row["pdb_id"])
        try:
            if archive is None or shard_items >= shard_size:
                close_shard()
                open_shard()
            raw_path = _raw_path(raw_root, pdb_id)
            arrays, metadata = materialize_entry(row, raw_path)
            sample_id = str(metadata["sample_id"])
            npz_name = f"{sample_id}.npz"
            json_name = f"{sample_id}.json"
            assert archive is not None
            _add_bytes(archive, npz_name, _npz_bytes(arrays))
            _add_bytes(
                archive,
                json_name,
                (
                    json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n"
                ).encode("utf-8"),
            )
            index_rows.append(
                {
                    "sample_id": sample_id,
                    "pdb_id": pdb_id,
                    "shard": str((archive_part or Path()).with_suffix("")),
                    "npz": npz_name,
                    "metadata": json_name,
                    "pilot_component": row.get("pilot_component"),
                    "pilot_stratum": row.get("pilot_stratum"),
                    "qa": metadata["qa"],
                }
            )
            shard_items += 1
            counts["success"] += 1
        except FileNotFoundError as exc:
            counts["missing_raw"] += 1
            errors.append({"pdb_id": pdb_id, "error_type": "missing_raw", "message": str(exc)})
        except (RuntimeError, ValueError, OSError) as exc:
            counts["parse_or_materialize_error"] += 1
            errors.append({"pdb_id": pdb_id, "error_type": type(exc).__name__, "message": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive taxonomy boundary
            counts["unexpected_error"] += 1
            errors.append({"pdb_id": pdb_id, "error_type": type(exc).__name__, "message": str(exc)})
    close_shard()

    compressed = gzip.GzipFile(filename=str(index_path), mode="wb", mtime=0)
    with io.TextIOWrapper(compressed, encoding="utf-8") as handle:
        for row in index_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    errors_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in errors), encoding="utf-8"
    )
    summary = {
        "pilot": str(pilot_path),
        "raw_root": str(raw_root),
        "worker_index": worker_index,
        "worker_count": worker_count,
        "input_count": len(rows),
        "counts": dict(sorted(counts.items())),
        "index": str(index_path),
        "error_file": str(errors_path),
    }
    (output_root / f"summary-worker-{worker_index:03d}.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--worker-index", type=int, default=0)
    parser.add_argument("--worker-count", type=int, default=1)
    parser.add_argument("--shard-size", type=int, default=256)
    args = parser.parse_args()
    materialize(
        args.pilot,
        args.raw_root,
        args.output_root,
        args.worker_index,
        args.worker_count,
        args.shard_size,
    )


if __name__ == "__main__":
    main()
