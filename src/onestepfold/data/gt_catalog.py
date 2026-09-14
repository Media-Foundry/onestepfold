"""Stage A structure-first catalog scanning for OneStepFold GT v1.

This module intentionally stops at metadata. It does not materialize assembly
coordinates or repair missing residues/atoms. The package name is retained for
backwards compatibility with the original prototype repository.
"""

from __future__ import annotations

import csv
import gzip
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

STANDARD_AMINO_ACIDS = frozenset(
    "ALA CYS ASP GLU PHE GLY HIS ILE LYS LEU MET ASN PRO GLN ARG SER THR VAL TRP TYR".split()
)
PROTEIN_ENTITY_TYPES = frozenset({"polypeptide(l)", "polypeptide(d)"})
NUCLEIC_ENTITY_TYPES = frozenset(
    {"polyribonucleotide", "polydeoxyribonucleotide", "polyribonucleotide/polypeptide"}
)
WATER_CODES = frozenset({"HOH", "DOD", "WAT", "OH2"})
ION_CODES = frozenset(
    {
        "LI", "NA", "K", "RB", "CS", "MG", "CA", "SR", "BA", "ZN", "FE", "MN",
        "CU", "CO", "NI", "CD", "HG", "CL", "BR", "IOD", "I", "F",
    }
)
SCHEMA_VERSION = "gt_catalog_v1"


def _strip_cif_value(value: Any) -> str:
    """Return a scalar mmCIF value without delimiters or null markers."""
    text = "" if value is None else str(value).strip()
    if text in {"", ".", "?"}:
        return ""
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1]
    return text


def clean_polymer_sequence(value: Any) -> str:
    """Normalize an entity polymer sequence without using UniProt sequence."""
    text = _strip_cif_value(value).upper()
    # Semicolon-delimited multiline values and whitespace are formatting only.
    text = text.replace(";", "")
    return "".join(character for character in text if character.isalpha())


def split_strand_ids(value: Any) -> tuple[str, ...]:
    """Split `_entity_poly.pdbx_strand_id` into author chain identifiers."""
    text = _strip_cif_value(value).replace(",", " ")
    return tuple(token for token in re.split(r"\s+", text) if token)


def split_asym_ids(value: Any) -> tuple[str, ...]:
    """Split assembly asym IDs, including semicolon-delimited CIF text blocks."""
    text = _strip_cif_value(value).replace(";", " ").replace(",", " ")
    return tuple(token for token in re.split(r"\s+", text) if token)


def is_protein_entity(entity_type: Any) -> bool:
    """Return whether an mmCIF entity type is a protein polymer."""
    normalized = _strip_cif_value(entity_type).lower()
    return normalized in PROTEIN_ENTITY_TYPES or "polypeptide" in normalized


def is_nucleic_acid_entity(entity_type: Any) -> bool:
    """Return whether an entity type denotes an RNA/DNA polymer."""
    normalized = _strip_cif_value(entity_type).lower()
    return normalized in NUCLEIC_ENTITY_TYPES or "ribonucleotide" in normalized or (
        "deoxyribonucleotide" in normalized
    )


def load_sifts_chain_map(path: Path) -> dict[str, list[dict[str, str]]]:
    """Load SIFTS rows grouped by lower-case PDB identifier.

    SIFTS is provenance and entry discovery here. The chain resolver itself
    uses `pdbx_strand_id`, not a direct lookup into `_struct_asym.id`.
    """
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with gzip.open(path, "rt", newline="") as handle:
        rows = (line for line in handle if not line.startswith("#"))
        reader = csv.DictReader(rows)
        for raw_row in reader:
            row = {
                (key or "").strip().upper(): (value or "").strip()
                for key, value in raw_row.items()
            }
            pdb_id = row.get("PDB", "").lower()
            if len(pdb_id) != 4:
                continue
            grouped[pdb_id].append(row)
    return dict(grouped)


def _normalize_sifts_row(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Convert SIFTS CSV names into the stable provenance schema."""
    aliases = {
        "pdb": ("PDB", "pdb"),
        "chain": ("CHAIN", "chain"),
        "sp_primary": ("SP_PRIMARY", "sp_primary"),
        "res_beg": ("RES_BEG", "res_beg"),
        "res_end": ("RES_END", "res_end"),
        "pdb_beg": ("PDB_BEG", "pdb_beg"),
        "pdb_end": ("PDB_END", "pdb_end"),
        "sp_beg": ("SP_BEG", "sp_beg"),
        "sp_end": ("SP_END", "sp_end"),
    }
    result: dict[str, Any] = {}
    for output_key, input_keys in aliases.items():
        value = ""
        for input_key in input_keys:
            if input_key in raw:
                value = _strip_cif_value(raw[input_key])
                break
        result[output_key] = value or None
    return result


def _category_rows(block: Any, category: str) -> list[dict[str, str]]:
    table = block.find_mmcif_category(category)
    if not table:
        return []
    tags = list(table.tags)
    return [{tag: str(row[index]) for index, tag in enumerate(tags)} for row in table]


def _float_value(value: Any) -> float | None:
    text = _strip_cif_value(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _int_value(value: Any) -> int | None:
    text = _strip_cif_value(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _resolution(block: Any) -> tuple[float | None, list[float]]:
    values: list[float] = []
    for row in _category_rows(block, "_refine"):
        value = _float_value(row.get("_refine.ls_d_res_high"))
        if value is not None:
            values.append(value)
    for row in _category_rows(block, "_em_3d_reconstruction"):
        value = _float_value(row.get("_em_3d_reconstruction.resolution"))
        if value is not None:
            values.append(value)
    return (min(values) if values else None, values)


def _assembly_source(details: str, method_details: str) -> str:
    text = f"{details} {method_details}".lower()
    author = "author" in text
    software = "software" in text or "pisa" in text
    if author and software:
        return "author_and_software"
    if author:
        return "author_determined"
    if software:
        return "software_determined"
    return "unspecified"


def _date_fields(block: Any) -> dict[str, str | None]:
    """Extract deposition and revision dates without consulting UniProt."""
    status_rows = _category_rows(block, "_pdbx_database_status")
    initial_deposition = None
    if status_rows:
        initial_deposition = _strip_cif_value(
            status_rows[0].get("_pdbx_database_status.recvd_initial_deposition_date")
        ) or None
    revisions: list[tuple[str, str]] = []
    for row in _category_rows(block, "_pdbx_audit_revision_history"):
        date = _strip_cif_value(row.get("_pdbx_audit_revision_history.revision_date"))
        if not date:
            continue
        content = _strip_cif_value(
            row.get("_pdbx_audit_revision_history.data_content_type")
        ).lower()
        revisions.append((date, content))
    all_dates = sorted(date for date, _ in revisions)
    structure_dates = sorted(date for date, content in revisions if "structure model" in content)
    return {
        "initial_deposition_date": initial_deposition,
        "initial_release_date": (structure_dates or all_dates or [None])[0],
        "latest_revision_date": (all_dates or [None])[-1],
    }


def _assembly_rows(block: Any) -> list[dict[str, Any]]:
    assemblies = _category_rows(block, "_pdbx_struct_assembly")
    generations = _category_rows(block, "_pdbx_struct_assembly_gen")
    by_id: dict[str, dict[str, Any]] = {}
    for row in assemblies:
        assembly_id = _strip_cif_value(row.get("_pdbx_struct_assembly.id"))
        if not assembly_id:
            continue
        details = _strip_cif_value(row.get("_pdbx_struct_assembly.details"))
        method_details = _strip_cif_value(row.get("_pdbx_struct_assembly.method_details"))
        by_id[assembly_id] = {
            "assembly_id": assembly_id,
            "details": details,
            "method_details": method_details,
            "oligomeric_details": _strip_cif_value(
                row.get("_pdbx_struct_assembly.oligomeric_details")
            ),
            "oligomeric_count": _int_value(row.get("_pdbx_struct_assembly.oligomeric_count")),
            "definition_source": _assembly_source(details, method_details),
            "generations": [],
        }
    for row in generations:
        assembly_id = _strip_cif_value(row.get("_pdbx_struct_assembly_gen.assembly_id"))
        if not assembly_id:
            continue
        record = by_id.setdefault(
            assembly_id,
            {
                "assembly_id": assembly_id,
                "details": "",
                "method_details": "",
                "oligomeric_details": "",
                "oligomeric_count": None,
                "definition_source": "unspecified",
                "generations": [],
            },
        )
        record["generations"].append(
            {
                "oper_expression": _strip_cif_value(
                    row.get("_pdbx_struct_assembly_gen.oper_expression")
                ),
                "asym_id_list": split_asym_ids(
                    row.get("_pdbx_struct_assembly_gen.asym_id_list")
                ),
            }
        )
    for record in by_id.values():
        text = f"{record['details']} {record['method_details']}".lower()
        record["author_determined"] = "author" in text
        record["software_determined"] = "software" in text or "pisa" in text
    return [by_id[key] for key in sorted(by_id)]


def _entity_rows(block: Any) -> dict[str, dict[str, str]]:
    """Load the broad `_entity` category for non-polymer classification."""
    result: dict[str, dict[str, str]] = {}
    for row in _category_rows(block, "_entity"):
        entity_id = _strip_cif_value(row.get("_entity.id"))
        if not entity_id:
            continue
        result[entity_id] = {
            "entity_category": _strip_cif_value(row.get("_entity.type")),
            "entity_description": _strip_cif_value(row.get("_entity.pdbx_description")),
        }
    return result


def _assembly_compositions(
    path: Path,
    assemblies: Iterable[Mapping[str, Any]],
    asym_to_entity: Mapping[str, str],
    entity_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Count generated assembly chain instances using Gemmi, no coordinates stored."""
    try:
        import gemmi

        structure = gemmi.read_structure(str(path))
    except (ImportError, OSError, RuntimeError, ValueError):
        return []

    result: list[dict[str, Any]] = []
    gemmi_assemblies = {str(assembly.name): assembly for assembly in structure.assemblies}
    for record in assemblies:
        assembly = gemmi_assemblies.get(str(record["assembly_id"]))
        if assembly is None:
            continue
        source_protein = source_nucleic = source_other_polymer = 0
        protein_instances = nucleic_instances = other_polymer_instances = 0
        source_asym_ids: set[str] = set()
        operator_count = 0
        for generator in assembly.generators:
            source_ids = list(generator.subchains or generator.chains)
            source_asym_ids.update(source_ids)
            op_count = len(generator.operators)
            operator_count += op_count
            generator_protein = generator_nucleic = generator_other_polymer = 0
            for asym_id in source_ids:
                entity = entity_by_id.get(asym_to_entity.get(asym_id, ""), {})
                entity_type = entity.get("entity_type", "")
                if is_protein_entity(entity_type):
                    generator_protein += 1
                elif is_nucleic_acid_entity(entity_type):
                    generator_nucleic += 1
                elif entity.get("entity_category", "").lower() == "polymer":
                    generator_other_polymer += 1
            source_protein += generator_protein
            source_nucleic += generator_nucleic
            source_other_polymer += generator_other_polymer
            protein_instances += generator_protein * op_count
            nucleic_instances += generator_nucleic * op_count
            other_polymer_instances += generator_other_polymer * op_count
        result.append(
            {
                "assembly_id": str(record["assembly_id"]),
                "source_asym_ids": sorted(source_asym_ids),
                "operator_count": operator_count,
                "polymer_source_asym_count": (
                    source_protein + source_nucleic + source_other_polymer
                ),
                "protein_source_asym_count": source_protein,
                "nucleic_acid_source_asym_count": source_nucleic,
                "other_polymer_source_asym_count": source_other_polymer,
                "polymer_chain_instance_count": (
                    protein_instances + nucleic_instances + other_polymer_instances
                ),
                "protein_chain_instance_count": protein_instances,
                "nucleic_acid_chain_instance_count": nucleic_instances,
                "other_polymer_chain_instance_count": other_polymer_instances,
                "composition_method": "gemmi_generators",
            }
        )
    return result


def _atom_statistics(block: Any, entity_by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Collect compact ASU atom/residue statistics without storing coordinates."""
    table = block.find_mmcif_category("_atom_site")
    if not table:
        return {
            "atom_count": 0,
            "heavy_atom_count": 0,
            "observed_residue_count": {},
            "observed_comp_ids": {},
            "auth_asym_ids": {},
            "altloc_atom_count": 0,
            "altloc_ids": [],
            "occupancy_min": None,
            "model_ids": [],
            "nonprotein_atom_count": 0,
            "nucleic_acid_atom_count": 0,
            "ligand_atom_count": 0,
            "water_atom_count": 0,
            "ion_atom_count": 0,
            "small_molecule_atom_count": 0,
            "other_polymer_atom_count": 0,
            "other_nonprotein_atom_count": 0,
        }
    tags = list(table.tags)
    index = {tag: position for position, tag in enumerate(tags)}

    def get(row: Any, tag: str, default: str = "") -> str:
        position = index.get(tag)
        return str(row[position]) if position is not None else default

    observed_residues: dict[str, set[str]] = defaultdict(set)
    observed_comp_ids: dict[str, set[str]] = defaultdict(set)
    auth_asym_ids: dict[str, set[str]] = defaultdict(set)
    altloc_ids: set[str] = set()
    model_ids: set[str] = set()
    atom_count = heavy_atom_count = altloc_atom_count = 0
    nonprotein = nucleic = ligand = water = ion = small_molecule = 0
    other_polymer = other_nonprotein = 0
    occupancy_min: float | None = None
    for row in table:
        group = _strip_cif_value(get(row, "_atom_site.group_PDB"))
        if group not in {"ATOM", "HETATM"}:
            continue
        atom_count += 1
        label_asym = _strip_cif_value(get(row, "_atom_site.label_asym_id"))
        entity_id = _strip_cif_value(get(row, "_atom_site.label_entity_id"))
        entity = entity_by_id.get(entity_id, {})
        entity_type = str(entity.get("entity_type", "")).lower()
        element = _strip_cif_value(get(row, "_atom_site.type_symbol")).upper()
        if element != "H":
            heavy_atom_count += 1
        if is_protein_entity(entity_type):
            seq_id = _strip_cif_value(get(row, "_atom_site.label_seq_id"))
            if seq_id:
                observed_residues[label_asym].add(seq_id)
            comp_id = _strip_cif_value(get(row, "_atom_site.label_comp_id"))
            if comp_id:
                observed_comp_ids[label_asym].add(comp_id)
        auth_id = _strip_cif_value(get(row, "_atom_site.auth_asym_id"))
        if auth_id:
            auth_asym_ids[label_asym].add(auth_id)
        alt_id = _strip_cif_value(get(row, "_atom_site.label_alt_id"))
        if alt_id:
            altloc_atom_count += 1
            altloc_ids.add(alt_id)
        occupancy = _float_value(get(row, "_atom_site.occupancy"))
        if occupancy is not None:
            occupancy_min = occupancy if occupancy_min is None else min(occupancy_min, occupancy)
        model_id = _strip_cif_value(get(row, "_atom_site.pdbx_PDB_model_num"))
        if model_id:
            model_ids.add(model_id)
        if is_protein_entity(entity_type):
            continue
        nonprotein += 1
        category = str(entity.get("entity_category", "")).lower()
        comp_id = _strip_cif_value(get(row, "_atom_site.label_comp_id")).upper()
        if is_nucleic_acid_entity(entity_type):
            nucleic += 1
        elif category == "water" or comp_id in WATER_CODES:
            water += 1
        elif comp_id in ION_CODES:
            ion += 1
        elif category == "polymer":
            other_polymer += 1
        elif category == "non-polymer":
            small_molecule += 1
            ligand += 1
        else:
            other_nonprotein += 1
    return {
        "atom_count": atom_count,
        "heavy_atom_count": heavy_atom_count,
        "observed_residue_count": {
            key: len(value) for key, value in sorted(observed_residues.items())
        },
        "observed_comp_ids": {
            key: sorted(value) for key, value in sorted(observed_comp_ids.items())
        },
        "auth_asym_ids": {key: sorted(value) for key, value in sorted(auth_asym_ids.items())},
        "altloc_atom_count": altloc_atom_count,
        "altloc_ids": sorted(altloc_ids),
        "occupancy_min": occupancy_min,
        "model_ids": sorted(model_ids),
        "nonprotein_atom_count": nonprotein,
        "nucleic_acid_atom_count": nucleic,
        "ligand_atom_count": ligand,
        "water_atom_count": water,
        "ion_atom_count": ion,
        "small_molecule_atom_count": small_molecule,
        "other_polymer_atom_count": other_polymer,
        "other_nonprotein_atom_count": other_nonprotein,
    }


def resolve_sifts_chain(
    chain_id: str,
    entity_rows: Iterable[Mapping[str, Any]],
    asym_rows: Iterable[Mapping[str, Any]],
    poly_seq_scheme_rows: Iterable[Mapping[str, Any]] = (),
    auth_to_label: Mapping[str, Iterable[str]] | None = None,
) -> list[dict[str, str]]:
    """Resolve one SIFTS author chain to a label asym without entity-wide leakage."""
    chain_id = _strip_cif_value(chain_id)
    valid_asym_ids = {
        _strip_cif_value(row.get("_struct_asym.id"))
        for row in asym_rows
        if _strip_cif_value(row.get("_struct_asym.id"))
    }
    matching_entities = [
        row
        for row in entity_rows
        if chain_id in split_strand_ids(row.get("_entity_poly.pdbx_strand_id"))
    ]
    entity_ids = {
        _strip_cif_value(row.get("_entity_poly.entity_id")) for row in matching_entities
    }

    # This residue-level category is the authoritative author-chain to label-chain map.
    scheme_matches: set[tuple[str, str]] = set()
    for row in poly_seq_scheme_rows:
        if _strip_cif_value(row.get("_pdbx_poly_seq_scheme.pdb_strand_id")) != chain_id:
            continue
        label_asym_id = _strip_cif_value(row.get("_pdbx_poly_seq_scheme.asym_id"))
        entity_id = _strip_cif_value(row.get("_pdbx_poly_seq_scheme.entity_id"))
        if not entity_id:
            entity_id = next(
                (
                    _strip_cif_value(asym.get("_struct_asym.entity_id"))
                    for asym in asym_rows
                    if _strip_cif_value(asym.get("_struct_asym.id")) == label_asym_id
                ),
                "",
            )
        if label_asym_id in valid_asym_ids and (not entity_ids or entity_id in entity_ids):
            scheme_matches.add((entity_id, label_asym_id))
    if scheme_matches:
        return [
            {"entity_id": entity_id, "label_asym_id": label_asym_id}
            for entity_id, label_asym_id in sorted(scheme_matches)
        ]

    candidates = {
        (
            _strip_cif_value(asym.get("_struct_asym.entity_id")),
            _strip_cif_value(asym.get("_struct_asym.id")),
        )
        for asym in asym_rows
        if _strip_cif_value(asym.get("_struct_asym.entity_id")) in entity_ids
    }
    if auth_to_label:
        auth_labels = {
            _strip_cif_value(label)
            for label in auth_to_label.get(chain_id, ())
            if _strip_cif_value(label)
        }
        auth_candidates = {candidate for candidate in candidates if candidate[1] in auth_labels}
        if len(auth_candidates) == 1:
            entity_id, label_asym_id = next(iter(auth_candidates))
            return [{"entity_id": entity_id, "label_asym_id": label_asym_id}]
    # Entity-only fallback is safe only when it identifies one label asym.
    if len(candidates) == 1:
        entity_id, label_asym_id = next(iter(candidates))
        return [{"entity_id": entity_id, "label_asym_id": label_asym_id}]
    return []


def scan_entry(path: Path, sifts_rows: Iterable[Mapping[str, str]] = ()) -> dict[str, Any]:
    """Scan one mmCIF entry into a JSON-serializable catalog record."""
    try:
        import gemmi
    except ImportError as exc:  # pragma: no cover - exercised in deployment env
        raise RuntimeError("Stage A catalog scanning requires the 'gemmi' package") from exc

    pdb_id = path.name.removesuffix(".cif.gz").lower()
    block = gemmi.cif.read_file(str(path)).sole_block()
    entity_rows = _category_rows(block, "_entity_poly")
    broad_entities = _entity_rows(block)
    asym_rows = _category_rows(block, "_struct_asym")
    entity_by_id: dict[str, dict[str, Any]] = {}
    for row in entity_rows:
        entity_id = _strip_cif_value(row.get("_entity_poly.entity_id"))
        if not entity_id:
            continue
        sequence = clean_polymer_sequence(row.get("_entity_poly.pdbx_seq_one_letter_code_can"))
        entity_by_id[entity_id] = {
            "entity_id": entity_id,
            **broad_entities.get(entity_id, {}),
            "entity_type": _strip_cif_value(row.get("_entity_poly.type")),
            "sequence": sequence,
            "sequence_length": len(sequence),
            "strand_ids": split_strand_ids(row.get("_entity_poly.pdbx_strand_id")),
            "nstd_linkage": _strip_cif_value(row.get("_entity_poly.nstd_linkage")),
            "nstd_monomer": _strip_cif_value(row.get("_entity_poly.nstd_monomer")),
        }
    for entity_id, metadata in broad_entities.items():
        entity_by_id.setdefault(
            entity_id,
            {
                "entity_id": entity_id,
                "entity_type": "",
                "sequence": "",
                "sequence_length": 0,
                **metadata,
            },
        )
    asym_to_entity = {
        _strip_cif_value(row.get("_struct_asym.id")): _strip_cif_value(
            row.get("_struct_asym.entity_id")
        )
        for row in asym_rows
        if _strip_cif_value(row.get("_struct_asym.id"))
    }
    scheme_rows = _category_rows(block, "_pdbx_poly_seq_scheme")
    auth_to_label: dict[str, set[str]] = defaultdict(set)
    atom_site = block.find_mmcif_category("_atom_site")
    if atom_site:
        tags = list(atom_site.tags)
        indices = {tag: position for position, tag in enumerate(tags)}
        auth_index = indices.get("_atom_site.auth_asym_id")
        label_index = indices.get("_atom_site.label_asym_id")
        if auth_index is not None and label_index is not None:
            for row in atom_site:
                auth_id = _strip_cif_value(row[auth_index])
                label_id = _strip_cif_value(row[label_index])
                if auth_id and label_id:
                    auth_to_label[auth_id].add(label_id)
    atom_stats = _atom_statistics(block, entity_by_id)
    sifts_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unresolved_sifts: list[dict[str, Any]] = []
    for raw in sifts_rows:
        chain_id = raw.get("CHAIN", raw.get("chain", "")).strip()
        resolved = resolve_sifts_chain(
            chain_id,
            entity_rows,
            asym_rows,
            scheme_rows,
            auth_to_label,
        )
        provenance_row = _normalize_sifts_row(raw)
        if not resolved:
            unresolved_sifts.append(provenance_row)
        for match in resolved:
            sifts_by_label[match["label_asym_id"]].append(provenance_row)

    chains: list[dict[str, Any]] = []
    for asym in asym_rows:
        label_asym_id = _strip_cif_value(asym.get("_struct_asym.id"))
        entity_id = _strip_cif_value(asym.get("_struct_asym.entity_id"))
        entity = entity_by_id.get(entity_id, {})
        entity_type = str(entity.get("entity_type", ""))
        provenance = sifts_by_label.get(label_asym_id, [])
        chains.append(
            {
                "source_label_asym_id": label_asym_id,
                "entity_id": entity_id,
                "entity_category": entity.get("entity_category", ""),
                "entity_type": entity_type,
                "is_protein": is_protein_entity(entity_type),
                "sequence": entity.get("sequence", ""),
                "sequence_length": entity.get("sequence_length", 0),
                "strand_ids": list(entity.get("strand_ids", ())),
                "auth_asym_ids": atom_stats["auth_asym_ids"].get(label_asym_id, []),
                "observed_residue_count": atom_stats["observed_residue_count"].get(
                    label_asym_id, 0
                ),
                "observed_comp_ids": atom_stats["observed_comp_ids"].get(label_asym_id, []),
                "residue_observation_fraction": (
                    atom_stats["observed_residue_count"].get(label_asym_id, 0)
                    / entity["sequence_length"]
                    if entity.get("sequence_length")
                    else None
                ),
                "sifts_accessions": sorted(
                    {
                        row.get("sp_primary") or ""
                        for row in provenance
                        if row.get("sp_primary")
                    }
                ),
                "sifts_provenance": provenance,
            }
        )
    methods = [
        _strip_cif_value(row.get("_exptl.method"))
        for row in _category_rows(block, "_exptl")
        if _strip_cif_value(row.get("_exptl.method"))
    ]
    resolution, resolution_values = _resolution(block)
    assembly_rows = _assembly_rows(block)
    return {
        "schema_version": SCHEMA_VERSION,
        "pdb_id": pdb_id,
        "source_mmcif_filename": path.name,
        "entities": [entity_by_id[key] for key in sorted(entity_by_id)],
        "chains": chains,
        "assemblies": assembly_rows,
        "assembly_compositions": _assembly_compositions(
            path,
            assembly_rows,
            asym_to_entity,
            entity_by_id,
        ),
        "experimental": {
            "methods": sorted(set(methods)),
            "resolution_high_angstrom": resolution,
            "resolution_values_angstrom": resolution_values,
            "model_count": len(atom_stats["model_ids"]),
            "model_ids": atom_stats["model_ids"],
            **_date_fields(block),
        },
        "asu_observations": atom_stats,
        "unresolved_sifts_rows": unresolved_sifts,
    }


def chain_instance_id(source_label_asym_id: str, entity_instance_index: int) -> str:
    """Build a stable human-readable ID for an assembly chain instance."""
    if entity_instance_index < 0:
        raise ValueError("entity_instance_index must be non-negative")
    return f"{source_label_asym_id}@{entity_instance_index + 1}"


def squared_distance(
    first: tuple[float, float, float], second: tuple[float, float, float]
) -> float:
    """Small geometry helper kept independent of a tensor/NumPy dependency."""
    return sum((left - right) ** 2 for left, right in zip(first, second, strict=True))


__all__ = [
    "SCHEMA_VERSION",
    "STANDARD_AMINO_ACIDS",
    "chain_instance_id",
    "clean_polymer_sequence",
    "is_nucleic_acid_entity",
    "is_protein_entity",
    "load_sifts_chain_map",
    "resolve_sifts_chain",
    "scan_entry",
    "split_strand_ids",
    "split_asym_ids",
    "squared_distance",
]
