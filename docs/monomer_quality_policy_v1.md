# Monomer View and Quality Policy v1

Status: frozen for the v1 full materialization and split build.

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

Stage A remains metadata-only. Stage B applies the following two quality tiers
to materialized coordinate records. A record that fails Train is rejected from
the primary pool; a Train record that fails HQ-Eval remains usable for masked
training but is excluded from the strict evaluation tier.

| Condition | Train v1 | HQ-Eval v1 |
| --- | ---: | ---: |
| resolution | <=4.5 A | <=3.0 A |
| N/CA/C frame coverage | >=0.80 | >=0.95 |
| canonical heavy-atom coverage | >=0.75 | >=0.90 |
| internal missing fraction | <=0.15 | <=0.02 |
| finite coordinates | required | required |
| unexplained CA chain breaks | 0 | 0 |
| chirality violations | 0 | 0 |
| bond/peptide outliers | 0 | 0 |

Terminal missing residues are allowed and remain masked. Modified residues are
retained; side chains without a canonical atom37 mapping are masked while the
raw component ID is preserved. Steric clashes are recorded as counts and
densities, but are not a v1 hard rejection because isolated experimental
clashes can reflect side-chain uncertainty or modified chemistry.

The policy is encoded in `configs/gt_quality_v1.toml` and applied by
`scripts/filter_stageb_quality.py`. The full catalog is the source for
eligibility distributions; the full Stage B materialization is the source for
coordinate-quality decisions.

The eventual quality policy must preserve the distinction between:

```text
Stage-A eligibility: catalog metadata and assembly composition
Stage-B quality: materialized coordinates, masks, and geometry checks
```
