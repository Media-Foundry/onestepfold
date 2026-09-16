# Project context

Updated: 2026-09-14

The active project is now OneStepFold: a strict, open, MSA-off protein folding
experiment with a multi-chain-aware GT catalog and a monomer-first training
view. The model target remains one Pairformer cycle, one structure-module
network evaluation, and one output sample. The primary sequence conditioner is frozen
ESMC-600M with cached per-residue embeddings; ESMC-300M and ESMC-6B are scale
ablations. The folding core is randomly initialized and trained separately.
The official `protenix_mini_esm_v0.5.0` ESM2 path is a compatibility baseline,
not the active conditioner. Clean-Structure MeanFlow remains the proposed
method with native one-step/consistency baselines.

Current scientific boundaries:

- the catalog is multi-chain-aware, but the first training/evaluation view is a
  declared monomer pool; a future multimer view reuses the same GT schema;
  ligand/RNA entities are not model inputs in the first view;
- MSA disabled by experimental protocol, with ESMC used as the single-sequence
  conditioner;
- `N_cycle=1`, structure `N_step=1`, `N_sample=1` are the final target, not an
  assumed starting capability;
- structure-core NFE and end-to-end ESM latency are reported separately;
- a clean-structure MeanFlow loss requires a derived JVP target and geometry
  path validation; it is not a plain coordinate MSE label;
- ESMC is not a drop-in replacement for Protenix Mini-ESM: the cache, model
  revision, residue alignment, and dimensionality adapter are versioned
  artifacts, and the ESMC folding core is trained separately;
- ESM3 structure-track outputs are excluded from the main input contract; ESM3
  is sequence-hidden-state-only ablation because its multimodal generation can
  act as an unstated structure teacher;
- the primary training sample is structure-derived: the input sequence,
  residue numbering, and all-atom target come from the PDB mmCIF entity/chain;
  UniProt/SIFTS is retained for provenance and residue-level traceability only,
  not as the source of the model input sequence or target coordinates;
  AF/ESMFold/Atlas coordinates are excluded from the primary target set;
- the initial hpc2 raw snapshot uses SIFTS flatfiles dated 2026-09-08,
  yielding 244,406 chain-mapped PDB entries and 76,273 UniProt accessions;
  remote downloads are staged under `/hpc2hdd/home/shuang886/Folding/Dataset`
  with PDB mmCIF and mapped UniProt FASTA kept as separate raw layers;
- the first-version entry universe is deliberately fixed to the `244,406`
  SIFTS-linked PDB entries already staged on hpc2. This is not an all-
  experimental-PDB universe, and no unmapped entries will be added in the first
  version. SIFTS remains an entry-discovery/provenance layer only; the training
  sequence and coordinates are still extracted exclusively from PDB mmCIF;
- dataset de-duplication is restricted to exact (100% sequence identity)
  duplicates at the chain level. Near-identical proteins, construct variants,
  and small mutations remain eligible records; exact-sequence groups must still
  be kept together when making train/validation/test splits to prevent label
  leakage, while the multi-chain structure instance remains the training unit;
- a PDB time split does not establish that ESMC has not seen a held-out sequence;
  record the exact ESMC revision and audit sequence overlap when its pretraining
  corpus is available, otherwise report residual representation-contamination
  risk;
- the authoritative 100% SI calculator is Biopython
  `Bio.Align.PairwiseAligner` in global mode, with identity defined as matches
  divided by all global alignment columns including gaps. Exact sequence
  SHA256 is only a lossless candidate index; it does not replace pairwise
  verification or introduce near-identity clustering;
- CUDA-oriented Protenix kernels and unverified ROCm fallback make backend and
  kernel selection part of the benchmark record;
- existing `src/fastglycan` code is preserved as a legacy prototype and is not
  the active data contract.

GT handling constraints:

- the chain resolver must map `SIFTS CHAIN ->
  _entity_poly.pdbx_strand_id -> entity_id -> _struct_asym.id -> atom_site`;
- missing atoms are not repaired in the raw or primary GT branch. Coordinates
  and atom masks are emitted as observed, and the training loss decides which
  atom labels are valid;
- missing residues may have a separately versioned PDBFixer-derived branch,
  but imputed residues/atoms must carry an explicit `imputed_mask` and are not
  treated as experimental coordinates by default;
- the raw mmCIF layer is immutable; any PDBFixer output is a derived artifact
  with its own provenance and does not replace the observed structure.

Multi-chain GT constraints:

- the universal GT schema represents a selected PDB structure instance and can
  contain multiple jointly modeled protein chains; the first training view
  selects monomer instances from that catalog;
- the GT record stores one sequence/residue/atom/mask block per chain plus a
  stable `chain_index`, `entity_id`, and label asym ID; total-residue and
  chain-count limits are applied at the instance level;
- the builder must preserve inter-chain geometry and emit chain-pair metadata
  needed for interface/contact losses and evaluation;
- `_pdbx_struct_assembly` and `_pdbx_struct_assembly_gen` must be inspected
  before shard creation. Asymmetric-unit coordinates and biological-assembly
  coordinates are distinct derived views and must never be silently mixed.

The first implementation milestone was Stage A: a deterministic catalog scan
over the fixed entry universe. Stage 0 folding evaluation uses a declared
low-homology monomer view with a paired fixed-seed run and a five-seed variance
subset. Do not start training or make an accuracy claim until the catalog,
monomer filter, checkpoint, Protenix version, assembly policy, kernel, and
latency accounting are captured.

Stage A scanner hardening passed 3-entry, 1,000-entry, and 10,000-entry HPC
audits with zero parser errors and zero unresolved SIFTS rows. The complete
244,406-entry catalog is now accepted: all 256 deterministic shards finalized,
PDB IDs are unique, error files are empty, dates and assembly composition are
present, and no partial outputs remain. The catalog-only monomer selector
produced 84,232 `monomer_clean` candidates and 18,427 `monomer_apo_like`
eligible records. Numeric resolution and coordinate-completeness thresholds
remain deferred to Stage B materialization.

The exact 100% SI manifest has also been generated for the monomer candidates
using Biopython global `PairwiseAligner` verification within lossless SHA256
sequence buckets: 84,232 records form 41,592 exact sequence groups with
42,640 verified duplicate memberships. No train/validation/test partition has
been generated yet; Stage B coordinate QA remains the next gate, followed by
an atomic split over these exact groups.

Stage B's first 10,000-record pilot (8,000 stratified plus 2,000 stress cases)
has completed on hpc2. Gemmi materialization produced 64 tar shards with
10,000/10,000 successful records and zero shape, finite-coordinate, mask, or
member-pair validation errors. The pilot reports coverage and missingness
distributions, modified-residue strata, geometry screening counts, and exact-
sequence structural variance. This is the historical pilot milestone; the
numeric policy, final split, and ESMC cache are superseded by the accepted
full-corpus milestones below.

The monomer training view is now structurally frozen: choose a biological
assembly with exactly one generated protein chain instance, zero generated
nucleic-acid/other-polymer chain instances, a primary X-ray/EM/neutron method,
one coordinate model, and a 20--1024 residue protein construct. Water, ions,
and small molecules remain allowed in `monomer_clean`; zero-small-molecule
records are marked as the `monomer_apo_like` subset. The full Stage B audit
below now freezes the resolution and coordinate-completeness thresholds.

The full Stage B v1 materialization is now accepted: all 84,232 monomer-clean
records succeeded across 348 tar shards, with 168,464 expected members and zero
shape, mask, finite-coordinate, or materialization errors. Full-corpus median
frame and canonical-heavy-atom coverage are 0.967 and 0.963. The frozen
`gt_quality_v1` policy yields 78,259 Train-valid records, 45,815 HQ-Eval-valid
records, and 5,973 rejects. It retains modified residues with unmapped side
chains masked and records clash density without making it a hard v1 filter.

Quality filtering rebuilt 38,400 exact sequence groups. Initial-release time
split at 2021-09-30 contains 31,689 train-seen groups (59,959 records), 6,711
unseen temporal test groups (12,940 records), and 932 leakage-excluded
post-cutoff same-sequence groups (5,360 records). A Biopython PairwiseAligner
near-homology audit uses a separate high-gap-cost global scoring policy,
residue identity, shorter-sequence coverage >=0.70, and at least 50 aligned
residues. Strict identity <0.30 leaves 15 groups (18 records) as the additional
low-homology test subset; the temporal test remains primary. The split artifacts
are frozen under `/hpc2hdd/home/shuang886/Folding/splits_v1`; the validated ESMC
cache is now the sequence-conditioning artifact for Stage 0.

The ESMC cache contract is versioned in `docs/esmc_cache_v1.md`. The production
cache uses `biohub/ESMC-600M` at HF revision
`28aed46fcaf217dfa59f78a589bb449aa3ae5d98`, using Biohub/esm revision
`bf343ba264b650dff7a073643725f9aaa1fdbe8d`, with the final residue layer as
the feature variant. Cache keys include the sequence SHA256, model and both
revisions, feature variant, and dtype. An all-layer, 2,000-group probe remains
available as an auditable representation diagnostic. The production cache
contains all 38,400 quality-valid exact sequence groups and passed an
independent Slurm validator. ESMC special tokens are removed only after an
explicit `L+2` assertion, and residue features are stored as BF16 sharded
safetensors.

The ESMC-300M scale-ablation cache is also complete on the two Precision W7900
cards. It uses HF revision `f0d413606442e6b433d5e75e9aae3285ca9b137f`, the
same pinned Biohub/esm revision, final-layer BF16 features, and the same 38,400
groups / 11,615,845 residues. Its two deterministic partitions merge into 719
validated shards occupying 21 GB under
`/media/WDisk/Datasets/OneStepFold/esmc_300m_final_v1`. It is an ablation and
does not replace the primary ESMC-600M cache.

Stage 0A is frozen as a compatibility-only Protenix Mini-ESM experiment. Its
view is `stage0_v1`: 1,024 HQ-valid temporal dev groups, a nested 128-group
five-seed variance subset, 2,440 remaining HQ-valid frozen-test groups, and a
separate complete 15-group strict-low-homology exclusion list. The sweep is
the 3x3 `{1,2,4} cycles x {1,2,5} steps` factorial through length 1024. It
must run on a fixed declared backend, preferably `i64m1tga800ue`, with each
factorial point submitted as an independent one-A800 job before any
ESMC-conditioned model tuning uses the frozen test. The runtime package is
Protenix 1.1.0 while the selected model checkpoint remains Mini-ESM v0.5.0;
their hashes are recorded independently.

Stage 0B/0C scoring and profiling found that quality depends much more strongly
on recycle depth than on structure diffusion steps. The current method-selection
stage is Stage 0D: predictive, risk-aware recycling from cycle-1 information,
compared against fixed depth, an AlphaFold-style reactive convergence signal
available only after cycle 2, and an oracle compute-quality frontier. This does
not claim adaptive recycling or early stopping as a new concept. The specific
question is whether recycle demand can be predicted before paying for the next
recycle. Clean-Structure MeanFlow is therefore deprioritized until a structure-
step bottleneck is demonstrated.

The cycle-1 internal-state audit is complete on `temporal_dev_v1` (A800 job
`12759723`, 1,024 records, zero hook errors). Compact Pairformer single/pair
statistics provide only a small additional risk-routing signal: HGB mean cycles
at TM catastrophic risk <=1% improve 2.066 -> 2.031, while joint TM/all-atom
risk <=1% improves 3.177 -> 3.156. Treat this as a diagnostic result, not a
novelty claim; retain fixed `c2_s2` and post-cycle-2 reactive convergence as
baselines, and keep the frozen temporal test untouched.

Stage 0E is complete on `temporal_dev_v1`: an independent c2_s2 run (A800
job `12761522`) produced 1,024/1,024 two-cycle internal traces with no hook
errors. The joint c2-to-c4 hard label has 76 positives. At joint risk <=1%,
the oracle is 2.129 mean cycles, the best current grouped-OOF HGB route is
2.477, and the existing reactive distance baseline is 2.551. This closes only
a small oracle gap and uses OOF threshold sweeps, so it is a diagnostic result;
default to fixed c2_s2 and require nested calibration before frozen-test use.

Stage 1A residual characterization passed a clean single-target smoke. The
runtime hook normalizes Protenix's unbatched `[L,C]`/`[L,L,C]` Pairformer
outputs, preserves cycle state after diagnostic exceptions, and runs
SVD/eigendecomposition on detached CPU FP32 tensors for backend portability.
The full temporal-dev `c4_s2` characterization completed as A800 job
`12767871` under `/hpc2hdd/home/shuang886/Folding/stage1a/residual_c4s2_v1`;
it has 1,024 rows, all three transitions, and zero feature errors. The
length-controlled report is committed under
`reports/stage1a_residual_analysis_2026-09-17.{json,md}`. Pair residual means
remain moderately correlated with c2 all-atom degradation after controlling
for sequence length (about -0.40); the spatial rank-8 statistic is for the
nonnegative pair-magnitude envelope, not the signed tensor rank.

Stage 1A is a completed characterization gate. Stage 1B teacher data uses
one deterministic train-valid record per exact sequence group and is split
into 16 independent Protenix shards for `c2_s2` and `c4_s2`. Stage 1C adds an
opt-in signed pair sketch and adjacent residual-direction cosines; its
256-target diagnostic is separate and does not touch frozen temporal test
data.
