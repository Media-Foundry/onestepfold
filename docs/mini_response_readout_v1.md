# Shared response readouts v1 — locked before outcomes

Follow-up to c34d9b59; new root `response_readout_v1_20261002`.
Hypothesis: distinguish WT encoder fitting from shared output organization. No model
promotion from single-site memorization. No AA-axis PCA, blockwise training, new hard
teacher collection, Mini tuning, Δs prediction or functional loss in training.

## Fixed bounded single-site experiment

1W53 T37 (parent3, zero36),19nonWT, same archived teachers and FP32 Δz subtraction.
Two seeds231301/231303, LR1e-3 fixed from the completed v2 grid, NOT reselected here.
AdamW wd1e-4/eps1e-8/clip1;8192full19-AA updates, checkpoints512/1024/2048/4096/8192.
No early stopping/best-checkpoint substitution. Twelve runs only:
3readouts × 2matrix targets(raw Δz, oracle R32 reconstructed Δz) × 2seeds.

- A/free_hidden: remove encoder; initialize20×L×256 free node hidden from the same
  large-bias encoder; train hidden AND original shared affine U/V heads. Fixed-site
  diagnostic only. No free per-channel U/V table; no deployment/transfer eligibility.
- B/pair: retain original large-bias encoder(width256,4blocks), replace U/V with
  shared nonlinear pair readout. Left/right node projections + discrete AA query +
  normalized WT z content, GELU→Linear128→GELU→Linear128channels. All pairs and chain
  lengths use the same function; no fixed-length row/full-field output table.
- C/channel: same encoder, nonlinear readout of node + discrete AA + learned channel
  embedding to2×R32 values. U random, V final rows zero initially. Shared nonlinear
  channel-conditioned factor rule; no canonical factor labels.

Different head parameter counts and computations are explicitly reported; this is
not a perfectly parameter-matched causal experiment. The encoder is initialized
identically in B/C; gradients update the whole model. No target s/z/s_inputs enter it.
R32 matrix targets use FP64 SVD followed by FP32 matrix reconstruction; compare against
their OWN normalized loss AND original hard Δz, including centered AA-specific NMSE.
Never report R32-label error as raw hard-response error. Monitor perAA/energy/gradient/
update-weight norms; keep every curve. Same-site low loss alone proves memorization.

## Small multi-context follow-up, conditional but no zero-shot site gate

If B or C (either label target) has original-hard-response NMSE≤.10 in BOTH seeds,
select the lowest two-seed mean raw error; tie within1e-6→fewest parameters→name.
A is diagnostic only. Single-site unseen-site error is reported, NOT a veto.

Selected architecture/label/LR: two FRESH initialized8192-update runs, cycle four TRAIN
contexts equally:1W53 T37+site84(parent3:36,83),1JHG site2(parent4:1),1A7G site65(parent5:64).
This gives2048exposures per context,19AA per update; do not pretend it matches single-
context per-site exposure. Evaluate training sites separately, held sites1JHG25/1A7G34,
and held TRAIN-source protein4PT4 sites10/17(parent6:9,16). The last protein was not
updated here but its archived panel already participated in development: no independent
test claim. Use no validation labels for selection or training. Stop after this bounded
stage; no automatic16→8 or expanded teachers, irrespective of the outcome.

If no B/C fits single-site, stop shared-generator training and retain all failures;
this does not undo whole-field dense memorization or prove a mathematical impossibility.

## Decoder closure and audit

Always decode the already completed whole-field dense LR1e-3/8192 checkpoints for
both seeds on1W53 T37, same two teacher noises230201/230211. This is a post-hoc diagnostic,
not fresh noise validation. Arms: Exact(target inputs/s/z), Baseline(WT inputs,target s/z),
WT-z, oracle R32, dense seed1/seed2. Target s stays oracle, target graph/chemistry rebuilt.
No C4 calls; replay Exact/Baseline to archived coordinates. Report19-AA Spearman/Top1/
regret, local RMSD P95/P99/max, lDDT, new geometry vs Baseline and raw reasons.
If a transferable B/C fits, add both terminal single-site checkpoints to this panel;
do not feed holdout functional outcomes back into model selection.

Head-only20-query forward latency, training wall time, peak allocated memory and actual
parameter counts are recorded. These exclude WT ESM/C4, decoder and reconstruction;
not an end-to-end speedup claim. No latency-based promotion without quality evidence.

Only physical HIP GPUs0–5; set HIP_VISIBLE_DEVICES only, remove inherited CUDA/ROCR
selectors. Never allocate6/7. One worker per allowed device. Input/code hashes locked
before jobs,8192terminal reports and checkpoint hashes audited, two checkpoint replays
per run, explicit failed/skipped denominator; unexpected execution errors stop progression.
