# Direct reference-conditioned task readout v1

Locked2026-10-03 after161712a2. Separate task-prediction diagnostic, NOT a mutant
structure generator or complete C4 replacement. The read-only collapse audit is
separate; do not patch/retrain the old Δz model based on its findings.

## Data and target

Reuse BOTH exact ten-site/eight-protein training lists from pair_coverage_v1;
seeds231301/231303, fresh initialization, no new teachers/ESM/C4/S1. Same exclusions,
48-site development panel, common-held34 and unseen-protein32sites16proteins.
Originalvalidation8proteins/heldN25/S34/all4PT4 excluded from updates. All are
method-development data; no independent confirmation or selection on held scores.

Main label uses **Exact native hard-mutant output**, not the oracle-s student
Baseline. For each candidate/noise use task(mutant)-task(WT), the existing parent
experimental-Cα-distance Huber proxy with fixed observed mask and >=3 sequence
separation. Train on arithmetic mean of OLD noises230201/230211 only. Fit one
scalar RMS scale from the arm's190 TRAIN labels only (no per-test-site scale).
Network output is normalized Δtask; undo this global training scale for reporting.
No probability/distribution calibration claim; no mutant experimental utility.

NEW noises270101/270103 are held from these labels but have previous development
history. Prediction has no noise input: one20-AA vector is evaluated against old,
new and four-noise teacher means. Its old-selection is never replaced after
viewing new noise. Δtask versus absolute task is only a candidate-independent WT
shift for ranking/regret; error metrics here explicitly measure task CHANGE.

## Legal inputs and fixed models

Reference backbone and observed mask are explicitly GIVEN task conditions. This
is reference-constrained screening; if a use case lacks that backbone, this
predictor does not provide its unknown-reference score. Reference coordinates
are parent GT, never experimental mutant coordinates. No target s/z/s_inputs or
mutant coordinates enter the forward inputs.

ContextTaskReadout: unchanged large WT node encoder (width256,4 bias-attention
blocks) from DeepResponseStudent, with factor heads removed. Full WT s/z, site,
source/target discrete AA enter node_response. Reference:20 invariant features
per residue, seven RBF distance summaries over observed >=3-separated reference
pairs, seven site-distance RBFs, observation flags, valid-pair fraction, sequence
offset, log length and site distance. Width128 reference projection; fuse with
node features to256; candidate-conditioned residue pooling plus site feature
and AA query to shared scalar readout. All positions/lengths share weights.
This task representation is finite and lossy; a failure cannot prove every
possible reference-conditioned scorer fails.

AATaskReadout: only source/target AA, embedding32, shared MLP96->128->64->1.
No WT tensors, position, protein identity, reference or per-site parameters.
This is a deliberately simple preference control, not a parameter-matched
causal ablation. In both models score(a)-score(WT) gives exact zero for WT.

## Training and stopping

2dataarms x2architectures x2seeds =8runs. Fresh from scratch. Both architectures
use32760updates,10contexts round-robin, all19nonWT each update,3276exposures/site.
Mean squared normalized task-delta error, AdamWlr1e-3/wd1e-4/eps1e-8,clip1,
no scheduler, no ranking/geometry/latent loss. Checkpoints10920/21840/32760;
intermediate TRAIN curves only, primary fixed32760. No retries, best-checkpoint
selection, fitting threshold, LR sweep, seed replacement or automatic extension.
Different architectures' capacity/cost reported explicitly. Initialization is
paired across dataarms WITHIN architecture, not between different architectures.

## Evaluation

All eight endpoints on all48sites. Main teacher Exact. Compare every identical
site/noise against archived WT-z, native Exact oracle choice, AA-only, and the
previous Δz student; their privileged target-s usage stays explicit. Also retain
Baseline/oracleR32 archived task comparators as diagnostics, not cheap methods.
Report Spearman,Top1,top3/5 overlap,regret,Δtask MAE/RMSE/scale and all scores.
Undefined constant-score Spearman is null, never zero or success; ties use
fixed AA order. Four-noise summaries and old-only choice/new-noise regret both
reported. Aggregate sites within protein, then equal-weight proteins; separate
train/seen-newsite/unseen-protein and fixed source-AA strata. No pooled
candidate/noise count as independent proteins. No thresholds fitted to results.

Expose per-protein regret/median/worst cases, not only top1 hits. For candidates
selected by each score head, retrieve archived **Exact** geometry in each noise,
including joint checked-geometry rate and severe/chirality details. This only
assesses the structures the native teacher produced at selected candidates:
score heads produce no coordinates and cannot claim to repair geometry.

Warm head-only20query timing on first locked site with20measured repeats after4
warmups is diagnostic only. Excludes WT C4, reference preparation and independent
hard evaluation; no end-to-end speedup or20C4 saving claim. Save actual training
parameters, time, memory, checkpoints and inference predictions.

## Integrity

Hash source/protocol, old completed report, teacher lock/manifest, train-label
files, evaluation-label file, reference GT and checkpoint. Training reads only
its train-label file; evaluation starts after all runs finish. WT-only loader
never requests a mutant conditioning. Independent check initialization/exposures,
optimizer steps, label normalization fromTRAIN, source data parity, ranking and
cross-noise choice. No new model generation/C4/S1. Use existing HIP-only physical
resource guard, max4workers. Stop after report. A successful scorer would not
establish structural distillation; a negative scorer result would not establish
intrinsic information insufficiency or final-state unlearnability.

## Pre-update execution correction

The first root `task_readout_v1_20261003` stopped before model initialization or
any optimizer update: broad `*.json` label hashing accidentally included the
controller's mutable status.json. Preserve that source/lock/log/failure. Correct
only label-manifest construction to explicitly include evaluation_labels.json,
train_restricted.json and train_expanded.json. Run the same scientific protocol
in new root `task_readout_v1a_20261003`; compare the three label-file hashes and
normalizers to the failed preparation. No outcome-based seed retry, hyperparameter
change or extension. The original no-retry rule applies to scientific runs, not
this pre-initialization metadata defect.
