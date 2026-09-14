# Monomer View and Quality Policy v1

Status: structural eligibility frozen; numeric quality thresholds remain
pending full-catalog and Stage B distributions.

## Monomer definition

An entry is a monomer candidate when a selected biological assembly has exactly
one generated protein chain instance:

```text
protein_chain_instance_count == 1
nucleic_acid_chain_instance_count == 0
other_polymer_chain_instance_count == 0
```

The count is taken from Gemmi assembly generators, not from the number of
protein chains in the asymmetric unit. This distinction preserves cases where
the ASU and biological assembly differ.

The catalog-only selector also requires a primary experimental method (X-ray,
electron microscopy, or neutron diffraction), one coordinate model, and a
protein construct length from 20 through 1024 residues. These are eligibility
conditions, not claims about final all-atom label quality.

## Context strata

Water, ions, and small molecules do not disqualify the primary monomer view.
Every selected row carries a `views` field:

```text
monomer_clean       primary structural view; small molecules allowed
monomer_apo_like    subset with zero observed small-molecule atoms
monomer_contextual  monomer assemblies containing nucleic/other polymer context
auxiliary           unsupported method or multi-model record
```

The current selector emits `monomer_clean` rows and marks the apo-like subset
without duplicating records. Contextual and auxiliary entries remain in the
catalog for analysis and future views, but are not in the primary candidate
table.

## Quality thresholds

Resolution and coordinate completeness are deliberately not frozen in Stage A.
The full catalog must first report method/resolution/length distributions.
Stage B then computes residue coverage, backbone coverage, heavy-atom coverage,
internal missing runs, terminal missing fractions, chain breaks, and geometry
validity. Mild missingness is retained with masks; severe incompleteness can be
filtered after its distribution is visible.

The eventual quality policy must preserve the distinction between:

```text
Stage-A eligibility: catalog metadata and assembly composition
Stage-B quality: materialized coordinates, masks, and geometry checks
```
