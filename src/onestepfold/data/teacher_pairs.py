"""Frozen c2/c4 teacher-pair manifests and lazy coordinate loading.

The manifest keeps exact-sequence groups atomic across train and validation.
Prediction CIF files are parsed only when an example is requested; missing
atoms remain explicitly masked and are never imputed by this loader.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

TEACHER_PAIR_SCHEMA_VERSION = "teacher_pair_manifest_v1"
SPLIT_NAMESPACE = "onestepfold-stage1b-teacher-pairs-v1"
BACKBONE_ATOMS = ("N", "CA", "C", "O")
THREE_TO_ONE = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}


class TeacherPairDataError(ValueError):
    """Raised when a manifest row or prediction pair violates the contract."""


@dataclass(frozen=True)
class TeacherPairRecord:
    """One exact-group teacher pair with paths relative to the output root."""

    group_id: str
    split: str
    shard: str
    sequence: str
    sequence_length: int
    sample_id: str
    c2_cif: str
    c4_cif: str
    c2_confidence: str
    c4_confidence: str
    c2_source: str
    c4_source: str

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> TeacherPairRecord:
        if row.get("schema_version") != TEACHER_PAIR_SCHEMA_VERSION:
            raise TeacherPairDataError(
                f"unsupported teacher-pair schema {row.get('schema_version')!r}"
            )
        record = cls(
            group_id=str(row["group_id"]),
            split=str(row["split"]),
            shard=str(row["shard"]),
            sequence=str(row["sequence"]),
            sequence_length=int(row["sequence_length"]),
            sample_id=str(row["sample_id"]),
            c2_cif=str(row["c2_cif"]),
            c4_cif=str(row["c4_cif"]),
            c2_confidence=str(row["c2_confidence"]),
            c4_confidence=str(row["c4_confidence"]),
            c2_source=str(row["c2_source"]),
            c4_source=str(row["c4_source"]),
        )
        record.validate()
        return record

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": TEACHER_PAIR_SCHEMA_VERSION, **self.__dict__}

    def validate(self) -> None:
        if not self.group_id or not self.sample_id:
            raise TeacherPairDataError("group_id and sample_id must be non-empty")
        if self.split not in {"train", "validation"}:
            raise TeacherPairDataError(f"invalid split {self.split!r}")
        if self.sequence_length != len(self.sequence) or self.sequence_length < 1:
            raise TeacherPairDataError(
                f"sequence length mismatch for group {self.group_id}: "
                f"declared={self.sequence_length}, observed={len(self.sequence)}"
            )
        for value in (
            self.c2_cif,
            self.c4_cif,
            self.c2_confidence,
            self.c4_confidence,
        ):
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts:
                raise TeacherPairDataError(f"artifact path must be relative and contained: {value}")


@dataclass(frozen=True)
class PredictionStructure:
    """Coordinates and explicit backbone masks parsed from one prediction."""

    atom_keys: tuple[tuple[str, int, str], ...]
    positions: Any
    b_factors: Any
    backbone_positions: Any
    backbone_mask: Any


@dataclass(frozen=True)
class TeacherPairExample:
    """A strictly atom-aligned c2/c4 example."""

    record: TeacherPairRecord
    c2: PredictionStructure
    c4: PredictionStructure
    c2_confidence: Mapping[str, Any]
    c4_confidence: Mapping[str, Any]


def split_key(group_id: str, seed: int) -> str:
    """Return the stable ordering key used for the exact-group split."""
    payload = f"{SPLIT_NAMESPACE}:{seed}:{group_id}".encode()
    return hashlib.sha256(payload).hexdigest()


def assign_exact_group_splits(
    rows: Sequence[Mapping[str, Any]], validation_count: int, seed: int
) -> dict[str, str]:
    """Choose an exact-size validation set using a stable hash ordering."""
    group_ids = [str(row["group_id"]) for row in rows]
    if len(group_ids) != len(set(group_ids)):
        duplicates = sorted(group_id for group_id, count in Counter(group_ids).items() if count > 1)
        raise TeacherPairDataError(f"duplicate exact group IDs: {duplicates[:5]}")
    if validation_count < 1 or validation_count >= len(group_ids):
        raise ValueError("validation_count must be positive and smaller than the corpus")
    ordered = sorted(group_ids, key=lambda group_id: (split_key(group_id, seed), group_id))
    validation = set(ordered[:validation_count])
    return {
        group_id: "validation" if group_id in validation else "train"
        for group_id in group_ids
    }


def prediction_relative_paths(
    setting: str, shard: str, group_id: str, seed: int
) -> tuple[str, str]:
    """Return prediction CIF and confidence paths relative to the output root."""
    parent = PurePosixPath(setting, shard, f"seed-{seed}", group_id, f"seed_{seed}", "predictions")
    return (
        str(parent / f"{group_id}_sample_0.cif"),
        str(parent / f"{group_id}_summary_confidence_sample_0.json"),
    )


def build_teacher_pair_records(
    rows: Sequence[Mapping[str, Any]],
    *,
    validation_count: int,
    seed: int,
    c2_sources: Mapping[str, str],
    c4_sources: Mapping[str, str],
) -> list[TeacherPairRecord]:
    """Build deterministic manifest records from frozen teacher input metadata."""
    splits = assign_exact_group_splits(rows, validation_count, seed)
    records: list[TeacherPairRecord] = []
    for row in sorted(rows, key=lambda item: str(item["group_id"])):
        group_id = str(row["group_id"])
        shard = str(row["teacher_shard"])
        try:
            c2_source = c2_sources[shard]
            c4_source = c4_sources[shard]
        except KeyError as exc:
            raise TeacherPairDataError(f"missing source provenance for {shard}") from exc
        c2_cif, c2_confidence = prediction_relative_paths("c2_s2", shard, group_id, seed)
        c4_cif, c4_confidence = prediction_relative_paths("c4_s2", shard, group_id, seed)
        record = TeacherPairRecord(
            group_id=group_id,
            split=splits[group_id],
            shard=shard,
            sequence=str(row["sequence"]),
            sequence_length=int(row["sequence_length"]),
            sample_id=str(row["sample_id"]),
            c2_cif=c2_cif,
            c4_cif=c4_cif,
            c2_confidence=c2_confidence,
            c4_confidence=c4_confidence,
            c2_source=c2_source,
            c4_source=c4_source,
        )
        record.validate()
        records.append(record)
    return records


def write_teacher_pair_manifest(path: Path, records: Sequence[TeacherPairRecord]) -> str:
    """Atomically write a deterministic gzip JSONL manifest and return SHA256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as compressed:
            for record in records:
                line = json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":")) + "\n"
                compressed.write(line.encode("utf-8"))
    temporary.replace(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iter_teacher_pair_manifest(
    path: Path, *, split: str | None = None
) -> Iterator[TeacherPairRecord]:
    """Yield validated, unique records from a gzip JSONL manifest."""
    if split not in {None, "train", "validation"}:
        raise ValueError("split must be train, validation, or None")
    seen: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = TeacherPairRecord.from_dict(json.loads(line))
            except Exception as exc:
                raise TeacherPairDataError(f"invalid manifest row {line_number}: {exc}") from exc
            if record.group_id in seen:
                raise TeacherPairDataError(f"duplicate group_id {record.group_id} in manifest")
            seen.add(record.group_id)
            if split is None or record.split == split:
                yield record


def load_teacher_pair_manifest(
    path: Path, *, split: str | None = None
) -> list[TeacherPairRecord]:
    return list(iter_teacher_pair_manifest(path, split=split))


def _require_data_dependencies() -> tuple[Any, Any]:
    try:
        import gemmi
        import numpy as np
    except ImportError as exc:  # pragma: no cover - depends on optional installation
        raise ImportError("teacher-pair coordinate loading requires onestepfold[data]") from exc
    return gemmi, np


def _finite_numbers(value: Any) -> bool:
    if isinstance(value, Mapping):
        return all(_finite_numbers(item) for item in value.values())
    if isinstance(value, list):
        return all(_finite_numbers(item) for item in value)
    return not isinstance(value, (int, float)) or isinstance(value, bool) or math.isfinite(value)


def load_confidence(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not _finite_numbers(payload):
        raise TeacherPairDataError(f"invalid confidence JSON: {path}")
    return payload


def parse_prediction_cif(
    path: Path, *, sequence: str, sequence_length: int
) -> PredictionStructure:
    """Parse a monomer prediction without filling missing atoms."""
    gemmi, np = _require_data_dependencies()
    block = gemmi.cif.read_file(str(path)).sole_block()
    table = block.find_mmcif_category("_atom_site.")
    tags = [str(tag) for tag in table.tags]
    required = (
        "_atom_site.group_PDB",
        "_atom_site.label_atom_id",
        "_atom_site.label_alt_id",
        "_atom_site.label_comp_id",
        "_atom_site.label_asym_id",
        "_atom_site.label_seq_id",
        "_atom_site.B_iso_or_equiv",
        "_atom_site.Cartn_x",
        "_atom_site.Cartn_y",
        "_atom_site.Cartn_z",
        "_atom_site.pdbx_PDB_model_num",
    )
    missing_tags = sorted(set(required) - set(tags))
    if missing_tags:
        raise TeacherPairDataError(f"{path} lacks atom_site tags {missing_tags}")
    index = {tag: tags.index(tag) for tag in required}
    atoms: dict[tuple[str, int, str], tuple[tuple[float, float, float], float, str]] = {}
    residues: dict[tuple[str, int], str] = {}
    for row in table:
        if row[index["_atom_site.group_PDB"]] != "ATOM":
            continue
        if row[index["_atom_site.pdbx_PDB_model_num"]] != "1":
            continue
        alt_id = row[index["_atom_site.label_alt_id"]]
        if alt_id not in {".", "?"}:
            raise TeacherPairDataError(f"unexpected alternate location {alt_id!r} in {path}")
        chain = row[index["_atom_site.label_asym_id"]]
        residue_id = int(row[index["_atom_site.label_seq_id"]])
        atom_name = row[index["_atom_site.label_atom_id"]]
        residue_name = row[index["_atom_site.label_comp_id"]]
        key = (chain, residue_id, atom_name)
        if key in atoms:
            raise TeacherPairDataError(f"duplicate atom key {key} in {path}")
        xyz = tuple(float(row[index[tag]]) for tag in (
            "_atom_site.Cartn_x",
            "_atom_site.Cartn_y",
            "_atom_site.Cartn_z",
        ))
        b_factor = float(row[index["_atom_site.B_iso_or_equiv"]])
        if not all(math.isfinite(value) for value in (*xyz, b_factor)):
            raise TeacherPairDataError(f"non-finite atom values for {key} in {path}")
        atoms[key] = (xyz, b_factor, residue_name)
        previous = residues.setdefault((chain, residue_id), residue_name)
        if previous != residue_name:
            raise TeacherPairDataError(f"inconsistent residue name for {(chain, residue_id)}")
    if not atoms:
        raise TeacherPairDataError(f"no model-1 ATOM rows in {path}")
    chains = {chain for chain, _ in residues}
    if len(chains) != 1:
        raise TeacherPairDataError(
            f"expected one predicted protein chain in {path}, found {chains}"
        )
    chain = next(iter(chains))
    residue_ids = sorted(residue_id for asym, residue_id in residues if asym == chain)
    if residue_ids != list(range(1, sequence_length + 1)):
        raise TeacherPairDataError(f"residue numbering/length mismatch in {path}")
    try:
        observed_sequence = "".join(THREE_TO_ONE[residues[(chain, i)]] for i in residue_ids)
    except KeyError as exc:
        raise TeacherPairDataError(
            f"unsupported predicted residue {exc.args[0]!r} in {path}"
        ) from exc
    if observed_sequence != sequence:
        raise TeacherPairDataError(f"predicted sequence mismatch in {path}")

    atom_keys = tuple(sorted(atoms, key=lambda item: (item[0], item[1], item[2])))
    positions = np.asarray([atoms[key][0] for key in atom_keys], dtype=np.float32)
    b_factors = np.asarray([atoms[key][1] for key in atom_keys], dtype=np.float32)
    backbone_positions = np.full((sequence_length, len(BACKBONE_ATOMS), 3), np.nan, np.float32)
    backbone_mask = np.zeros((sequence_length, len(BACKBONE_ATOMS)), dtype=np.bool_)
    for residue_id in residue_ids:
        for atom_index, atom_name in enumerate(BACKBONE_ATOMS):
            value = atoms.get((chain, residue_id, atom_name))
            if value is not None:
                backbone_positions[residue_id - 1, atom_index] = value[0]
                backbone_mask[residue_id - 1, atom_index] = True
    return PredictionStructure(
        atom_keys=atom_keys,
        positions=positions,
        b_factors=b_factors,
        backbone_positions=backbone_positions,
        backbone_mask=backbone_mask,
    )


def load_teacher_pair(record: TeacherPairRecord, output_root: Path) -> TeacherPairExample:
    """Load and strictly align both settings for one manifest record."""
    c2 = parse_prediction_cif(
        output_root / record.c2_cif,
        sequence=record.sequence,
        sequence_length=record.sequence_length,
    )
    c4 = parse_prediction_cif(
        output_root / record.c4_cif,
        sequence=record.sequence,
        sequence_length=record.sequence_length,
    )
    if c2.atom_keys != c4.atom_keys:
        only_c2 = sorted(set(c2.atom_keys) - set(c4.atom_keys))[:5]
        only_c4 = sorted(set(c4.atom_keys) - set(c2.atom_keys))[:5]
        raise TeacherPairDataError(
            f"atom-key mismatch for {record.group_id}: only_c2={only_c2}, only_c4={only_c4}"
        )
    c2_confidence = load_confidence(output_root / record.c2_confidence)
    c4_confidence = load_confidence(output_root / record.c4_confidence)
    if c2_confidence.get("num_recycles") != 2:
        raise TeacherPairDataError(f"c2 num_recycles mismatch for {record.group_id}")
    if c4_confidence.get("num_recycles") != 4:
        raise TeacherPairDataError(f"c4 num_recycles mismatch for {record.group_id}")
    return TeacherPairExample(
        record=record,
        c2=c2,
        c4=c4,
        c2_confidence=c2_confidence,
        c4_confidence=c4_confidence,
    )


class TeacherPairDataset(Sequence[TeacherPairExample]):
    """Lazy sequence-like view over a frozen teacher-pair manifest."""

    def __init__(self, records: Sequence[TeacherPairRecord], output_root: Path) -> None:
        self.records = tuple(records)
        self.output_root = Path(output_root)

    @classmethod
    def from_manifest(
        cls, manifest_path: Path, output_root: Path, *, split: str | None = None
    ) -> TeacherPairDataset:
        return cls(load_teacher_pair_manifest(manifest_path, split=split), output_root)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> TeacherPairExample:
        return load_teacher_pair(self.records[index], self.output_root)
