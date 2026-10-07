# Mini multi-reference structure learning — execution 2026-10-07

**Status: preflight passed; the fixed eight-run queue is active. No new training
quality, transfer or acceleration conclusion yet.**

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

Training executes four n15 runs followed by four n3 runs on available guarded
workers, without failed-seed retries. Each run has the protocol's fixed update
budget. An infrastructure timeout (90 minutes preflight, six hours per worker)
retains an incomplete/failed record; it does not create a replacement seed or
extend scientific exposure. Fixed checkpoint evaluation is independent of latent
fit. Total expected training-worker calls, if all complete: 222,260 S1 including
evaluation and timing, 77,824 optimizer updates. Preflight and later independent
checkpoint replay are accounted separately.

The 1,100-file execution snapshot is frozen in `lock.json`. An independent
coordinate scorer/replayer is separately frozen in `auditor_lock.json`; its
copy adds response metrics without modifying running execution code. All
metrics use the protocol's fixed definitions and parent-level experimental units.
Native preparation and archived ESM/C4 costs are outside model-only timing.
Concurrent-worker timing is descriptive, not an isolated end-to-end benchmark.

Large checkpoints, prepared chemistry packets and coordinates remain in the
remote execution root; this directory initially contains lock/preflight/status
metadata. Terminal reports and independent scoring/replay evidence will be added
after the queue completes. Prior development holdouts and prior failure records
remain unchanged.
