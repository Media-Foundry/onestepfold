"""Gemmi-backed Stage B materialization for the structure-first GT contract."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

ATOM37_NAMES = (
    "N",
    "CA",
    "C",
    "CB",
    "O",
    "CG",
    "CG1",
    "CG2",
    "OG",
    "OG1",
    "SG",
    "CD",
    "CD1",
    "CD2",
    "ND1",
    "ND2",
    "OD1",
    "OD2",
    "SD",
    "CE",
    "CE1",
    "CE2",
    "CE3",
    "NE",
    "NE1",
    "NE2",
    "OE1",
    "OE2",
    "CH2",
    "NH1",
    "NH2",
    "OH",
    "CZ",
    "CZ2",
    "CZ3",
    "NZ",
    "OXT",
)
ATOM37_INDEX = {name: index for index, name in enumerate(ATOM37_NAMES)}
BACKBONE_NAMES = frozenset({"N", "CA", "C", "O"})
STANDARD_AA = frozenset("ACDEFGHIKLMNPQRSTVWY")
CANONICAL_ATOMS: dict[str, frozenset[str]] = {
    "A": frozenset("N CA C CB O".split()),
    "R": frozenset("N CA C CB O CG CD NE CZ NH1 NH2".split()),
    "N": frozenset("N CA C CB O CG OD1 ND2".split()),
    "D": frozenset("N CA C CB O CG OD1 OD2".split()),
    "C": frozenset("N CA C CB O SG".split()),
    "Q": frozenset("N CA C CB O CG CD OE1 NE2".split()),
    "E": frozenset("N CA C CB O CG CD OE1 OE2".split()),
    "G": frozenset("N CA C O".split()),
    "H": frozenset("N CA C CB O CG ND1 CD2 CE1 NE2".split()),
    "I": frozenset("N CA C CB O CG1 CG2 CD1".split()),
    "L": frozenset("N CA C CB O CG CD1 CD2".split()),
    "K": frozenset("N CA C CB O CG CD CE NZ".split()),
    "M": frozenset("N CA C CB O CG SD CE".split()),
    "F": frozenset("N CA C CB O CG CD1 CD2 CE1 CE2 CZ".split()),
    "P": frozenset("N CA C CB O CG CD".split()),
    "S": frozenset("N CA C CB O OG".split()),
    "T": frozenset("N CA C CB O OG1 CG2".split()),
    "W": frozenset("N CA C CB O CG CD1 CD2 NE1 CE2 CE3 CZ2 CZ3 CH2".split()),
    "Y": frozenset("N CA C CB O CG CD1 CD2 CE1 CE2 CZ OH".split()),
    "V": frozenset("N CA C CB O CG1 CG2".split()),
}


def _clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if text in {"", ".", "?", "\x00"}:
        return ""
    return text.strip("'\"")


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(_clean(value))
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(_clean(value))
    except (TypeError, ValueError):
        return default


def _atom_rows(block: Any, source_asym: str) -> list[dict[str, Any]]:
    table = block.find_mmcif_category("_atom_site")
    if not table:
        return []
    tags = list(table.tags)
    index = {tag: position for position, tag in enumerate(tags)}

    def get(row: Any, tag: str, default: str = "") -> str:
        position = index.get(tag)
        return str(row[position]) if position is not None else default

    result: list[dict[str, Any]] = []
    for row in table:
        if _clean(get(row, "_atom_site.label_asym_id")) != source_asym:
            continue
        if _clean(get(row, "_atom_site.group_PDB")) not in {"ATOM", "HETATM"}:
            continue
        if _int(get(row, "_atom_site.pdbx_PDB_model_num"), 1) != 1:
            continue
        label_seq_id = _int(get(row, "_atom_site.label_seq_id"))
        if label_seq_id is None or label_seq_id < 1:
            continue
        element = _clean(get(row, "_atom_site.type_symbol")).upper()
        atom_name = _clean(get(row, "_atom_site.label_atom_id")).upper()
        if element == "H" or atom_name not in ATOM37_INDEX:
            continue
        result.append(
            {
                "label_seq_id": label_seq_id,
                "auth_seq_id": _clean(get(row, "_atom_site.auth_seq_id")) or None,
                "insertion_code": _clean(get(row, "_atom_site.pdbx_PDB_ins_code")) or None,
                "comp_id": _clean(get(row, "_atom_site.label_comp_id")).upper(),
                "atom_name": atom_name,
                "altloc": _clean(get(row, "_atom_site.label_alt_id")),
                "occupancy": _float(get(row, "_atom_site.occupancy"), 1.0),
                "x": _float(get(row, "_atom_site.Cartn_x")),
                "y": _float(get(row, "_atom_site.Cartn_y")),
                "z": _float(get(row, "_atom_site.Cartn_z")),
                "auth_asym_id": _clean(get(row, "_atom_site.auth_asym_id")),
            }
        )
    return result


def _operator_for_source(
    structure: Any, assembly_id: str, source_asym: str
) -> tuple[Any, list[str]]:
    """Return the unique assembly operator for a selected monomer source chain."""
    identity = None
    try:
        import gemmi

        identity = gemmi.Transform()
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise RuntimeError("Stage B requires gemmi") from exc
    if not assembly_id:
        return identity, []
    assembly = next(
        (item for item in structure.assemblies if str(item.name) == str(assembly_id)), None
    )
    if assembly is None:
        return identity, []
    matches = []
    for generator in assembly.generators:
        sources = list(generator.subchains or generator.chains)
        if source_asym in sources:
            matches.extend(generator.operators)
    if not matches:
        return identity, []
    operator = sorted(matches, key=lambda item: str(item.name))[0]
    return operator.transform, [str(operator.name)]


def _select_altloc(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None, float | None]:
    nonblank = defaultdict(float)
    for row in rows:
        if row["altloc"]:
            nonblank[row["altloc"]] += max(row["occupancy"], 0.0)
    selected = None
    fraction = None
    if nonblank:
        selected = sorted(nonblank, key=lambda key: (-nonblank[key], key))[0]
        total = sum(nonblank.values())
        fraction = nonblank[selected] / total if total else None
    filtered = [row for row in rows if not row["altloc"] or row["altloc"] == selected]
    by_atom: dict[str, dict[str, Any]] = {}
    for row in filtered:
        previous = by_atom.get(row["atom_name"])
        if previous is None or (row["occupancy"], row["altloc"]) > (
            previous["occupancy"],
            previous["altloc"],
        ):
            by_atom[row["atom_name"]] = row
    return list(by_atom.values()), selected, fraction


def _apply_transform(transform: Any, x: float, y: float, z: float) -> tuple[float, float, float]:
    import gemmi

    position = transform.apply(gemmi.Position(x, y, z))
    return float(position.x), float(position.y), float(position.z)


def _geometry_qa(
    positions: np.ndarray, mask: np.ndarray, residue_mask: np.ndarray
) -> dict[str, Any]:
    name = ATOM37_INDEX

    def distance(residue_a: int, atom_a: str, residue_b: int, atom_b: str) -> float | None:
        ia, ib = name[atom_a], name[atom_b]
        if not (mask[residue_a, ia] and mask[residue_b, ib]):
            return None
        return float(np.linalg.norm(positions[residue_a, ia] - positions[residue_b, ib]))

    bond_outliers = peptide_outliers = chain_breaks = chirality = 0
    for index in range(len(residue_mask)):
        for left, right, low, high in (
            ("N", "CA", 1.15, 1.65),
            ("CA", "C", 1.15, 1.75),
            ("C", "O", 1.0, 1.45),
        ):
            value = distance(index, left, index, right)
            bond_outliers += int(value is not None and not low <= value <= high)
        if all(mask[index, name[atom]] for atom in ("N", "CA", "C", "CB")):
            n, ca, c, cb = (positions[index, name[atom]] for atom in ("N", "CA", "C", "CB"))
            volume = float(np.dot(np.cross(n - ca, c - ca), cb - ca))
            chirality += int(volume <= 0.1)
        if index + 1 < len(residue_mask):
            peptide = distance(index, "C", index + 1, "N")
            peptide_outliers += int(peptide is not None and not 1.1 <= peptide <= 1.6)
            ca_distance = distance(index, "CA", index + 1, "CA")
            chain_breaks += int(ca_distance is not None and not 2.8 <= ca_distance <= 4.5)
    clash_count = 0
    try:
        from scipy.spatial import cKDTree

        valid = np.argwhere(mask)
        if len(valid):
            coordinates = positions[mask]
            tree = cKDTree(coordinates)
            for first, second in tree.query_pairs(2.0):
                if abs(int(valid[first, 0]) - int(valid[second, 0])) > 1:
                    clash_count += 1
    except ImportError:  # pragma: no cover - scipy is a deployment extra
        pass
    return {
        "bond_length_outlier_count": bond_outliers,
        "peptide_bond_outlier_count": peptide_outliers,
        "chirality_violation_count": chirality,
        "steric_clash_count": clash_count,
        "chain_break_count": chain_breaks,
    }


def materialize_entry(
    row: Mapping[str, Any], raw_path: Path
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Materialize one selected entry into arrays and compact metadata."""
    try:
        import gemmi
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise RuntimeError("Stage B requires gemmi") from exc
    structure = gemmi.read_structure(str(raw_path))
    block = gemmi.cif.read_file(str(raw_path)).sole_block()
    source_asym = str(row["source_label_asym_id"])
    sequence = str(row["sequence"])
    length = len(sequence)
    transform, operator_path = _operator_for_source(
        structure, str(row.get("assembly_id") or ""), source_asym
    )
    rows_by_residue: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for atom in _atom_rows(block, source_asym):
        rows_by_residue[atom["label_seq_id"]].append(atom)

    positions = np.zeros((length, len(ATOM37_NAMES), 3), dtype=np.float32)
    mask = np.zeros((length, len(ATOM37_NAMES)), dtype=np.bool_)
    residue_metadata: list[dict[str, Any]] = []
    observed = np.zeros(length, dtype=np.bool_)
    selected_altlocs: set[str] = set()
    modified_count = 0
    auth_asym_ids = sorted(
        {
            atom["auth_asym_id"]
            for atoms in rows_by_residue.values()
            for atom in atoms
            if atom["auth_asym_id"]
        }
    )
    for index in range(length):
        label_seq_id = index + 1
        selected_rows, altloc, alt_fraction = _select_altloc(rows_by_residue.get(label_seq_id, []))
        if altloc:
            selected_altlocs.add(altloc)
        comp_ids = sorted({atom["comp_id"] for atom in selected_rows if atom["comp_id"]})
        comp_id = comp_ids[0] if comp_ids else ("UNK" if not sequence[index] else sequence[index])
        modified = comp_id not in {
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
        modified_count += int(modified)
        expected = CANONICAL_ATOMS.get(sequence[index], frozenset())
        if index == length - 1 and sequence[index] in CANONICAL_ATOMS:
            expected = expected | {"OXT"}
        by_name = {atom["atom_name"]: atom for atom in selected_rows}
        for atom_name, atom in by_name.items():
            if atom_name not in expected or (modified and atom_name not in BACKBONE_NAMES):
                continue
            x, y, z = _apply_transform(transform, atom["x"], atom["y"], atom["z"])
            atom_index = ATOM37_INDEX[atom_name]
            positions[index, atom_index] = (x, y, z)
            mask[index, atom_index] = True
        observed[index] = bool(mask[index].any())
        source = selected_rows[0] if selected_rows else {}
        residue_metadata.append(
            {
                "label_seq_id": label_seq_id,
                "auth_seq_id": source.get("auth_seq_id"),
                "insertion_code": source.get("insertion_code"),
                "comp_id": comp_id,
                "aatype": sequence[index],
                "is_modified_residue": modified,
                "selected_altloc": altloc,
                "altloc_fraction": alt_fraction,
            }
        )

    missing = ~observed
    leading = 0
    while leading < length and missing[leading]:
        leading += 1
    trailing = 0
    while trailing < length - leading and missing[length - trailing - 1]:
        trailing += 1
    internal = missing[leading : length - trailing if trailing else length]
    longest_internal = current = 0
    for value in internal:
        current = current + 1 if value else 0
        longest_internal = max(longest_internal, current)
    expected_count = sum(
        len(CANONICAL_ATOMS.get(letter, ())) + int(index == length - 1)
        for index, letter in enumerate(sequence)
    )
    observed_count = int(mask.sum())
    frame_count = int(
        np.all(mask[:, [ATOM37_INDEX[name] for name in ("N", "CA", "C")]], axis=1).sum()
    )
    backbone4_count = int(
        np.all(mask[:, [ATOM37_INDEX[name] for name in ("N", "CA", "C", "O")]], axis=1).sum()
    )
    qa = {
        "observed_residue_fraction": float(observed.mean()) if length else 0.0,
        "frame_coverage": frame_count / length if length else 0.0,
        "backbone4_coverage": backbone4_count / length if length else 0.0,
        "heavy_atom_coverage": observed_count / expected_count if expected_count else 0.0,
        "terminal_missing_fraction": (leading + trailing) / length if length else 0.0,
        "internal_missing_fraction": int(missing.sum() - leading - trailing) / length
        if length
        else 0.0,
        "longest_internal_missing_run": longest_internal,
        "modified_residue_count": modified_count,
        "selected_altlocs": sorted(selected_altlocs),
        "finite_coordinate_violation_count": int(
            np.isfinite(positions[mask]).all(axis=1).sum() != int(mask.sum())
        ),
    }
    qa.update(_geometry_qa(positions, mask, np.ones(length, dtype=np.bool_)))
    chain_record = row.get("chain_record", {})
    hidden = row.get("asu_observations", {})
    metadata = {
        "schema_version": "gt_schema_v1",
        "sample_id": f"{row['pdb_id']}.assembly-{row.get('assembly_id') or 'asu'}.model-1",
        "pdb_id": row["pdb_id"],
        "coordinate_view": "biological_assembly" if row.get("assembly_id") else "asymmetric_unit",
        "assembly_id": row.get("assembly_id"),
        "model_id": 1,
        "assembly_definition_source": row.get("assembly_definition_source", "unspecified"),
        "assembly_author_determined": row.get("assembly_definition_source") == "author_determined",
        "assembly_software_determined": row.get("assembly_definition_source")
        in {"software_determined", "author_and_software"},
        "atom_vocabulary": "atom37_heavy_v1",
        "chains": [
            {
                "assembly_chain_instance_id": f"{source_asym}@1",
                "chain_index": 0,
                "source_label_asym_id": source_asym,
                "auth_asym_ids": auth_asym_ids,
                "entity_id": str(row.get("entity_id") or chain_record.get("entity_id") or ""),
                "entity_category": "polymer",
                "entity_instance_index": 0,
                "homomer_group_id": str(
                    row.get("entity_id") or chain_record.get("entity_id") or source_asym
                ),
                "operator_path": operator_path,
                "sequence": sequence,
                "sequence_length": length,
                "residues": residue_metadata,
                "sifts_provenance": chain_record.get("sifts_provenance", []),
            }
        ],
        "chain_pair_interfaces": [],
        "experimental": {
            "methods": row.get("experimental_methods", []),
            "resolution_high_angstrom": row.get("resolution_high_angstrom"),
            "model_id": 1,
            "model_count": int(row.get("model_count", 1)),
            "initial_deposition_date": None,
            "initial_release_date": row.get("initial_release_date"),
            "latest_revision_date": None,
            "r_work": None,
            "r_free": None,
        },
        "hidden_context": {
            "nonprotein_atom_count": int(hidden.get("nonprotein_atom_count", 0)),
            "nucleic_acid_atom_count": int(hidden.get("nucleic_acid_atom_count", 0)),
            "ligand_atom_count": int(
                hidden.get("ligand_atom_count", hidden.get("small_molecule_atom_count", 0))
            ),
            "water_atom_count": int(hidden.get("water_atom_count", 0)),
            "ion_atom_count": int(hidden.get("ion_atom_count", 0)),
            "small_molecule_atom_count": int(hidden.get("small_molecule_atom_count", 0)),
            "other_polymer_atom_count": int(hidden.get("other_polymer_atom_count", 0)),
            "other_nonprotein_atom_count": int(hidden.get("other_nonprotein_atom_count", 0)),
            "ligand_bridges_protein_chains": False,
        },
        "provenance": {
            "source_mmcif_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
            "source_mmcif_filename": raw_path.name,
            "parser_version": f"gemmi-{gemmi.__version__}",
            "protocol_version": "gt_protocol_v1",
        },
        "qa": qa,
        "tensor_fields": {
            "npz": [
                "aatype",
                "residue_index",
                "atom37_positions",
                "atom37_mask",
                "residue_mask",
                "chain_index",
            ]
        },
    }
    aa_to_index = {letter: index for index, letter in enumerate("ACDEFGHIKLMNPQRSTVWY")}
    arrays = {
        "aatype": np.asarray([aa_to_index.get(letter, 20) for letter in sequence], dtype=np.int8),
        "residue_index": np.arange(1, length + 1, dtype=np.int32),
        "atom37_positions": positions,
        "atom37_mask": mask,
        "residue_mask": np.ones(length, dtype=np.bool_),
        "chain_index": np.zeros(length, dtype=np.int16),
    }
    return arrays, metadata


__all__ = ["ATOM37_NAMES", "CANONICAL_ATOMS", "materialize_entry"]
