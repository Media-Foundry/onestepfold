# Native Mini site-parallel acceptance check

This is an engineering check of the existing ordered CPU/Gloo prototype, not
a new model-quality experiment. The reference-anchor trial ending at commit
3a4b1d58 stays closed. Do not resume its checkpoints or change its results.

Reuse its frozen code, source/data manifests, TRAIN-only scales, 27 TRAIN sites,
513 candidates, initial Mini suffix and seed272001. Same FP32 within-site
candidate/reference backward and canonical CPU FP64 across-site reduction.
Candidate native input/single stay fixed; target pair remains a loss label.
No C4, recycle, input embedding, diffusion, ESM/MSA preparation or held labels
may be computed. Parameters used here are disposable verification replicas.

Run six torchrun workers, max-restarts0, Gloo on loopback. The parent uses only
HIP_VISIBLE_DEVICES=0,1,2,3,4,5; each new worker narrows that variable to its own
device before importing torch. No CUDA/ROCR visibility override. Actual PCI
mapping must be recorded. Initial inspection maps HIP0–5 to PCI32,35,11,14,AE,B3;
the busy SMI card5 is PCI93/HIP7 and is outside this task. Recheck availability
at launch; never terminate unrelated work to obtain a device.

Cache construction and model loading are timed separately. Rank0 retains all
27 sites for the serial reference; other ranks retain their round-robin shard.
The distributed partition is fixed by canonical index modulo6, giving
5/5/5/4/4/4 sites. No timing-driven repartition. The optimizer runs only on root;
its updated parameters are broadcast and hashed on every worker.

Warm each execution path once with a gradient pass and no optimizer update.
Then run two fresh-initialization comparisons, three AdamW updates per method:
serial→parallel and parallel→serial. Same lr1e-4, weight_decay1e-4, eps1e-8,
betas(.9,.999), clip1. There are12 measured full-gradient/update executions,
plus two warmup full-gradient equivalents:7,182 candidate forward/backward
evaluations and378 reference forward/backwards globally. These are repeated
verification computations, not independent training evidence.

Compare every step's full CPU FP64 gradient, canonical site objective rows,
model state, AdamW step counters and first/second moments **bitwise** between
serial and parallel. Record max-absolute/relative gradient discrepancy on
failure, retain artifacts and stop. Do not relax this acceptance after seeing
results. The serial initial gradient must also match the preceding frozen
anchor audit within its existing relative5e-5 tolerance; initialization hash
and objective checks retain the previous contract. This historical replay
tolerance does not relax the serial/parallel bitwise requirement.

Measure synchronized complete update time, including gradient transfers,
canonical reduction, clipping, optimizer, broadcast and replica checks.
Exclude initial data/model loading, warmups, snapshot serialization and the
independent comparison, reporting their work separately. Retain all three
updates in both execution orders; report per-order ratios, aggregate time,
per-rank time and peak allocated memory. This measures training update
throughput on this cache/model, not folding inference or fewer FLOPs. Six-GPU
wall time and GPU resource use must remain distinct.

Save step snapshots and source hashes; a separate CPU process must reload all
paired snapshots and verify equality after the worker group finishes. Native
model hashes and zero forbidden-call counters must hold on every worker.
Uncaught worker failure terminates the group; no automatic retry, continuation
or checkpoint selection. Use a finite30-minute process-group cap with cleanup
limited to the newly owned group. A network/observer timeout is not a job
failure and must never cause a duplicate launch.

Acceptance requires native numerical equality and measured speed/memory.
Failure closes this implementation attempt with its evidence. Success only
qualifies the infrastructure for a separately locked future scientific run;
it does not promote the reference-anchor model or establish production restart
semantics.
