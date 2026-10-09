# Native-stage-aligned Mini pair-recovery evidence

Current snapshot: **n1 complete; n15 pending**, not a closed full experiment.
`interim_manifest.json` hashes the completed single-site evidence and a controller
snapshot. `analysis_interim.json` and `verification_interim.json` explicitly set
`scientific_experiment_complete=false`. Once the full controller and all eight
independent replays finish, the full export uses a separate `manifest.json`.
The final/272003 joint run has an anomalously long update; do not select the
other three runs or classify this unresolved runtime state as model quality.

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
