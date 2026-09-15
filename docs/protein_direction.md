# OneStepFold protein direction

## Locked first target

The first research target is a protein monomer predictor backed by a
multi-chain-aware GT catalog with this explicit
inference contract:

```text
single protein chain from a selected monomer view
MSA disabled
one Pairformer cycle
one structure-module network evaluation
one output sample
all-atom coordinates and confidence outputs
```

The GT schema and catalog retain jointly modeled protein chains, assembly copies,
and inter-chain metadata for a future multimer view. Ligand and RNA entities
are retained as provenance where present but are not inputs in the first view.
The assembly policy (asymmetric unit versus a declared biological assembly) is
a required dataset decision and must be recorded with every shard.

The structure NFE count excludes the sequence conditioner. It must still be
included in end-to-end latency, peak memory, and throughput. The active
conditioner is frozen ESMC-600M (`esmc_600m`) with cached per-residue
embeddings; ESMC-300M is the memory baseline and ESMC-6B is an upper-bound
ablation. The official `protenix_mini_esm_v0.5.0` checkpoint remains a separate
ESM2 compatibility baseline: its 135.22M structure parameters and released
four-cycle/five-step defaults are useful references, but its input projection
cannot be assumed to accept ESMC features without retraining an adapter.

This removes coordinate-teacher supervision, not pretrained-representation
bias. ESMC is trained on billions of protein sequences, so a PDB release cutoff
does not by itself prove that a held-out sequence was unseen by ESMC. Record the
exact ESMC revision and report sequence-identity overlap when the pretraining
corpus is available; otherwise label this as a residual contamination risk.

## What is already known

DCFold is an ICLR 2026 single-step all-atom model derived from Protenix. It
reports one recycle and one diffusion step, but its Mini comparison is a 135M
model using two-step ODE sampling; the one-step DCFold model is the distilled
larger Protenix path. Therefore this project cannot claim novelty from “one-step
folding” alone. The first defensible experiment is a randomly initialized,
ESMC-conditioned folding core trained without coordinate-teacher trajectories,
with a matched Protenix initialization and a DCFold-style consistency baseline.
Clean-Structure MeanFlow is a candidate objective, not a novelty claim until
its geometry and one-step quality are demonstrated.

ESMC is the primary sequence representation model because it is explicitly
designed to provide protein-biological representations and long-range
structure-related information from sequence. ESM3 is a different class: its
sequence, structure, and function tracks are jointly tokenized and generated.
The local `esm3-sm-open-v1` model is therefore an optional ablation using only
sequence-derived hidden states; feeding ESM3 structure-track outputs to the
folding core would introduce an existing structure predictor as an unstated
teacher.

MeanFlow is not ordinary clean-coordinate regression. Its average-velocity
identity uses the instantaneous flow field and a Jacobian-vector product during
training. A clean-structure parameterization is allowed as a change of variables
only after deriving the corresponding target and testing the derivative path.

Two implementation facts affect the first training milestone. The active ESMC
path is not a drop-in replacement for Protenix Mini-ESM: it needs a versioned
cache format, tokenizer/model revision, sequence-to-row alignment, and a
learned dimensionality adapter. The released Mini-ESM checkpoint is kept only
for the compatibility baseline; the ESMC folding core is trained separately.
Do not silently replace ESMC with MSA features while calling the experiment
MSA-off.

The Protenix runtime also ships CUDA-oriented optional kernels and has no
official ROCm validation in this protocol. AMD runs are useful compatibility
tests; the reported benchmark should use one fixed backend and record whether
fused kernels or PyTorch fallbacks were active.

## Stage 0A: Protenix compatibility baseline

Before running the matrix, freeze `temporal_dev_v1` from HQ-valid temporal
groups using `scripts/select_temporal_dev.py`. The default view contains 1,024
exact sequence groups, one deterministic HQ target per group, and a fixed
seed. The remaining HQ-valid temporal groups are written to
`frozen_temporal_test_v1`; the 15 strict low-homology groups remain in the
frozen test view and are never used for tuning. Their complete group list is
also written to `frozen_temporal_low_homology_groups_v1`, including groups
without an HQ target. The selector preserves joint length, resolution,
apo-like, and experimental-method strata and records its protocol beside the
manifests. It also writes a fixed, stratified `temporal_variance_v1` subset
of 128 groups for the five-seed repeat.

Run the complete 3x3 factorial in `configs/protenix_stage0.toml` on the
temporal dev view, with one paired seed and one sample. The matrix is
`(cycles, steps) in {(1,1), (1,2), (1,5), (2,1), (2,2), (2,5), (4,1), (4,2),
(4,5)}` and includes lengths through 1,024 residues. Repeat the same matrix
on the fixed 128-group subset with seeds `101, 103, 107, 109, 113` before
interpreting stochastic variance. Do not inspect or tune against the frozen
temporal test or strict low-homology view. Use the
Protenix CLI with
`--use_default_params false`; otherwise the model defaults can overwrite manual
cycle/step values. Example:

```bash
protenix pred \
  -i "$INPUT" -o "$OUT/c1_s1" -s 101 \
  -n protenix_mini_esm_v0.5.0 \
  --use_default_params false --cycle 1 --step 1 --sample 1 \
  --use_msa false --use_template false --dtype bf16
```

Record the exact command, Protenix commit/tag, checkpoint hash, kernel backend,
GPU, sequence length, wall time, model-forward time, peak VRAM, output validity,
and all metrics. This tells us whether the dominant failure is diffusion NFE,
recycling, or both before any new loss is implemented. Keep structure-core
latency (excluding ESM) separate from end-to-end latency; confidence inference
belongs in the latter.

## Stage 0B: ESMC conditioner smoke test

Before folding-core training, run `configs/esmc_stage0.toml` on the same
sequences with ESMC-300M and ESMC-600M. Verify embedding shape, padding and
residue alignment, cache round-tripping, extraction throughput, and peak VRAM.
The first ESMC folding run should use random core weights and a frozen
conditioner; no ESM3 structure track or external predicted coordinates are
allowed in the input.

## Training sequence

1. **Scratch core:** randomly initialize the folding core, freeze ESMC, and
   train with one cycle. Compare direct one-step MeanFlow, a standard flow/ODE
   objective, and a consistency objective under identical data and budgets.
2. **Capacity diagnostic:** run the same weights with four cycles or multiple
   structure evaluations only as an analysis upper bound. This separates model
   capacity from the strict deployment contract without making it part of the
   main model.
3. **Stabilization:** add confidence and geometry terms only after the structure
   objective is stable; keep the Protenix-initialized model as a matched control.

## Data and metrics

Use monomer instances first, with a declared release cutoff and family/cluster
separation. The catalog remains multi-chain-aware for future complex views.
UniProt is provenance only; it is not an
all-atom structure-label database or input-sequence source. Structure targets
must come from experimentally resolved PDB entities/chains, with constructs,
missing residues, mutations, assembly membership, and alternate locations
recorded. The Protenix
training pipeline's complete prepared data is large
(the official instructions state at least 1.5 TB for full preparation), so Stage
0 should use its released evaluation indices or a small audited subset. Do not
claim generalization from random frame or chain splits.

DCFold's headline one-step results include broader structure tasks. This
project's first view is monomer and MSA-off; compare matched subsets and report
protocol differences instead of copying a cross-task headline number.

Report TM-score, lDDT-Ca, all-atom lDDT, GDT-TS, backbone/side-chain RMSD, bond
and angle violations, clashes, chirality, Ramachandran outliers, confidence
calibration, and length-stratified latency. lDDT is naturally available both on
all atoms and on C-alpha-only distances; use one fixed implementation and state
whether hydrogens and stereochemical checks are included.

The first paper-level claim should be “training-efficient, open, MSA-off,
one-step monomer folding with a multi-chain-ready GT catalog,” not “we invented
one-step folding.”
