# Ordered site-parallel gradient prototype

The first CPU/Gloo prototype preserves the serial reference-anchor trainer's
gradient and optimizer arithmetic in a small test. It is not connected to the
ongoing locked Mini experiment. No training run was migrated or restarted, and
this result does not establish native Mini multi-GPU equivalence or speed.

## Execution contract

`src/fastglycan/site_parallel.py` partitions complete training sites across up to
six workers. Each site retains its original candidate order, normalization,
reference graph and shared reference pullback. The existing
`AnchoredFullBatchTrainer` computes every site gradient without modification.

Workers send CPU FP64 site gradients to rank zero through Gloo. Rank zero
restores the canonical global site order, sums and averages exactly as the
serial trainer, installs the gradient, clips once, and executes one optimizer
step. Only rank zero owns AdamW moments. Updated parameters are broadcast and
their hashes checked on every worker. All reference graphs must be rebuilt
after an update.

This differs from ordinary DDP averaging of already averaged worker gradients:
sites can be unevenly distributed, and changing the reduction order would
change the floating-point calculation. It also differs from the repository's
existing two-candidate structure-loss DDP runner, whose batch contract is not
the current 27-site full-gradient objective.

The prototype rejects missing or duplicate sites, invalid gradients, differing
replica parameters or site order, and gradients computed at an older parameter
version. A reported worker error is broadcast before the optimizer update.
Worker death is left to the process-group timeout; automatic retries and
checkpoint continuation are not implemented. An optimizer failure after it
has begun modifying state is terminal, without a rollback guarantee.

## Executed checks

Five tests passed in **53.32 seconds** inside an isolated copy of the frozen
runtime, with `HIP_VISIBLE_DEVICES=''` and one CPU thread per worker. The
recorded subprocess duration was 54.15 seconds. These are test durations, not
performance comparisons.

Four cases use three actual Gloo processes: two sites (one empty shard) and
five sites (uneven shards), each in FP32 and FP64. They execute three AdamW
updates. Full gradients, objective values, parameters, optimizer step counters,
and both AdamW moment tensors match the serial reference **bitwise**. They also
check that stale gradients and an intentional worker error stop every rank
without a further parameter update. A fifth test rejects incomplete site
coverage and nonfinite gradients.

The small fixture has three candidates per site and mock nonlinear pair blocks;
it exercises the same reference-anchor trainer, but it is not a native Mini
test. The evidence and source hashes are in
`reports/mini_site_parallel_2026-10-10/cpu_equivalence.json`; the unchanged test
output is `cpu_equivalence.log` in that directory.

## Cost and next acceptance gate

For the current 1,315,332-parameter model, collecting all 27 FP64 site gradients
requires **284,111,712 bytes** of gradient payload per update (about 271 MiB),
before serialization, copies and parameter broadcasts. This straightforward
prototype favors reproducibility; it does not establish an efficient collective
implementation or a sixfold speedup.

Before a future scientific run can use it, a separate fixed engineering check
must compare native Mini serial and distributed gradients, updates and saved
states on the same data, and measure complete update time and memory. A
production launcher must additionally validate immutable inputs and implement
checkpoint/restart semantics. Current locked runs keep their original source,
devices, optimizer schedule, terminal checkpoint and six-hour cap.

No model-quality conclusion follows from this infrastructure result. The live
reference-anchor experiment still needs both terminal runs, coordinate scores
and independent tensor verification.
