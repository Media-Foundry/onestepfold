# Native C4 execution/dependency profile v1 — 2026-10-06

After c0e71d9e, keep original public Mini FP32 C4/S1, live ESM2-3B and all hard
candidate computations. No model/precision/kernel/cache/batching optimization in
this batch. No more prefix variants, student training or new data. This is a
measurement and dependency audit, not a speedup experiment.

Panel fixed from native_budget_v1_20261005: nine parents (eight reused DEV plus
separate2V66). For each, its WT and the first non-WT sequence in archived
native_sequences order:18 hard inputs. Operator/CPU traces only on the mutant
from parents0,13,28,8 (length88,145,164,111stress). No outcome-based sampling.
Four original noises230201/230211/310003/310019. Every generated coordinate must
match the old C4 archive bitwise, including instrumented runs; otherwise stop.

One worker avoids contention between this study's own workers. Other users/tasks
may still contend for host resources. Model load measured separately. First
invocation recorded explicitly, then every input gets one excluded warmup and
three complete unprofiled wall-time repeats. End-to-end repeats synchronize only
at workload boundaries; per-stage entries there are host elapsed times, not GPU
attributions. One additional synchronized-stage run per input provides stage
breakdown, distinctly labeled. Parent GT/mask/inventory lookup occurs before
per-sequence work and has a separately recorded setup cost.

Each complete workload rebuilds features/native inventory, transfers tensors,
prepares relative/atom pairs, runs target ESM, all four native recycle iterations,
four S1 calls and host transfers, creates geometry labels, computes task/geometry,
and writes NPZ coordinates. No confidence/CIF service; archive audit and metadata
serialization are outside screening wall-time. All repeated passes retain same
arithmetic and native noise construction. Count model/trunk/S1 calls.

On four fixed mutants, add one torch.profiler pass (CPU and GPU activity when
supported) and one cProfile pass. Export traces/operator aggregates and CPU call
records; do not quote profiled duration as deployment latency. If GPU activity is
unavailable or produces no device events, explicitly report missing GPU attribution
and retain CPU evidence; never relabel CPU launch time as GPU execution time.

Dependency inventory is observational plus source based: fingerprint feature leaves
and full conditioning outside measured repeats, compare WT/mutant identity/value,
record atom counts/layout. Equality on18 inputs alone does not authorize reuse.
The source dependency table must explain the complete cache key/invalidation
scope. In an isolated diagnostic, recompute diffusion pair/atom caches four times
on each fixed candidate conditioning, compare exact values, RNG and timing; do
not feed reused caches to S1 in this batch. Distinguish within-candidate/four-noise
reuse from unsafe cross-candidate reuse. No target ESM/pair/atom state presumed
constant merely because one residue changes.

Outputs: steady workload distributions, first-use and instrumentation overhead,
stage costs, top CPU/operator costs, transfer/allocation evidence, actual peak
memory, exact replay audit, dependency/invalidation table. No batched speed claim,
no independent biology/accuracy conclusion. Single bounded job timeout1800s;
failure stops, no silent retries or optimization follow-up.
