# Position pilot: probability/logit chain audit engineering retry

2026-09-30, AFTER initial four proposal workers terminated and BEFORE any hard
candidate evaluation. Original root position_utility_v1_20260930 is immutable.
Two workers(2FIP,1QSM) failed the hand-written FP32 softmax chain allclose; two
workers(1BFT,5CPG) passed. All gp/gq were finite. No hard candidate was evaluated.
Failure is NOT yet a full-path backward diagnosis.

Retry the same four parents/config/weights/seeds/objective in separate root
position_utility_chain_v1_20260930, preserving original failure and old formula
pass/fail. Save q,p,gp,gq before enforcing the audit. Reconstruct p from identical
q and require exact p replay; feed the saved gp through ONLY a fresh softmax VJP,
requiring exact equality to end-to-end gq. This tests probability/logit variable
routing without near-hard division. Record manual FP32 and FP64 algebra errors.
It is not independent differentiation of ESM/Pairformer/diffusion, not a change
to proposal scoring, and not end-to-end numerical certification. No old tolerance
is described as having passed if it did not.

Where previous workers saved complete gradients, require q,p,gp,gq,coordinates and
candidate lists to replay exactly before hard evaluation is released. Do not
change parents or select among reruns. Any failed local VJP blocks all hard
inference. Chemistry/quality acceptance and the original scientific protocol
are unchanged. The separate penetration preflight discrepancy(<1e-7Å) reflects
FP32 radii in legacy GeometryTopology versus higher-precision scoring; counts
were equal, no scientific acceptance threshold changed.
