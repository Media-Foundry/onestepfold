import json
from pathlib import Path

import pytest

from fastglycan.gt_catalog import (
    chain_instance_id,
    clean_polymer_sequence,
    resolve_sifts_chain,
    split_asym_ids,
    split_strand_ids,
)


def test_polymer_sequence_and_strand_normalization():
    assert clean_polymer_sequence(";ACD EF\n;") == "ACDEF"
    assert split_strand_ids("'A,B C'") == ("A", "B", "C")


def test_sifts_chain_resolves_via_entity_strand_to_label_asym():
    entities = [
        {
            "_entity_poly.entity_id": "7",
            "_entity_poly.pdbx_strand_id": "AD",
        },
        {
            "_entity_poly.entity_id": "8",
            "_entity_poly.pdbx_strand_id": "B",
        },
    ]
    asym = [
        {"_struct_asym.id": "W", "_struct_asym.entity_id": "7"},
        {"_struct_asym.id": "B", "_struct_asym.entity_id": "8"},
    ]
    assert resolve_sifts_chain("AD", entities, asym) == [
        {"entity_id": "7", "label_asym_id": "W"}
    ]


def test_assembly_chain_list_removes_cif_text_delimiters():
    assert split_asym_ids(";A, B;") == ("A", "B")


def test_assembly_chain_instance_id_is_not_chain_index():
    assert chain_instance_id("A", 0) == "A@1"
    assert chain_instance_id("A", 3) == "A@4"
    with pytest.raises(ValueError):
        chain_instance_id("A", -1)


def test_gt_schema_declares_multichain_identity_fields():
    schema_path = Path(__file__).parents[1] / "schemas" / "gt_schema_v1.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    chain = schema["$defs"]["chain"]
    required = set(chain["required"])
    assert {
        "assembly_chain_instance_id",
        "source_label_asym_id",
        "entity_id",
        "entity_instance_index",
        "operator_path",
        "homomer_group_id",
    } <= required
    assert schema["properties"]["coordinate_view"]["enum"] == [
        "asymmetric_unit",
        "biological_assembly",
    ]


@pytest.mark.skipif(
    __import__("importlib.util").util.find_spec("gemmi") is None,
    reason="Gemmi is installed in the hpc2 data environment, not the minimal local test env",
)
def test_scan_entry_smoke(tmp_path):
    import gzip

    from fastglycan.gt_catalog import scan_entry

    cif = """data_1abc
_entry.id 1abc
loop_
_entity_poly.entity_id
_entity_poly.type
_entity_poly.nstd_linkage
_entity_poly.nstd_monomer
_entity_poly.pdbx_seq_one_letter_code
_entity_poly.pdbx_seq_one_letter_code_can
_entity_poly.pdbx_strand_id
_entity_poly.pdbx_target_identifier
1 'polypeptide(L)' no no ACDE ACDE AD ?
loop_
_struct_asym.id
_struct_asym.pdbx_blank_PDB_chainid_flag
_struct_asym.pdbx_modified
_struct_asym.entity_id
_struct_asym.details
W N N 1 ?
loop_
_exptl.entry_id
_exptl.method
1 'X-RAY DIFFRACTION'
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.type_symbol
_atom_site.label_atom_id
_atom_site.label_alt_id
_atom_site.label_comp_id
_atom_site.label_asym_id
_atom_site.label_entity_id
_atom_site.label_seq_id
_atom_site.pdbx_PDB_ins_code
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
_atom_site.occupancy
_atom_site.B_iso_or_equiv
_atom_site.pdbx_formal_charge
_atom_site.auth_seq_id
_atom_site.auth_comp_id
_atom_site.auth_asym_id
_atom_site.auth_atom_id
_atom_site.pdbx_PDB_model_num
ATOM 1 N N . ALA W 1 1 ? 0 0 0 1.0 10 ? 1 ALA AD N 1
"""
    path = tmp_path / "1abc.cif.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(cif)
    result = scan_entry(
        path,
        [
            {
                "PDB": "1abc",
                "CHAIN": "AD",
                "SP_PRIMARY": "P12345",
            }
        ],
    )
    assert result["chains"][0]["source_label_asym_id"] == "W"
    assert result["chains"][0]["sifts_accessions"] == ["P12345"]
    assert result["experimental"]["methods"] == ["X-RAY DIFFRACTION"]
