"""Catalog-only monomer view selection for OneStepFold v1."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MonomerPolicy:
    """Structural eligibility policy; quality thresholds are Stage B concerns."""

    protein_chain_instances: int
    nucleic_acid_chain_instances: int
    other_polymer_chain_instances: int
    primary_methods: frozenset[str]
    max_models: int
    min_length: int
    max_length: int
    allow_water: bool
    allow_ions: bool
    allow_small_molecules: bool

    @classmethod
    def from_toml(cls, path: Path) -> MonomerPolicy:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        assembly = data["assembly"]
        method = data["method"]
        models = data["models"]
        sequence = data["sequence"]
        context = data["context"]
        return cls(
            protein_chain_instances=int(assembly["protein_chain_instances"]),
            nucleic_acid_chain_instances=int(assembly["nucleic_acid_chain_instances"]),
            other_polymer_chain_instances=int(assembly["other_polymer_chain_instances"]),
            primary_methods=frozenset(str(value).upper() for value in method["primary"]),
            max_models=int(models["max_models"]),
            min_length=int(sequence["min_length"]),
            max_length=int(sequence["max_length"]),
            allow_water=bool(context["allow_water"]),
            allow_ions=bool(context["allow_ions"]),
            allow_small_molecules=bool(context["allow_small_molecules"]),
        )


def _assembly_source_rank(assembly: Mapping[str, Any]) -> tuple[int, str]:
    if assembly.get("author_determined"):
        return (0, str(assembly.get("assembly_id", "")))
    if assembly.get("software_determined"):
        return (1, str(assembly.get("assembly_id", "")))
    return (2, str(assembly.get("assembly_id", "")))


def _composition_candidates(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    assemblies = {
        str(row.get("assembly_id")): row for row in record.get("assemblies", [])
    }
    candidates: list[dict[str, Any]] = []
    for composition in record.get("assembly_compositions", []):
        assembly_id = str(composition.get("assembly_id", ""))
        source = assemblies.get(assembly_id, {})
        candidates.append(
            {
                **composition,
                "assembly_id": assembly_id,
                "definition_source": source.get("definition_source", "unspecified"),
                "author_determined": bool(source.get("author_determined", False)),
                "software_determined": bool(source.get("software_determined", False)),
            }
        )
    return sorted(candidates, key=_assembly_source_rank)


def classify_catalog_record(
    record: Mapping[str, Any], policy: MonomerPolicy
) -> dict[str, Any]:
    """Classify one catalog record without applying resolution/completeness filters."""
    methods = {
        str(method).strip().upper()
        for method in record.get("experimental", {}).get("methods", [])
    }
    model_count = int(record.get("experimental", {}).get("model_count", 0) or 0)
    compositions = _composition_candidates(record)
    exact = [
        composition
        for composition in compositions
        if composition.get("protein_chain_instance_count") == policy.protein_chain_instances
        and composition.get("nucleic_acid_chain_instance_count")
        == policy.nucleic_acid_chain_instances
        and composition.get("other_polymer_chain_instance_count")
        == policy.other_polymer_chain_instances
    ]
    selected = exact[0] if exact else None
    selected_id = selected.get("assembly_id") if selected else None
    if selected is None:
        contextual = [
            composition
            for composition in compositions
            if composition.get("protein_chain_instance_count") == policy.protein_chain_instances
        ]
        return {
            "classification": "contextual" if contextual else "ineligible",
            "reason": "polymer_context_or_nonmonomer" if contextual else "no_monomer_assembly",
            "assembly_id": contextual[0].get("assembly_id") if contextual else None,
        }
    protein_chains = [chain for chain in record.get("chains", []) if chain.get("is_protein")]
    source_asym_ids = set(selected.get("source_asym_ids", []))
    selected_protein_chains = [
        chain
        for chain in protein_chains
        if chain.get("source_label_asym_id") in source_asym_ids
    ]
    if selected_protein_chains:
        protein_chains = selected_protein_chains
    if len(protein_chains) != 1:
        return {
            "classification": "ineligible",
            "reason": "assembly_source_chain_not_unique",
            "assembly_id": selected_id,
        }
    chain = protein_chains[0]
    length = int(chain.get("sequence_length", 0) or 0)
    if length < policy.min_length or length > policy.max_length:
        return {
            "classification": "ineligible",
            "reason": "sequence_length",
            "assembly_id": selected_id,
            "sequence_length": length,
        }
    if not methods.intersection(policy.primary_methods):
        return {
            "classification": "auxiliary",
            "reason": "experimental_method",
            "assembly_id": selected_id,
            "sequence_length": length,
        }
    if model_count < 1 or model_count > policy.max_models:
        return {
            "classification": "auxiliary",
            "reason": "multi_model_or_missing_model",
            "assembly_id": selected_id,
            "sequence_length": length,
        }
    observations = record.get("asu_observations", {})
    if observations.get("small_molecule_atom_count", 0) and not policy.allow_small_molecules:
        return {
            "classification": "apo_like_excluded",
            "reason": "small_molecule_context",
            "assembly_id": selected_id,
            "sequence_length": length,
        }
    if observations.get("ion_atom_count", 0) and not policy.allow_ions:
        return {
            "classification": "context_excluded",
            "reason": "ion_context",
            "assembly_id": selected_id,
            "sequence_length": length,
        }
    if observations.get("water_atom_count", 0) and not policy.allow_water:
        return {
            "classification": "context_excluded",
            "reason": "water_context",
            "assembly_id": selected_id,
            "sequence_length": length,
        }
    return {
        "classification": "monomer_clean",
        "reason": "structural_policy_pass",
        "apo_like_eligible": not bool(observations.get("small_molecule_atom_count", 0)),
        "assembly_id": selected_id,
        "assembly_definition_source": selected.get("definition_source"),
        "chain_source_label_asym_id": chain.get("source_label_asym_id"),
        "entity_id": chain.get("entity_id"),
        "sequence": chain.get("sequence", ""),
        "sequence_length": length,
        "experimental_methods": sorted(methods),
        "model_count": model_count,
    }


__all__ = ["MonomerPolicy", "classify_catalog_record"]
