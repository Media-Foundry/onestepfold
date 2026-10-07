# Mini multi-reference structure learning — execution 2026-10-07

**Status: CLOSED. All eight runs, independent scoring and 36 checkpoint replays
completed. No promotion.** Training ranking improves; held-reference response,
ranking, selection and geometry do not improve together. Workspace mean regret
has positive observations that are retained separately.

[Full findings](../../docs/mini_reference_editor_multiref_findings_2026-10-07.md).

[Locked protocol](../../docs/mini_reference_editor_multiref_v1.md) and
[fixed data/run plan](../mini_reference_editor_multiref_plan_2026-10-07/README.md).
Execution root: `reference_multiref_v1_20261007` on DiamondHill. The preparation
plan retains its original historical `prepared` status; this execution record
and `controller.json` describe the subsequent authorized run.

The original Mini workspace implementation is unchanged. The direct control
inherits its cache, validation, anchored complete-conditioning and late pair
writeout, replacing workspace iteration with broadcast hard edits and four
pointwise residual node MLPs. Registered parameters: 9,352,387 / 9,320,643.
Shared modules have identical initialization hashes for each paired seed;
architecture-specific parameters use independent deterministic RNG streams.
Neither control uses oracle target conditioning during inference or training.

Preflight results:

- All 24 WT references and 912 non-WT candidates replayed on both archived noises
  with bit-identical Exact coordinates. Separate reference-only outputs saved.
- Four architecture/seed combinations passed real-shape cache/fresh, no-edit,
  candidate permutation and subset checks (maximum error 0).
- Structural loss through frozen S1 gives finite nonzero required branch gradients
  in all four combinations. Mini gradients remain absent.
- Gradient-connected parameter counts: 9,351,554 / 9,319,810. The two disconnected
  biases (`input_out.bias`, `single_out.bias`, 833 values) are inherited equally
  and intentionally absent from anchored linear writeout, not matching padding.
- 3,708 S1 calls, zero C4, zero input-encoder calls, zero parameter updates in
  preflight; 386.58 seconds. These are engineering checks, not learning results.
- Fourteen local focused tests passed, including schedule/leakage, paired
  initialization, global response, cache/gradient, device-policy and response
  metric checks.

All four n15 and four n3 runs completed their fixed budgets without replacement
seeds or timeouts. Fixed checkpoint evaluation was independent of latent fit.
Actual training-worker calls: 222,260 S1 including evaluation and timing,
77,824 optimizer updates. Adding 3,708 preflight and 72 independent checkpoint
replay calls gives 226,040 S1 calls. No new C4/input-encoder calls. All 36 saved
checkpoints reproduce the fixed T37A/two-noise coordinates bitwise. Controller
wall time was 8,298.32 seconds; independent scoring/replay completed subsequently.

The 1,100-file execution snapshot is frozen in `lock.json`. An independent
coordinate scorer/replayer is separately frozen in `auditor_lock.json`; its
copy adds response metrics without modifying running execution code. All
metrics use the protocol's fixed definitions and parent-level experimental units.
Native preparation and archived ESM/C4 costs are outside model-only timing.
Concurrent-worker timing is descriptive, not an isolated end-to-end benchmark.

Large checkpoints, prepared chemistry packets, coordinates, full `scores.json.gz`
and `history.jsonl` remain in the remote root:
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/reference_multiref_v1_20261007`.
Prior development holdouts and prior failure records remain unchanged.

Collected evidence:

- `collection_manifest.json` / `collection_verification.json`: all 81 collected
  payloads verified by size/SHA-256; ranks and cross-noise regret recomputed;
  counts, fixed exposure and replay assertions checked. Large files not committed
  here retain their remote relative path and hash in this manifest.
- `runs/<run>/report.json`, `summary.json`, `execution.json`, exposure manifests
  and `checkpoint_replay.json`: complete run and independent audit records.
- `aggregate.json` and `terminal_tables.md`: automatic terminal summaries, with
  all seeds and actual size-dependent evaluation strata.
- `learning_curve.csv`: every fixed evaluation, equal-parent metrics and pooled
  structure/geometry tails. `sites.csv`: all site-level scores and selections.
- `training_windows.csv`: losses/gradients/clipping over complete 19-visit AA
  cycles, retaining the same exposure composition within each run.
- `derived_analysis.json.gz`: full site score arrays, additional shared-five-site
  comparisons, named stress cases and sampled worst-output records. This is a
  descriptive post-run analysis, not a change to the locked main endpoint.
- `held_learning_curve.png` / `.pdf`: common nine-protein curves; seed-range
  shading is not a confidence interval. Terminal 64-exposure results remain primary.
