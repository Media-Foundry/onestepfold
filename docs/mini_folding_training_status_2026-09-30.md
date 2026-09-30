# TRAIN128 versus TRAIN423: continuation started on HPC3

This is the folding mainline, with ESM2 and C4/S1/K1 fixed. BindCraft/interface
work remains deferred; ESMC is a later matched conditioner-interface comparison.
The scientific protocol is [folding scaling cycle v1](mini_folding_scaling_cycle_v1.md).
No new held-out model-quality result is available at launch.

## First TRAIN128 probe: modest fitting improvement, new damage remains

At512 new updates, the locked original-TRAIN32 probe (two training noises each)
shows the following paired change. These proteins are used for training, not
validation; no checkpoint selection or budget change follows from this observation.

| Metric | Retained starting point | TRAIN128 +512 updates |
|---|---:|---:|
|All-atom lDDT|0.804772891|0.807179219|
|Cα-lDDT|0.885653254|0.887278297|
|Zero severe pairs and strict checked chirality|41/64|47/64|
|Total severe pairs|394|330|

Protein means improve for29/32 in AA and27/32 in Cα; none has mean AA loss
greater than0.05. Nevertheless,2 previously collision-free instances acquire severe
pairs, and2 previously strict-stereo instances lose that status. Better aggregate
geometry is not uniform preservation or full chemical validity. TRAIN423 has not
yet reached the same512-update probe at this observation, so no between-arm
quality comparison is available.

Both probe reports have exact locked coverage;128 saved coordinate files across
the two timepoints were checked for hashes and finite values. This is an interim
artifact check, not the final independent training audit or GT score recomputation.
Files: `reports/mini_folding_training_2026-09-30/interim/`.

## Terminal evaluation now queued

The fixed-terminal pipeline is implemented and submitted under `acd_u` in a
separate frozen-code root. Training is still running: at the archived observation,
TRAIN128 had407/2048 updates and expanded423 had300/2048, with no reported errors.
These counters do not establish quality improvement.

| Job | Work | Dependency |
|---|---|---|
|662313|bind audited checkpoints and evaluation lock|audit662294|
|662314|first of eight evaluation shards|prepare662313|
|662315–662321|remaining seven evaluation shards|first shard662314|
|662322|scheduler/coverage audit, GT scoring and cohort summaries|all eight shards|

All evaluation jobs are currently dependency-pending, not completed predictions.
Any failed dependency cancels downstream work. GPU workers use one H100 allocation
each; preparation/scoring reserve a hidden unused GPU as required by `acd_u`.
CPU scoring has12 single-thread workers. No active training code or scientific
budget was changed.

Compare publicS1/S2, retained512 and both fixed2048 terminals on455 proteins with
two assigned noises:4550 outputs. Reuse1692 audited TRAIN reference outputs;
2922 new prediction NFEs plus80 engineering-probe NFEs. OriginalTRAIN128,
addedTRAIN295 and newVAL32 are summarized separately with protein-level bootstrap
and paired tails; no best-of-noise. Experimental GT scoring has an independent
dense-distance check. Length and assembly subsets remain descriptive.

Three focused tests pass, including missing/duplicate-record rejection and an
adversarial two-noise case that must not become best-of-two or joint chemistry
success. The continuation loader still enforces exact terminal budget, parent,
origin lock and parameter scope before copying tensors. Actual GPU checkpoint
replay for the new terminals awaits completion of training.

Protocol: [fixed terminal evaluation](mini_folding_terminal_evaluation_v1.md).
Remote: `/data/user/shuang886/Folding/folding_scale_evaluation_v1_20260930`.
Submission, scheduler observation, deployed hashes and launcher:
`reports/mini_folding_evaluation_2026-09-30/`.

## Cache audit completed

Eight workers completed successfully. CPU audit662257 completed in7m11s:

-455 native C4 conditionings, comprising423 TRAIN and32 new validation;
-1692 TRAIN-only native S1/S2 reference coordinates,423 exact cache-reload replays;
-1820 Pairformer cycles and2961 diffusion calls including replay;
-55,800,460,070 bytes of cache artifacts checked by SHA256;
-684,611 observed TRAIN atoms and1895 missing atoms correctly masked;
-no validation predictions or validation supervision labels generated.

The audit independently checked observed GT coordinates, distance supervision,
neighbor normalization, bond labels, feature finite values, worker coverage and
source/model hashes. Synthetic S2 coordinates remain explicitly auxiliary labels,
not experimental GT. Conditioning never receives experimental coordinates.

## Runtime and checkpoint preflight completed

Preparation662281 completed4s; GPU preflight662283 completed1m02s on H10080GB.
The two probes are the shortest and longest original TRAIN proteins (52 and968
residues), selected before outputs. Public checkpoint predictions match their
HPC3 cache bitwise; retained trained-checkpoint reload also replays bitwise.
All288 selected diffusion tensors have finite, nonzero gradients on both probes.
All parameter values remain unchanged during this no-update preflight, and the
frozen parameters match the public model. Peak allocated memory16,763,567,616B.
The same retained parent SHA is used by both arms, with identical initial parameter
fingerprints. These are runtime/gradient-coverage checks, not new quality claims
or an end-to-end soft-sequence derivative certification.

Two focused tests passed: locked LR endpoints/update bounds, and checkpoint
metadata/scope/nonfinite rejection before any parameter copy. Existing model
implementation and public numerical backend were not changed.

## Running jobs

| Job | Work | Budget |
|---|---|---|
|662290|TRAIN128 continuation|2048 new updates,8192 exposures|
|662291|TRAIN423 continuation|2048 new updates,8192 exposures|
|662294|post-training audit|after both successful completions|

Each training arm uses one H100,4 CPUs,96GB host-memory allocation; scheduler
wallclock cap3h, scientific budget remains fixed. No auto-extension or early
checkpoint choice. The post-training audit reserves a hidden unused GPU due to
acd_u policy. Dependency failures cancel the audit rather than leave an impossible
job queued indefinitely.

Both arms reset AdamW, retain the locked schedule/loss and freeze all non-diffusion
parameters. Original TRAIN32 probe is hash-locked, with both training noises at
updates0/512/1024/2048. Coordinates, AA/Cα-lDDT, geometry and loss histories are
saved. Probe inference is reported separately from8192 training NFEs:256 additional
calls per arm. All four probe points use identical targets and scoring; none uses
new validation proteins. Same exposure budget is not equal GPU time or equal
per-protein exposure (128:64 passes;423:19 passes plus155 samples).

Independent terminal audit checks orders, optimizer steps, LR, initial fingerprints,
frozen parameters, complete probe coordinates and checkpoint provenance. New
validation evaluation is not automatically authorized by merely observing lower
TRAIN loss; it follows the locked fixed-terminal protocol and successful audit.
Full terminal TRAIN and newVAL32 comparisons are still outstanding.

Remote root:
`/data/user/shuang886/Folding/folding_scale_training_v1_20260930`

Source/cache roots and split remain those in the prior resume report. Raw lock,
cache audit and preflight reports are archived under
`reports/mini_folding_training_2026-09-30/`. Checkpoints at512/1024/2048 are retained
for provenance and training curves; only2048 is the predeclared terminal candidate.
The new checkpoint schema is `folding_scale_continuation_v1`, distinct from the
old512-update parent, so an old loader cannot silently misidentify it.
