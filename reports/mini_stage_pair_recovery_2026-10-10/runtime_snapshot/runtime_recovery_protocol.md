# One operational retry after the stalled native-stage training execution

Locked2026-10-10 after the bounded prefix diagnostic completed. Original n15
Final/272003 remains live but has produced no record after1420 for about50min.
An independent clone from its checkpoint0 reproduced all4260 recorded values
(two losses and pre-clip gradient norm at each of1420updates) exactly. The next
update completed in about0.2sec. These observations justify an execution
recovery, not a claim that the original weights, GPU, proot or a specific kernel
has been proved to be the root cause. Full unobserved parameter-state equality
is not inferred from scalar equality.

Preserve the original run directory, logs, controller, checkpoint0, all1420
history records and the diagnostic1420/1421checkpoints. Terminate only the
confirmed anomalous process group715283 after verifying all other scientific
train/score jobs completed. Observe its terminal state and the original
controller's failure record before launching any retry. Do not treat an expired
observation, a missing log line alone or process intent as terminal evidence.

Exactly ONE fresh operational retry: same Final objective/272003 seed, frozen
825-file snapshot and original protocol, identical n15 training lock/data,
initial model digest, AdamW/clip/schedule,8208updates and0/4104/8208evaluations.
Run on now-freeHIP0 in a separate runtime_retry_v1 directory; do not overwrite
the original incomplete attempt or promote the partial diagnostic into a new
scientific result. No checkpoint/model selection, new seed, hyperparameter,
target, data or precision change. Original worker script is unmodified. A
stdlib faulthandler wrapper records Python stacks periodically and can receive
a nonfatal diagnostic signal; it does not change model state or RNG.

Use the original n15 lock creation time plus6hours as the absolute deadline
(slightly conservative relative to the controller's later phase_start). Retry,
scoring and independent verification must fit in the remaining interval. No
automatic second retry. Any failure and partial work remain reportable.

After successful training, use unchanged scoring and independent NumPy checkpoint
verification. Completed seven original runs remain the other scientific records.
Export a source-provider map, original failure artifacts, recovery controller and
both diagnostic protocols/results. The original controller is allowed to remain
failed; a distinct recovery completion record governs the assembled eight-run
report. This operational exception is disclosed, not silently folded into the
original execution or called a new independent seed.

Accounting if the retry finishes: scientific runs still have65664accepted
updates; add1421diagnostic updates and1420recorded discarded updates, giving
68505recorded updates overall. The original next update may have partial work
that was not logged (at most one additional optimizer step/two candidate
forwards); do not claim an exact total for this unobserved portion. Repeat of
the failed attempt's checkpoint0 evaluation adds1824S1, bringing preparation
plus all scientific/failed-attemptS1 to33744. The separate two-candidate no-update
probe and independent checkpoint re-forwards are counted separately. No
ESM/MSA preparation, new teacher labels or S1 backward is added.

Scientific quality remains unqualified until all fixed terminal results are
assembled. Runtime recovery is not evidence of improved mutation prediction.
