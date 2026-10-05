# Native candidate budget — launch status, 2026-10-05

**Running, not completed.** The score-head A/B/C batch is closed at7b7b763b;
no head retraining or floor tuning is started. NativeC4 remains the reference and
default. This is a no-training baseline for retaining less realcandidate compute,
not a universalC1 requirement or a demonstrated WT-state reuse accelerator.

Reuse review found historical Stage0C1/C2/C4S1 parent-folding ninegrid scores,
and a C2S2/C4S2 warm-time/quality tradeoff. Their feature-cache/stochastic/GT/task
conditions differ from the current hard-mutant screening workload. ChordFold
explicitly did not execute latentwarmstart. See [protocol](mini_native_budget_v1.md)
and historical reports linked below; no comparable budget result is silently reused.

Locked9parents:5OI7,1C5E,4GN0,1JKE,3QR7,1LJ9,1XKO,4LR3 (previously observedDEV)
plus2V66stress. All4archivedADLTsites each,36sites,693uniquehardsequences.
EveryC1/C2/C4 arm recomputes its own nativefeatures/liveESM/fullconditioning,
then fournoiseS1coordinates. Neither targetC4s norz norWTlatent feeds cheaperarms.

Actual resident screening timing includes features, devicepreparation, ESM,
trunk, fourdenoisings, task/geometry checks andNPZwrite. Model loading and audit
are separate. No confidencehead/CIFservice benchmark or theoreticalspeedupclaim.
Quality includes19AAselection/cross-noiseC4regret, actual generatedgeometry,
fullstructurefidelity/tails toC4, and observedexperimentalWTquality.

ControllerPID1723064 started2026-10-05 15:57:04UTC (23:57:04HKT).
Earlysnapshot:294/2079conditioning,1176/8316S1,392/2772C4coordinate replays;
all observed C4replays bitwise match. No final selection/quality/timing conclusion.
9tests passed,1074frozenfiles match; originalmodel/helper code unchanged.
Inference is followed automatically byCPUquality, collection, independentaudit
and summaries. Failure preserves partialresults and stopsdependentstages.

Live remote:
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/native_budget_v1_20261005`

Local metadata:
`/home/husrcf/Code/onestepfold_runtime/native_budget_v1_20261005`

This page is a historical launch snapshot. Read runtime `status.json` and
`execution.json` for current status; do not duplicate after a connection timeout.

[Startup lock/checks](../reports/mini_native_budget_2026-10-05/)

Historical references:
[Stage0ninegrid](../reports/stage0_eval_summary_2026-09-16.md),
[Stage0confirmation](../reports/stage0_confirmation_2026-09-19/execution/confirm/report.md),
[ChordFoldclosure](chordfold_edit_findings_2026-10-01.md).
