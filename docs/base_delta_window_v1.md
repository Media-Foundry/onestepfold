# Base C4 structured-delta window / cost audit v1

Locked2026-10-06, before new outputs. User authorizes follow-up after60d6a307.
Model-only, no external MSA/ESM preparation or end-to-end pipeline claims.
Same Base_default_v0.5.0 FP32/native C4/query-only MSA as prior audit; internal
MSA remains active. Not Base's default quality protocol. No decoder, optimizer,
kernel, rank-truncated execution or candidate selection experiment.

Twelve inputs, all reused byte-identical from prior frozen packets:
5OI7 A50,2V66 T75,4LR3 T4; WT and C/V/W at each. Fixed chemical/size diversity,
including known T4W stress case; no selection by favorable spectral outcome.
This remains three development contexts, not independent validation.

Capture block inputs/outputs and actual gated TriMul outgoing/incoming A/B:
cycle1 B8/12/16/24/32/40/48, cycles2/3/4 B1. Also MSA input/output in cycles2/3/4.
66 full FP32 tensors per input. Preserve every128 channel in offline spectra,
not only the previous eight-channel sample. R90/R95/R99, energyR2/4/8/16/24/32/48/64,
outside-row/column energy, strict equality/support. Report channel and candidate
distributions, maxima/minima and parent strata; energy ranks are not exact ranks
or decoder fidelity. Full tensors remain remote for independent verification.

Three plain timed C4 calls/input, one observed call, two event-profiled calls;
each WT repeats all observations; one excluded warmup.76C4/304recycle,zeroS1.
Every non-warmup final s_inputs/s/z must match previous archive whole-byte hashes
and matching execution RNG. WT observation repeats must match whole-byte hashes.
Timers start with prepared device inputs; exclude loading, transfer, offline
SVD, file I/O. All inputs and source/weight hashes verified before and after.

Timing: separate whole TriMul and internal contraction CUDA events at every
main block in every cycle. These levels overlap; never add parent+child.
Within each level, calls are disjoint. Compare event-profiled wall to plain
wall to quantify perturbation. Two profile repetitions are descriptive.
Report prefix costs through fixed depths and per-cycle costs, with no assumption
that sparsely sampled spectral points certify the intervening blocks.

No automatic new rank thresholds or quality gates. A low-energy-rank interval
must also cover material native cost and admit cheap factor generation before
motivating a prototype. This audit does not generate factors online, measure
compression/materialization crossover, implement dense fallback or establish
approximate output quality. Do not count offline SVD as an acceleration.

One physically checked HIP0 worker, bounded45minutes; independent CPU spectral
verification after completion. Original data, model weights and prior results
unchanged. Stop on any parity/integrity/nonfinite failure, preserve failed run.
