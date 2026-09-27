"""Provenance and acceptance checks for the bounded paired-teacher intervention."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROTOCOL_VERSION = "hpc3-paired-teacher-v2-pilot512x256"
PARENT_MANIFEST_SHA256 = "084fbc88f8302eb770a021e593ff94b47a76e48cc38b079c96f00c58e7188325"
ESMC_MANIFEST_SHA256 = "a751c1581137248c4e3de75da4c0994d3c51c790bda547af4a0ea202355f0ba1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def balanced_partitions(records, count: int):
    """Greedy L-squared scheduling, with each worker's longest example first."""
    if count < 1 or count > len(records):
        raise ValueError("invalid worker count")
    partitions = [[] for _ in range(count)]
    costs = [0] * count
    for record in sorted(records, key=lambda r: (-r.sequence_length, r.group_id)):
        index = min(range(count), key=lambda i: (costs[i], i))
        partitions[index].append(record)
        costs[index] += record.sequence_length**2
    return partitions


def validate_pair_traces(c2, c4, *, diffusion_seed=12345):
    """Reject uncontrolled or mismatched feature/noise conditions."""
    for events, cycles in ((c2, 2), (c4, 4)):
        if len(events) != 2:
            raise ValueError("expected one trunk and one diffusion event")
        trunk, diffusion = events
        if (trunk["kind"], trunk["cycles"], trunk["mc_dropout"]) != ("trunk", cycles, False):
            raise ValueError("incorrect recycle count or MC dropout enabled")
        if diffusion["kind"] != "diffusion" or diffusion["explicit_seed"] != diffusion_seed:
            raise ValueError("missing shared diffusion seed")
    for key in ("input_feature_sha256", "rng_before"):
        if c2[0][key] != c4[0][key]:
            raise ValueError(f"paired trunk mismatch: {key}")
    if c2[1]["rng_at_sampler_entry"] != c4[1]["rng_at_sampler_entry"]:
        raise ValueError("paired sampler RNG mismatch")


def accepted_protocol_hash(teacher_root: Path, manifest: Path) -> str | None:
    """Bind derived data to an accepted protocol; old corpora retain their contract."""
    control = teacher_root / "control"
    protocol_path = control / "paired_teacher_protocol.json"
    if not protocol_path.exists():
        return None
    protocol_hash = sha256(protocol_path)
    protocol = json.loads(protocol_path.read_text())
    acceptance = json.loads((control / "paired_teacher_acceptance.json").read_text())
    if protocol["schema_version"] != PROTOCOL_VERSION:
        raise ValueError("unsupported paired-teacher protocol")
    if not acceptance.get("complete") or acceptance["protocol_sha256"] != protocol_hash:
        raise ValueError("paired-teacher protocol is not accepted")
    if acceptance["manifest_sha256"] != sha256(manifest):
        raise ValueError("accepted paired-teacher manifest changed")
    if acceptance["split_counts"] != {"train": 512, "validation": 256}:
        raise ValueError("paired-teacher acceptance has incorrect group counts")
    return protocol_hash
