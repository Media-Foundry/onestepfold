# Pretrained ESMC GT adaptation and nested training-size comparison

2026-09-27. The user authorized expanding training and using DiamondHill's eight
GCDs. Primary deployment remains frozen ESMC-600M, one Pairformer cycle, one
structure evaluation, one sample. No frozen temporal test access.

Starting point: accepted native Mini-ESM folding weights with the TRAIN512-fitted
1152→449 affine ESMC projection. This is pretrained adaptation, not scratch
training. The existing native/bridge evaluation gives DEV128 lDDT 0.81965/0.79190
and worst-5% 0.50746/0.42412. Retaining the folding prior recovers substantial
quality; a meaningful tail gap remains.

TRAIN8192 is accepted and exactly nests TRAIN2048, with unchanged DEV128. All
ESMC features are cached. Sequence length remains 32–256; expanding this window
is a separate question. DEV has substantial homology to TRAIN and is reused for
development, so it cannot establish novel-fold generalization.

## Distributed execution gate, locked before launch

Use four DiamondHill GCDs and eight TRAIN-only examples from the accepted bridge
bundle. Sort all 512 TRAIN rows by `(length, group_id)` and select rounded indices
`round(i * 511 / 7)` for i=0…7. This covers 33–256 residues without selecting model
errors. The first diagnostic batch uses sorted indices [0,2,5,7], the second
[1,3,4,6]. No DEV coordinates enter the gradient check.

Verify collective sum; exact common/source/data hashes; exact accepted initial
model-state hash; one trunk/one structure/no confidence in each forward; finite
nonzero bridge and atom-decoder gradients; identical all-reduced gradient and
updated-state hashes on every rank. Compare the first distributed gradient with
a separate serial mean over the same four targets and noise seeds, requiring
relative L2 error ≤1e-4. Check an exact model/optimizer save–reload and a second
successful distributed update. Confidence and distogram heads stay unchanged.
Diagnostic weights are discarded, never used as the training parent.

Retain the existing coordinate objective `A + 0.1 F + R + 10 D`. Fresh AdamW,
bridge LR 1e-4/core LR 1e-5, betas (0.9,0.999), epsilon 1e-8, weight decay 1e-4,
global gradient clip 10; one protein per rank, global batch four, protein-equal
loss. Actual inference schedule and sampler parameters are recorded, including
[2560,0], gamma0=0 and step_scale_eta=1. No new loss/noise/geometry grid.

The optimizer is constructed after moving the model to its device. Checkpoint
resume preserves optimizer moments. A bounded 15-minute launcher timeout catches
communication failures; logs and failed artifacts must remain available.

Full matched-training budget, evaluation checkpoints and final acceptance rules
will be frozen after this execution/timing gate and before GT training starts.
Training on8192 has not yet started.

## Training protocol locked after the passing execution gate

The four-rank gate passed (PID1516484, exit0). Serial/distributed mean-gradient
relative error4.1505e-8 over1355 tensors; exact per-rank gradients, state updates,
checkpoint reload, and unchanged heads. Warm update1.68s; first-call10.86s includes
warmup. Treat this as a rough ETA, not a throughput benchmark.

Two concurrent runs on DiamondHill, GCD0–3 for TRAIN2048 and4–7 for TRAIN8192.
Same accepted initialization; discard both preflight updates. Four proteins/update,
4096 updates,16384 sample presentations in each arm:8 exposures/protein at2048,
2 at8192. This matches updates and samples, not exact FLOPs or convergence.
Record residues seen, measured optimization/evaluation/checkpoint seconds and
reserved four-GCD hours separately. Hard launcher limit4h per run; an incomplete
run does not pass the matched4096-update comparison.

Fresh optimizer and constant LRs as above. Each epoch visits every TRAIN group
once. Hash shuffle using seed101 and one-based epoch, sort lengths within pools
of64, split into four-protein batches, then hash shuffle batches. This reduces
idle time from length imbalance without dropping examples or changing loss
weighting. Sampler noise uses the existing `training_sampler_seed(group,epoch)`.

Export fixed DEV128 and32 common TRAIN probes at updates0,512,1024,2048,4096;
probes selected by the same evenly spaced length rule within the accepted512,
independent of errors. At step0, all320 coordinates must exactly replay the
accepted bridge output before any optimizer update. Two fixed noises12345/54321
are separate K=1 draws, averaged per target for paired analysis, never best-of-K.
All checkpoint weights and final optimizer state are saved. Recovery snapshots
every128 updates are retained atomically; no automatic retry after worker failure.

Primary comparison is the predeclared final4096 update. Intermediate curves are
secondary; do not replace the primary endpoint with the best checkpoint. Score
saved predictions independently on HPC3 using the same observed masks, atom
correspondence and all-atom lDDT/CA-lDDT/TM metrics, plus C–N MAE and chirality.
Report mean, worst5% (ceil(.05N)), paired deltas and fraction losing>.05 in lDDT
or TM against both initial ESMC bridge and native ESM2 reference. Compare8192
versus2048 at equal samples/updates and disclose measured compute differences.
Protein bootstrap5000, seed20260926; CIs are exploratory and not adjusted for
homology or multiple comparisons. Tail improvement needs direct evidence, not
an inference from the mean. Chemistry metrics are partial, not full acceptance.

This first expansion can establish learning progress at a fixed budget. It does
not establish convergence, superiority of ESMC over ESM2, scratch learning,
independent generalization, or the final end-to-end deployment goal.

## Hardware amendment before any GT training: HPC3 fallback

At01:30–01:35 DiamondHill became unreachable (SSH connection timeouts, including
fresh sessions). Its DDP preflight is accepted; no GT training was launched.
The single-stream transfer was deliberately stopped after measuring ~100MB/s;
3021 completed files were hash-verified and excluded from four disjoint remaining
transfer lists. The parallel controller is still in metadata staging; no training
was delegated to it. Do not restart it or launch duplicate DiamondHill training.

To avoid waiting, prepare the same two four-GPU runs on HPC3 H100. All data are
already accepted there. Preserve the DiamondHill v1 lock and failed/interrupted
transfer artifacts. Re-run the same two-update DDP gate on H100 and rebuild only
the fixed160-target (DEV128 + commonTRAIN32) native/bridge initial reference, using
both noise views, on H100. Cross-backend RNG need not produce identical coordinates;
therefore do not weaken the exact initial-replay gate to accept different outputs.
The H100 runs must exactly replay their own saved H100 reference. Report native
and ESMC baselines from the same hardware; compare DiamondHill only descriptively.

This changes the execution backend, not the data, model, optimizer, objective,
4096-update budget, sampling, evaluation targets or primary endpoint. A separate
HPC3 root/lock and immutable source snapshot will bind the H100 baseline and DDP
acceptance before either training arm starts. No duplicate adaptation experiments
will run on DiamondHill when it reconnects.

## Execution status:01:43 HKT

H100 DDP654959 completed1m30s, serial-gradient relative error3.70017e-8,
exact optimizer/model reload, warm four-protein update0.657s. First reference
654962 stopped before GPU execution because the copied bundle manifest still
bound the previous source manifest. Preserve v1. Isolated v2 updated the source
binding;654973 completed1m18s with all640 predictions. CPUscore654975 completed
1m08s, all640 coordinate hashes and16 dense-lDDT checks passed. Two focused
scheduler/optimizer tests also passed. Four score files, lock and source manifest
were copied and their hashes verified against HPC3.

Separate HPC3 lock SHA256:
`9a709fb1427f805336c1efbfe853db0a7930a8416acda6bd41fb403905781d7d`.
Source manifest:
`9f446b7f56e40952782fc43273994cec754dacd95d3ab61204e64fc22589edf3`.
Both runs enforce NVIDIA H10080GB and the same frozen runtime; original accepted
HPC3 packets are reused with per-load input/supervision hash checks.

Jobs654978(TRAIN2048) and654980(TRAIN8192) are RUNNING onACD1-52,4H100 each.
Initial320-coordinate replay per arm precedes the first optimizer update.
Controller `scripts/finish_pretrained_gt.py`, PID740846/session44056, submits
independent CPU scoring only after an evaluation export is complete, then the
fixed-endpoint report after both runs/all scores finish. It caps its score jobs
at2 and respects the5-debug-job limit. No automatic restart after failures.
Timed worker GPU hours are reported separately from Slurm elapsed allocation
records. Full training quality and the original deployment goal remain unproven.

Update01:45 HKT: both initial320-coordinate replays passed exactly and both runs
completed32 optimizer updates, roughly1.0s/update. Provisional completion75–90min;
first512-update quality about10min. InitialCPUscore654986/654987 completed0:0 in33s/31s.
H100initialDEV native/bridge meanlDDT0.819560/0.792012 and worst5%0.506955/0.423968.
These are the same-hardware references, not trained improvements.

## Read-only monitoring and checkpoint acceptance

Added after launch without changing either training worker or its lock: an interim
report reads only independently scored fixed checkpoints, shows mean/worst5%
lDDT/TM, commonTRAIN32 quality and chemistry, and pairs each arm against native
and initial ESMC references. It does not select a checkpoint or change the4096
primary endpoint. TRAIN8192 is not fully encountered before2048 updates.

A separate checkpoint audit reloads the saved model and exactly replays32 outputs:
eight length-spaced targets from commonTRAIN32 plus eight length-spaced DEV128,
both existing evaluation noises. Sort by(length,group_id), choose rounded indices
`i*(n-1)/7`, i=0…7. Verify checkpoint/model/export hashes, frozen heads against the
original initializer, one trunk/one structure/no confidence, sampler settings,
unchanged weights and exact coordinates. These are reconstruction checks, not new
training or an independent generalization claim. Exercise this new audit once on
TRAIN2048 step0 (job655003); after it passes, apply it to both final4096 checkpoints.
Audit source is isolated in `checkpoint_audit_code_v1`; no live training edits.

Checkpoint reconstruction preflight655003 completed0:0 in53s: all32 predictions
replayed exactly, frozen heads and weights unchanged. Separate monitor5870/
PID742304 schedules fixed interim plots and final audits; it uses its own job
record and archives outputs independently of the main scoring controller.
