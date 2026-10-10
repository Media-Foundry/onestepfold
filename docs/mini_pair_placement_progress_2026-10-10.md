# Mini early/late pair adaptation: native gate and launch record

This is an engineering progress record, not a quality result. The earlier
candidate fits, teacher hints, linear probes, full-gradient optimizer comparisons
and reference-anchor trial remain closed. Their negative transfer conclusions
are unchanged.

The new comparison moves two trainable native pair blocks from positions14/15
to positions0/1 and propagates the early correction through frozen blocks2..15.
Both placements have1,315,332 trainable parameters, identical node initialization
per seed, the same TRAIN objective, and frozen candidate final inputs/single.
The full protocol is [mini_pair_placement_v1.md](mini_pair_placement_v1.md).

## Completed initialization gate

All912 archived warm candidate paths and24 WT references were replayed, using
their actual saved recycle RNG. The candidate pre-block0 state and existing
block13 boundary were checked against the original full warm result. Both
placements and both seeds reproduced the candidate final pair exactly:3,648
candidate identity checks. The two sites per reference also passed192 reference
branch/no-edit checks. Native weights were unchanged.

This used936 native recycle executions, no target C4 teacher generation,
no ESM/MSA preparation, and no S1 calls. The cached boundary tensors and metadata
occupy9,474,306,071 bytes. They are diagnostic/training caches, not a memory or
inference acceleration result.

Native gate lock: `fae3c951ef3cb858d2b824ce65aa092e64a246d3741dff557e29d0df6a11c178`.
Boundary manifest: `26fcd6da0ff46b21aabd7f2dde6006066367c8264f34ac58f0cbea36ee8e9e3c`.
Frozen suffix: `25647ea2df4f277fd3d4fed393988a8f92afeb14ef93a91a8a5ac21d9c7ca569`.

The first16 CPU tests covered initialization, frozen-weight ownership, input
derivatives, FP64 finite differences, joint versus streamed reference backward,
candidate isolation and reconstruction. The complete launch suite then passed
37 tests in56.00 seconds, including the established distributed reduction tests.

## Preserved startup failure and current work

Training launchv1 stopped at pytest before any native gradient or fitting:
the source package omitted existing `test_site_parallel.py`. The failed directory,
lock and log are retained. Launchv2 only adds that unchanged test. It does not
alter model code, numerical criteria, labels, seeds, optimizer or budget.

Training lockv2: `e42afe9a85392527056b93afa6efa14f84e6129b0572fda98549670f238cbc6b`.
Controller1057181 owns the finite job group. The early path's two-update
serial/six-rank comparison passed: gradients, parameters and complete AdamW
state are bytewise equal. An independent CPU reload also passed. This disposable
gate used2,052 candidate forwards/backwards and108 reference forwards/backwards;
its updates do not count toward the scientific fits.

The four fixed128-update fits started at Unix1791624106.835674, with a six-hour
deadline. Order: late272001, early272001, late272003, early272003. All nodes
0/32/128 are decoded;128 remains primary. The first run was loading at the last
observation; there is no learned-quality result in this record. Independent
checkpoint verification is queued under controller1058272, waiting for this
original comparison to finish; it does not restart failed training.

Separate native checkpoint replay, paired quality analysis and complete cost
analysis remain required. No inference speed, learned-response improvement,
transfer success or model promotion is claimed by this record.

The early graph first needs the candidate's unadapted final single and then
replays the pair stack with an edit. Frozen blocks still execute and transmit
input gradients; they are not free. This placement test does not inherit the
earlier training or cached-folding speed multipliers.

Evidence: [preflight bundle](../reports/mini_pair_placement_2026-10-10/preflight).
The transferred archive's SHA256 is
`2068dc0d904c5be18376f11e0f4f9cdb22362059ea155b4b71d29194e435f2c1`;
local metadata checks confirm the complete native gate and record counts.

Accepted numerical gate evidence: [parallel gate](../reports/mini_pair_placement_2026-10-10/parallel_gate).
Archive SHA256: `6cfb4bafa3ce006f73b5f3decb28ea817ea4fa221bf5d0caaf7e17214b99f2a0`.
Its two-step timings are gate execution records, not a balanced throughput benchmark.
