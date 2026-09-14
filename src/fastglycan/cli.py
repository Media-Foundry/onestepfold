"""Command-line utilities for data-first project bootstrapping."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import audit_ensembles
from .glycoshape import import_glycoshape
from .io import load_ensembles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fastglycan")
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit", help="validate a weighted ensemble JSONL file")
    audit.add_argument("path", type=Path)
    fetch = subparsers.add_parser(
        "fetch-glycoshape", help="download and unpack one GlycoShape archive"
    )
    fetch.add_argument("glytoucan_id")
    fetch.add_argument("output_dir", type=Path)
    fetch.add_argument("--cluster-level", default="level_1")
    fetch.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "audit":
        report = audit_ensembles(load_ensembles(args.path))
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0 if report.ok else 2
    if args.command == "fetch-glycoshape":
        manifest = import_glycoshape(
            args.glytoucan_id,
            args.output_dir,
            cluster_level=args.cluster_level,
            overwrite=args.overwrite,
        )
        print(
            json.dumps(
                {
                    "glytoucan_id": manifest.glytoucan_id,
                    "model_count": len(manifest.models),
                    "manifest": str(Path(args.output_dir) / args.glytoucan_id / "manifest.json"),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
