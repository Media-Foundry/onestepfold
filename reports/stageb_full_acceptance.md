# Stage B Full Materialization and Split Acceptance

Date: 2026-09-15

## Full materialization

The frozen `monomer_clean` candidate table was materialized with the corrected
missing-residue-aware geometry QA. The Slurm array used 32 deterministic hash
workers with 64 CPUs and 500 GB per task.

| Check | Result |
| --- | ---: |
| input candidates | 84,232 |
| materialized records | 84,232 / 84,232 |
| tar shards | 348 |
| tar members | 168,464 / 168,464 |
| materialization errors | 0 |
| NPZ shape errors | 0 |
| metadata length errors | 0 |
| non-finite valid coordinates | 0 |
| residue/atom mask errors | 0 |

Output: `/hpc2hdd/home/shuang886/Folding/processed_stageb_v1`.

The full-corpus QA medians are 0.967 observed-residue/frame coverage and
0.963 canonical-heavy-atom coverage. P05 values are 0.818 and 0.807. Geometry
screening totals are 577 bond outliers, 1,679 peptide outliers, 179 chirality
violations, 1,639 unexplained CA breaks, and 6,492 steric clash pairs. Clashes
remain reporting-only in quality v1. Modified/noncanonical components occur in
9,080 records and are retained with unmapped side chains masked.

## Quality policy

`configs/gt_quality_v1.toml` is the frozen Train/HQ-Eval policy:

| Tier | Resolution | Frame | Heavy atom | Internal missing |
| --- | ---: | ---: | ---: | ---: |
| Train | <=4.5 A | >=0.80 | >=0.75 | <=0.15 |
| HQ-Eval | <=3.0 A | >=0.95 | >=0.90 | <=0.02 |

Both tiers require finite coordinates, zero CA breaks, zero chirality
violations, and zero configured bond/peptide outliers. Terminal missingness is
allowed; modified residues are retained; clashes are recorded but do not reject
records in v1.

| Quality result | Records | Exact groups |
| --- | ---: | ---: |
| Train-valid | 78,259 | 38,400 |
| HQ-Eval-valid | 45,815 | 21,680 |
| Reject | 5,973 | - |

Quality artifacts are under `/hpc2hdd/home/shuang886/Folding/quality_v1`.

## Time and sequence views

Groups were rebuilt after quality filtering. A group is train-seen when it has
at least one valid record with initial release on or before 2021-09-30. Later
records of such groups are leakage-excluded. Only groups whose valid records are
all post-cutoff enter the temporal test candidate pool.

| View | Groups | Records |
| --- | ---: | ---: |
| train | 31,689 | 59,959 |
| post-cutoff same-sequence | 932 | 5,360 |
| temporal test | 6,711 | 12,940 |
| HQ-Eval (all eligible dates) | 21,680 | 45,815 |
| low-homology test | 15 | 18 |

The near-homology audit compares every temporal test group against all 31,689
train groups with Biopython `PairwiseAligner`. It reports residue identity
(aligned residue-residue columns), shorter-sequence coverage, and global
alignment identity. The low-homology stress subset requires residue identity
<30%, coverage >=70%, and at least 50 aligned residues. The small size of this
subset is a result, not a reason to weaken the primary temporal split.

Split artifacts are under `/hpc2hdd/home/shuang886/Folding/splits_v1`; near-SI
blocks are under `/hpc2hdd/home/shuang886/Folding/low_homology_v1`.

## Acceptance

Stage B v1 is accepted for downstream ESMC caching and folding experiments.
The raw mmCIF layer, catalog, quality index, exact groups, and split manifests
are immutable inputs for the next model milestone. No ESMC cache was generated
in this step.
