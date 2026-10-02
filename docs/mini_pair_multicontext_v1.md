# Raw pair readout: bounded multi-context learning and unconditional decoding

Locked before new training/results, following b0851cb6. The architecture/label choice
uses development evidence; the old NMSE<=0.10 failures remain unchanged. No new NMSE
gate, architecture search, functional loss, Mini tuning, teacher C4, or Δs predictor.

## Model, updates and exposure

Unchanged NonlinearResponseReadout(kind='pair'): large WT encoder(width256,4blocks),
nonlinear shared pair readout width128, 3,627,904 parameters. Inputs only WT s/z,
mutation position, WT AA and candidate hard AA. Supervision is raw FP32 target z-WT z,
mean of 19 per-AA normalized matrix MSEs; old normalization floor retained.
AdamW lr1e-3,wd1e-4,eps1e-8,global gradient clip1, no scheduler. Seeds231301/231303,
both freshly initialized, never continued from single-site weights.

Cycle these four contexts in this fixed order, every update contains all19 non-WT AA:

| Context | Archive parent / zero-based position | Role |
|---|---|---|
| 1W53 T37 | 3 / 36 | train |
| 1W53 Y84 | 3 / 83 | train |
| 1JHG A2 | 4 / 1 | train |
| 1A7G N65 | 5 / 64 | train |
| 1JHG N25 | 4 / 24 | seen protein, unseen site |
| 1A7G S34 | 5 / 33 | seen protein, unseen site |
| 4PT4 L10 | 6 / 9 | unseen protein in this training |
| 4PT4 D17 | 6 / 16 | unseen protein in this training |

Each seed:32768 updates=8192 complete AA-batch exposures/context. Snapshot at global
updates8192/16384/32768, i.e.2048/4096/8192 exposures/context. Evaluate ALL snapshots,
terminal32768 is primary; no best-checkpoint selection, early stopping, LR change or
extra steps. Held-site/protein labels never enter optimizer. Finite execution failures
stop the batch and stay in the denominator. No automatic16->8 or expanded sampling.
4PT4 and these archives already participated in development: not independent testing.

## Frozen decoder panel and budget

All8 contexts, all19 non-WT, old noises230201/230211 and new noises270101/270103,
locked here before outcomes. New means unused in this response panel, not a claim
of global uniqueness across every historical random-number generator.
Arms:Exact(target s_inputs/s/z), Baseline(WT s_inputs,target s/z), WT-z,
oracle per-channel spatial R32 z, and all6 student checkpoints.
Every intervention uses exact target s, WT s_inputs and independently rebuilt native
target chemistry/atom graph. WT is bypassed to original WT output for every arm.
No full mutant trunk replacement or deployable accelerator claim.

Cache each checkpoint's19-AA prediction once/context for all noises. Reuse reference
outputs across checkpoints. Exact/Baseline old-noise outputs and WT must reproduce
archived coordinates bitwise. Repeat Baseline at the first non-WT AA of each context
for both new noises to check deterministic replay. Reject C4 calls with a hook.
Budget:8*19*4*10 +4parents*4WT =6096 distinct S1 outputs, plus16 new-noise replays,
total6112 S1 calls. Scored rows6400 include WT reused across sites/arms, not6400 calls.

## Predeclared evaluations; no post-hoc functional pass threshold

Report train / seen-protein-new-site / unseen-protein separately at every checkpoint
and seed, with site records and equal-protein-weighted summaries. Do not pool152
mutants or608 mutant/noise instances as independent proteins. Training group has3
proteins/4sites, new-site group2proteins/2sites, new-protein group1protein/2sites.

- Raw and centered AA-specific NMSE, response energy, perAA error; train curves,
  gradient norm, update/weight norm, per-context exposure counts.
- Same-noise19-AA Spearman, Top1, Top3/5 recall, teacher-best inclusion in student
  Top3/5, regret, score MAE/RMSE/bias and centered scale ratio, versus BOTH references.
- Arithmetic mean scores over old pair, new pair and all4 noises. Rank the mean
  scores (never average ranks or choose best noise). Report chosen AA and regret.
- Cross-noise selection: choose using old-pair mean only, evaluate chosen AA on
  new-pair Baseline mean; report regret to new-pair optimum and extra regret versus
  the old-pair Baseline-selected AA. No new noise is used to retrain or reselect.
- CA/all-atom lDDT, global/local RMSD, pair-distance/contact/distogram differences;
  P95/P99/max local RMSD and >1Å counts; no change to neighborhood or metric definitions.
- Baseline pass->fail and fail->pass identities, absolute geometry passes, severe
  pairs and checked chirality. Record wrong-centre atom identities, signed volume,
  reference-oriented normalized volume and volume ratio; retain all centres for
  1W53 T37N at every noise/arm. Existing zero-sign rule is unchanged.

No softmax temperature, biological-probability or thermodynamic calibration claim.
The task is parent experimental-CA distance proxy, not mutant experimental effect.
Geometry means zero severe heavy-atom collisions plus strict CHECKED chirality, not
complete chemical validity. Geometric failures are disclosed research outcomes,
not a reason to suppress decoding. 6UFE-92 stays an old stress case outside this panel.

## Provenance and stopping

Hash source/protocol/teacher manifests before training; checkpoint hashes fixed
before decoding. Audit fresh initialization, exposure counts, checkpoint/latent
replay, old/new coordinate replay, ranking/score aggregation and geometry identities.
Only HIP_VISIBLE_DEVICES chooses devices, with the existing physical PCI guard;
workers use safe HIP0..3, training on0/1. No external structure downloads.
Record training/decode wall time and memory; this shared-machine batch is not an
end-to-end speed benchmark. Final deliverable is a complete bounded report, followed
by a separate decision on further multi-context data or matched functional continuation.
