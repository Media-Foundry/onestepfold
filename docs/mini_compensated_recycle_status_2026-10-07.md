# Mini compensated last recycle: preflight passed, training started

**Historical launch snapshot.** Both runs and audits subsequently completed;
see [2026-10-08 final findings](mini_compensated_recycle_findings_2026-10-08.md).
The collected controller/evidence files now reflect completion.

Implementation commit: `fda8f488`. Execution directory:
`DiamondHill:/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/compensated_recycle_v1d_20261007`.
Protocol: [mini_compensated_recycle_v1.md](mini_compensated_recycle_v1.md).
Frozen execution lock SHA256:
`d754f35c4b061f54862609cf8836ea078273e2b81e962ef8ddaf3c3853fa51a6`.
The local [evidence snapshot](../reports/mini_compensated_recycle_2026-10-07/)
has five collected files /429,609 bytes, each checked against its remote SHA256.

## Verified, before training

Ten focused local tests passed, including native split RNG parity, input-encoder
bypass, prefix ownership, candidate independence, global correction, no-edit,
zero initialization, gradients, and empty native constraints returning None.

Native preflight completed in727.749s:

- All24 WT cached-input C4 final tensors and two-noise coordinates replay bitwise.
- All912 hard candidates replay archived C4 final tensors and two-noise Exact
  coordinates bitwise; their target3→target1 continuation is audit-only.
- Candidate s_inputs are saved in a separate tensor-only cache. Target final s/z
  are discarded after audit and never provided to the compensation network.
- Each WT3 prefix is read-only. Unadapted WT3→Target1 two-noise baseline was
  generated for all912 candidates.
- Both fresh seeds reproduce that baseline at the fixed preflight candidate.
  Their full-panel zero-checkpoint replay remains part of the training workers.
- Registered trainable parameters: **1,420,160**. Original Mini135.22M stays frozen.
  Gradients through native last recycle and S1 reach both zero output heads.
  After one dry update, AA and mutation-anchored pair relation gradients are
  finite/nonzero for both seeds. Four dry optimizer updates total are discarded.
- Native model parameters and checkpoint hashes remain unchanged. No input
  encoder, ESM or MSA preparation was called. Peak allocated preflight memory
  1,929,728,512 bytes is a preflight measurement, not a training-memory bound.

Preflight executed **4,668 native recycle passes and3,704 S1 calls**. This includes
full cold C4 replay audits, unadapted continuation, and gradient/order probes.
Do not interpret the inherited `counts.c4=0` field as zero trunk computation:
that counter tracks the old forbidden full-forward entry; native passes are
explicitly counted in `counts.recycle`.

## Active bounded experiment

Two fresh seeds272001/272003, each8,208 updates, two candidates/update,
32exposures/AA/site;15TRAIN references/27sites. Same-parent three held sites
and nine held references/18sites remain development panels. Checkpoints
0/4,104/8,208 all receive complete correct/wrong-query evaluation; disabled
adapter is the immutable same-candidate-input native continuation baseline.

Workers are allocated only HIP0/1 with physical PCI verification (management
GCD2/3). No additional selector is set. Controller requires preflight success,
has a6h/run limit, retains failures without replacement, then runs independent
coordinate scoring and serial checkpoint replay/cached folding timing.

No trained quality, correspondence, transfer or acceleration result exists in
this snapshot. Endpoints, not selected intermediate checkpoints, are primary.
This is a cached-candidate-input folding study, **not strict WT-only inference**;
candidate ESM/input preparation cost is excluded and must not be silently treated
as zero in a future full-pipeline claim.

## Pre-outcome implementation history

v1 stopped at import before model loading: a fixed-derangement helper was omitted
from the frozen overlay. v1b stopped before the first native recycle: an empty
constraint encoding returns None, matching the original implementation's guarded
addition. Both failures remain archived. The missing dependency and None guard
were corrected; a focused regression test was added. v1c was frozen but never
executed; startup review added the update-budget field required by the existing
scheduler and old baseline-file hash verification. v1d is the executed revision.
No training outcome, threshold, seed or exposure budget was changed.

GitNexus all/staged checks returned complete symbol/process lists, without
partial/truncated results. Staged aggregate risk was CRITICAL (37symbols,
17flows across the six new files); shared training/continuation/decode paths
were reviewed and covered by the above integration gate. No existing native
Mini, prefix helper, editor runtime or earlier experiment was edited.
