# Old-six local fitting execution v1

2026-09-30. Bounded continuation of the standing mainline task, using the recommended
direction in the optional preference question; no new user answer is assumed.
The previous draft and independent32 rejection remain unchanged. This execution
implements the draft's single-parent, six-input CPU diagnosis, not a new validation
panel or a change to deployed model behavior.

Only the six source cases, reference and topology in the frozen
`anchored_tail_v1_20260929/lock.json` may be used. Check their hashes and exact
arm/seed list. Capture a new immutable runtime lock before solving. The copied
ArticulatedOutput/PoseVariables and chemical reference code must match the old
lock. Inputs are original raw predictions, never previous repaired outputs.

Run `fit_local_projection` as prepared in e36b99c1: one initialization, one FP64 CPU
L-BFGS solve, max_iter60/max_eval90, history20, lr1, strong-Wolfe,
tolerance_grad1e-8/tolerance_change1e-12. One CPU thread per worker, at most two
workers, 900s external ceiling per case. All six stay in the denominator, including
runtime failures; no retries or altered settings. No GPU inference or training.

Report final iterate only, full/native-atom error vs raw, backbone and side-chain
error, per-residue changes, local bond/angle invariants, all checked handedness,
the original chain residuals, clashes and displacement constraints. Replay saved
parameters and compare the old initialization within1e-8 Å (CPU/GPU floating-point
ordering need not be bitwise identical). Fitting success is not joint geometry
acceptance or experimental accuracy. Record actual iterations, closures, gradient
norm and time; max_iter reached is not convergence.

No contact objective, geometry weight tuning, extra optimizer stages, best-iterate
selection, or composition with the joint solver. No experimental GT is used in
this old-six diagnostic. A future GT-based development check requires its own
source/mask contract and must exclude the reserved32 and their near sequences.

Stop after these six. Interpret a lower raw-coordinate error only as evidence
that the old direct extraction was not the best fit found on its own chemical
manifold; it does not certify a globally nearest projection or restored lDDT.
