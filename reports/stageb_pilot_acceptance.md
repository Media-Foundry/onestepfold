# Stage B 10k Pilot Acceptance

Date: 2026-09-15

This pilot materializes a deterministic 8,000-record stratified sample plus
2,000 stress cases from the frozen `monomer_clean` candidate view. The catalog
and exact-SI artifacts remain immutable inputs. The pilot is a quality audit,
not the final training pool or a final train/validation/test split.

## Selection

| Component | Records |
| --- | ---: |
| stratified representative sample | 8,000 |
| stress cases | 2,000 |
| total selected | 10,000 |
| non-empty selection strata | 51 |

Selection strata cross release bucket, length bin, primary method, resolution
bin, and apo-like status. Stress ranking prioritizes alternate locations, low
occupancy, modified residues, missing residues, multiple assembly definitions,
and long chains. The selection and join were checked for 10,000 unique PDB IDs;
every selected source chain agrees with the assembly composition used by the
monomer filter.

## Materialization acceptance

| Check | Result |
| --- | ---: |
| worker jobs | 32 / 32 completed |
| materialized records | 10,000 / 10,000 |
| tar shards | 64 |
| tar members | 20,000 (expected 20,000) |
| index records | 10,000 |
| missing NPZ/JSON pair | 0 |
| NPZ shape errors | 0 |
| metadata length errors | 0 |
| non-finite valid coordinates | 0 |
| residue/atom mask inconsistencies | 0 |
| materialization error records | 0 |

The physical output is approximately 923 MiB at
`/hpc2hdd/home/shuang886/Folding/processed_stageb_pilot`. Each tar entry has a
compressed NPZ tensor and a compact JSON metadata record. The logical GT record
is reconstructed from the two files; atom arrays are not duplicated in JSON.

The NPZ fields are:

```text
aatype              [L]
residue_index       [L]
atom37_positions    [L,37,3] float32
atom37_mask         [L,37] bool
residue_mask        [L] bool
chain_index         [L]
```

`residue_mask` is false for sequence positions with no observed canonical atom;
the construct sequence and residue metadata are retained in all cases. No
PDBFixer or other coordinate imputation is used. Modified-residue side chains
without an explicit canonical parent mapping are masked, while their raw
`comp_id` remains in metadata.

## Coverage and missingness

Coverage is computed against residue-specific canonical heavy-atom sets, with a
terminal OXT slot where applicable, rather than against `37 * L`:

```text
metric                  p05       p25       p50       p75       p95
observed residue        0.7441    0.8771    0.9430    0.9849    1.0000
N/CA/C frame            0.7406    0.8763    0.9423    0.9846    1.0000
N/CA/C/O backbone       0.7406    0.8762    0.9421    0.9846    1.0000
heavy atom              0.7040    0.8664    0.9341    0.9798    1.0000
internal missing        0.0000    0.0000    0.0000    0.0288    0.1051
terminal missing        0.0000    0.0070    0.0333    0.0899    0.2244
```

1,845 structures contain at least one observed noncanonical/modified component
under the pilot detector. This is a metadata/side-chain masking stratum, not a
reason to discard the entire structure before reviewing the distribution.

## Geometry QA

All 10,000 samples have finite valid coordinates. The pilot heuristic checks
reported the following total outlier counts:

```text
bond length outliers       65
peptide bond outliers     188
chirality determinant      12
steric clash pairs       1388
CA chain breaks           284
```

These are screening metrics with fixed thresholds, not a substitute for a
full restraint-aware validation package. They identify the tail that should be
reviewed before freezing numeric quality cutoffs.

## Same-sequence structural variance

The exact-100%-SI manifest was joined to the pilot and structures were compared
within exact sequence groups. The audit compares each group's deterministic
representative with every other pilot member (not all possible member pairs):

```text
pilot records in replicate groups    3,373
exact groups with >=2 pilot records    911
representative comparisons           2,462
disagreement comparisons               190
disagreement fraction                0.07717
```

Disagreement is defined as Kabsch-aligned C-alpha RMSD > 2.0 A or TM-score <
0.9. RMSD quantiles are 0.112/0.240/0.426/0.775/3.298 A (P05/P25/P50/P75/P95)
and TM-score quantiles are 0.879/0.985/0.996/0.998/1.000. The nonzero tail
supports sampling structure records through exact-sequence groups rather than
uniformly sampling PDB records for the eventual training loader.

## Artifacts and next gate

```text
/hpc2hdd/home/shuang886/Folding/stageb_pilot/stageb_pilot.jsonl.gz
/hpc2hdd/home/shuang886/Folding/processed_stageb_pilot/stageb_pilot_summary.json
/hpc2hdd/home/shuang886/Folding/processed_stageb_pilot/same_sequence_variance.json
```

Stage B pilot acceptance is limited to parser/serialization integrity and
distribution audit. Numeric resolution, residue/backbone/heavy-atom coverage,
modified-residue handling, and geometry thresholds remain policy decisions to
freeze after reviewing these distributions. The next implementation step is a
quality-policy selector and group-aware sampling rule; final split generation
and ESMC caching remain blocked until that policy is recorded.
