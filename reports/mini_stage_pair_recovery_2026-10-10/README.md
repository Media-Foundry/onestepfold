# Native-stage-aligned Mini pair-recovery evidence

Final status: **all eight runs and all fixed checkpoints complete; not promoted**.
`manifest.json`, `analysis.json` and `verification.json` report completion of the
locked scientific experiment. This is not completion of the research goal or
qualification of a faster folding model. See the [full report](../../docs/mini_stage_pair_recovery_findings_2026-10-10.md).

The original controller remains failed: one n15 worker stalled after update1420.
A separately locked prefix replay succeeded, followed by exactly one unchanged
operational retry under the original absolute deadline. Training, scoring and
independent verification all completed. `execution_recovery.json` is closed;
`source_provider_map` identifies the one accepted result from `runtime_retry_v1`.
Failed-attempt, replay and retry records remain separate. No run or checkpoint
was selected by its quality.

`interim_manifest.json`, `analysis_interim.json` and `verification_interim.json`
describe the earlier incomplete snapshot at commit `2c63ad13`. Their completion
flags remain false. Some top-level operational logs subsequently advanced, so
verify that historical manifest against that commit, not against newer logs.

`runtime_snapshot/manifest.json` is a later, explicitly incomplete operational
snapshot (retry observed at4104). `verify_runtime_snapshot.py` independently checks
its72file hashes, failed-attempt preservation and4260identical prefix scalars.
`runtime_snapshot_verification.json` is NOT completion of the scientific trial.
This72-file snapshot was sealed at commit `fa187177` and remains unchanged.
It is not silently replaced by the completed results.

`diagnose_objective.py` reconstructs the fixed TRAIN objectives using saved full-
field moments, originalq and lengths. It separates frozen-checkpoint objectives
from moving-parameter optimizer-history means; it does not select new weights or
hyperparameters. `objective_diagnostic.json` covers all eight completed runs;
`objective_diagnostic_n1.json` retains the earlier n1-only analysis.

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

`learning_curve.png` / `.pdf` show every fixed node and historical controls.
`summarize_tails.py` writes `tail_decomposition.json`, with per-parent geometry
counts checked against the scored totals and the three largest local deviations
for each fixed method and panel. These are descriptive diagnostics, not a new
selection rule.

The final export contains212 hash-verified files. Its transferred archive SHA256
is `0a1b9d04f36f060766f48df5e4b71bb5223d6063d8633dcf1328c5ef1d2ce94a`;
`transfer_verification.json` records the checked import. Verification covers32
checkpoint nodes,596 site/checkpoint replays,7740 correlations,2580 regrets and
98040 output records including repeated controls. Accepted scientific training
used65664 updates. Including the discarded attempt and diagnostic replay gives
68505 recorded updates, plus at most one unobserved partial update. Preparation
and accepted evaluations used31920 S1 calls; including failed-attempt initial
evaluation gives33744. Independent tensor checks add11420 recovery forwards.
These accounting categories are not deployment speed measurements.
