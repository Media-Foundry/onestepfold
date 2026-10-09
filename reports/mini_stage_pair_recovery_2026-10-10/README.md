# Native-stage-aligned Mini pair-recovery evidence

Current snapshot: **n1 complete; n15 pending**, not a closed full experiment.
`interim_manifest.json` hashes the completed single-site evidence and a controller
snapshot. `analysis_interim.json` and `verification_interim.json` explicitly set
`scientific_experiment_complete=false`. A separate final `manifest.json` will be produced only after all eight accepted
runs and their independent checks complete. The original controller is now failed:
one n15 worker stalled after1420, a separately locked prefix replay succeeded,
and exactly one unchanged operational retry is running under the original absolute
deadline. Do not select the other three models or treat a runtime failure as quality.

`runtime_snapshot/manifest.json` is a later, explicitly incomplete operational
snapshot (retry observed at4104). `verify_runtime_snapshot.py` independently checks
its72file hashes, failed-attempt preservation and4260identical prefix scalars.
`runtime_snapshot_verification.json` is NOT completion of the scientific trial.
The original115-file interim manifest still describes the earlier committed raw
snapshot. It is not silently replaced by the later runtime state.

`diagnose_objective.py` reconstructs the fixed TRAIN objectives using saved full-
field moments, originalq and lengths. It separates frozen-checkpoint objectives
from moving-parameter optimizer-history means; it does not select new weights or
hyperparameters. The optional n1-only output is descriptive and already available.

Two predeclared cohorts (one historical TRAIN site; original15TRAINparents),
two objectives (final; equal-weight corresponding block14 and final labels),
two paired seeds. Architecture begins at the actual candidate block13 pair and
copies native blocks14/15; B_inputs/B_s remain frozen. Initial native function
must replay exactly. No target intermediate state is a predictor input.

See[protocol](../../docs/mini_stage_pair_recovery_v1.md). `build_lock.json` and
the per-cohort training locks bind source, cached inputs, labels and budgets.
Native cache preparation is counted separately. `manifest.json` hashes raw
exported evidence. Full pair caches/checkpoints/coordinates stay at the recorded
runtime root. Independent read-only checkpoint re-forwards use NumPy FP64 to
check latent arithmetic; they add no training/native/S1 calls and are counted
separately from the scientific run. Their exact source is in `verification_code`.

`verify_results.py` verifies all source hashes, source membership, exposure,
first-step pair gradients, historical controls, scores and geometry counts.
`analyze_results.py` retains every fixed node and paired objective comparison.
n1 has no protein-bootstrap inference; all n15 panels remain development data.
No winner selection, no changed scientific budget, no new folding-speed claim.
