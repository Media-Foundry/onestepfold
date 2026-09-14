from pathlib import Path

from onestepfold.data.monomer_filter import MonomerPolicy, classify_catalog_record


def _policy() -> MonomerPolicy:
    return MonomerPolicy(
        protein_chain_instances=1,
        nucleic_acid_chain_instances=0,
        other_polymer_chain_instances=0,
        primary_methods=frozenset({"X-RAY DIFFRACTION"}),
        max_models=1,
        min_length=20,
        max_length=1024,
        allow_water=True,
        allow_ions=True,
        allow_small_molecules=True,
    )


def _record(*, small_molecules=0, nucleic=0, models=1, method="X-RAY DIFFRACTION"):
    return {
        "pdb_id": "1abc",
        "chains": [
            {
                "is_protein": True,
                "source_label_asym_id": "A",
                "entity_id": "1",
                "sequence": "A" * 100,
                "sequence_length": 100,
            }
        ],
        "assemblies": [
            {
                "assembly_id": "1",
                "definition_source": "author_determined",
                "author_determined": True,
                "software_determined": False,
            }
        ],
        "assembly_compositions": [
            {
                "assembly_id": "1",
                "protein_chain_instance_count": 1,
                "nucleic_acid_chain_instance_count": nucleic,
                "other_polymer_chain_instance_count": 0,
            }
        ],
        "experimental": {"methods": [method], "model_count": models},
        "asu_observations": {
            "small_molecule_atom_count": small_molecules,
            "water_atom_count": 1,
            "ion_atom_count": 0,
        },
    }


def test_monomer_clean_allows_small_molecule_context_and_marks_apo_like():
    decision = classify_catalog_record(_record(small_molecules=12), _policy())
    assert decision["classification"] == "monomer_clean"
    assert decision["apo_like_eligible"] is False


def test_monomer_apo_like_is_a_subset_without_small_molecules():
    decision = classify_catalog_record(_record(), _policy())
    assert decision["classification"] == "monomer_clean"
    assert decision["apo_like_eligible"] is True


def test_contextual_and_auxiliary_views_are_not_primary():
    assert classify_catalog_record(_record(nucleic=2), _policy())["classification"] == "contextual"
    assert classify_catalog_record(_record(models=20), _policy())["classification"] == "auxiliary"
    assert (
        classify_catalog_record(_record(method="SOLUTION NMR"), _policy())["classification"]
        == "auxiliary"
    )


def test_policy_loads_frozen_config():
    policy = MonomerPolicy.from_toml(
        Path(__file__).parents[1] / "configs" / "monomer_view_v1.toml"
    )
    assert policy.protein_chain_instances == 1
    assert policy.primary_methods == frozenset(
        {"X-RAY DIFFRACTION", "ELECTRON MICROSCOPY", "NEUTRON DIFFRACTION"}
    )
