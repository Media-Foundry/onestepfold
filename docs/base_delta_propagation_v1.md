# Base C4 delta propagation audit v1

Locked 2026-10-06 before observations. Model-only scope requested by user.
No training, custom kernels, ESM inference, MSA search, decoder sampling,
confidence, output repair, or end-to-end pipeline speedup claim.

Model: official protenix_base_default_v0.5.0, FP32, native torch operators,
four complete recycles, no templates or MC dropout. This is a diagnostic C4
configuration, not Base's default C10/200-step quality protocol. Inputs are
prebuilt query-only (one-row dummy MSA) native features, candidate-specific
chemistry. Internal MSA modules remain active. No claim about rich-MSA workloads.

Panel fixed before measurement: 5OI7 A50 (L88), 2V66 T75 (L111), 4LR3 T4 (L164).
WT plus all19 standard substitutions per site:60 inputs. Existing development
and stress examples, not independent confirmation. No new structures/downloads.

Each input: two uninstrumented C4 calls and one observed C4 call, all with
identical starting execution RNG. All three final s_inputs/s/z and final RNG
must match bitwise. Each WT also repeats all observation points, and runs one
separate lightweight CUDA-event profiling call. One excluded initial warmup.
Total187 C4 /748 recycle updates /zero S1 /zero optimizer updates.

Observe input embedding, initialization projections/relative and bond outputs,
MSA input/output, main blocks1/2/4/8/last in cycles1/4; first MSA/main block
TriMul normalization, actual gated A/B operands, TriMul outputs, triangle
attention outputs and transition outputs in cycle1. End-attention observations
use its native transposed residue axes. Zero initial recycle contributions and
the additive initialization formula are separately checked in analysis.

Statistics: whole-tensor bitwise equality (including signed zero), numeric delta
support, unchanged whole tokens/pairs/rows/columns/16x16 tiles, delta RMS/max,
support outside mutation row/column. FP64 SVD on eight predetermined evenly
spaced channels: singular spectrum, R90/R95/R99 and energy at R2/8/16/32.
These are channel-sampled diagnostics, not all-channel rank guarantees.
Sampled tensors are archived for independent rank verification; whole tensor
hashes and equality summaries retained. Rank analysis is offline, excluded from
model timers; oracle SVD is not a compressed execution method.

Model timing starts with prepared device inputs and includes input embedding
and native trunk; excludes all input construction/transfers, rank analysis,
loading and snapshot I/O. Two steady repeats are descriptive only. Separate
CUDA-event ranges include nested operators: do not add parents and children.
No batching comparison, HBM traffic or occupancy claim.

Run one worker HIP0 after PCI/occupancy guard, bounded45minutes. All model/code
and input hashes frozen. Stop on replay/nonfinite/inventory integrity failures.
Inspect where usable structure is lost; only if real operator inputs support
cheap corrections propose a separately locked prototype. No automatic kernel
implementation or sparse/low-rank approximation promotion.
