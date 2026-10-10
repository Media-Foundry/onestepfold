# Mini candidate-first trajectory transport: interface and baseline audit

Authorized as the next experiment after the current early/late placement batch,
2026-10-10. This first phase performs no fitting, model selection, scaling search,
new ESM/MSA preparation or input embedding. It does not change the running batch.

## Question and exact task

Write W_r and M_r for the WT and true candidate's carried single/pair after
recycle r. Both components are token states at actual recycle boundaries.

    P3 = W3 + (M1 - W1)
    E3 = M3 - P3 = (M3 - W3) - (M1 - W1)

The first identity is the prediction. The second defines a future supervised
correction target; M3 is a label, never an inference input. The chosen FP32
parenthesization recovers W3 exactly when M1=W1. It is algebraically equivalent
to M1+(W3-W1), but floating-point cancellation differs and must not be concealed.

This tests whether candidate response after cycle1 can be transported along the
WT trajectory to cycle3. It does not assume that response is small, sparse,
low-rank or constant across recycle depth. The last native candidate update
recomputes single as well as pair; the previous fixed-final-single oracle is not
an oracle for this new interface.

## Fixed first-phase paths

1. Native candidate C4, four candidate updates: archived quality reference.
2. Cold candidate C2, two candidate updates: equal native-candidate-work control.
3. Candidate M1, transport P3, one final native candidate update: two candidate
   updates at inference, plus amortized WT work and arithmetic/cache overhead.

The later learned path is P3+G(candidate inputs,M1,W1,W3,hard edit), followed by
the same last native update. Its s/z target is E3, not the prior post-recycle
pair residual. No learning budget or architecture is launched by this audit.
It requires a separate training lock after the new boundary/RNG and cost checks.
Do not switch directly to M4 prediction or delete the last update from an M3 model.

## Inputs, cohort and RNG

Keep Mini v0.5.0 FP32, the existing n15 plan:24parents,48sites,912mutants; TRAIN
15parents/27sites/513mutants;3same-parent development sites;9new-parent development
proteins/18sites. These are reused development data, not independent confirmation.
Keep both decoder noises230201/230211 and all19non-WT choices at each site.
Retain true candidate s_inputs, prepared MSA features, atom inventory and chemical
graph. No target terminal state enters the prediction path. Native MSAModule
execution remains inside each counted recycle; upstream preparation is excluded.

For each parent use a fixed full RNG seed281001+parent, shared by its WT and all
candidates. Capture every recycle boundary and all Python/NumPy/CPU/HIP RNGs.
Audit candidate cycle3 RNG against WT cycle3 RNG for the fixed query-MSA protocol.
The prediction must use WT cycle3 RNG, not a target-derived RNG. Fail closed if
they disagree; do not quietly compute missing candidate rounds to obtain RNG.
This equality is a protocol-dependent check, not a guarantee for arbitrary MSAs.

Require full C4 states and both S1 coordinate outputs to equal the existing
archive; verify actual target3+1 state and final RNG replay for every candidate.
Verify WT1+transport+last reproduces WT4 and both coordinates. For each parent,
repeat the first candidate after the other18 candidates and their decodes;
require identical transferred state, native final state and both coordinates.
No-edit, reference immutability and an interleaved stochastic toy replay are also
checked. Any failed gate is preserved and stops the audit.

## Metrics and storage

At cycle3 compare predicted P3-W3 with M3-W3, separately for s/z, using full,
common and AA-centered FP64 moments. Repeat at final cycle4 with reference W4.
Report pre/post absolute error RMS and per-candidate final/input error-norm ratios
for each state, flagging tiny denominators. Different-stage NMSE denominators are
not comparable as a contraction factor; no claim of universal correction follows.

Decode every path, regardless of latent NMSE. Keep the established equal-parent
rank and response metrics, old-noise selection/new-C4-noise raw regret, Exact's
own cross-noise regret, individual high-cost choices, local displacement tails,
geometry transitions in both directions, clash and chirality severity. Compare
transport with cold C2 directly. C4 is a model reference, not experimental truth.

Persist candidate M1 and target M3 in physically separate input/label files,
with hashes and role labels. Reference W1/W3/RNG is shared per parent. Target3
was discarded in the earlier archive and must be regenerated; all native calls,
S1 calls, bytes and wall time are charged to this preparation/audit. No speed
claim follows from recycle counts or concurrent audit time. A later isolated
model-only inference benchmark must include WT construction and both candidate
updates; it must not time the cached-label audit as deployment.
The audit ledger expects5688native recycle calls and5568S1 calls in total,
including full teacher reconstruction, split and candidate-isolation checks.

## Execution and interpretation

Wait until the original four fits, scoring, ledger and independent saved-node
verification finish successfully. Then two independent parent shards run on the
now-authorized HIP6/7. Do not interrupt, restart, extend or alter the old queue.
Use a finite12-hour waiting window and2-hour audit/scoring cap, preserving failure.
Run frozen source snapshots and hash all locks and existing source contracts.

Better than cold C2 shows value in this specific trajectory reuse. Worse than
cold C2 does not mathematically rule out learning E3, but removes the claim that
the unlearned WT progression already helps. A future learned version must beat
this direct transport baseline on unseen proteins, not merely beat a wrong-AA
control or improve TRAIN fit. Structure, selection risk, geometry and actual cost
remain separate acceptance dimensions. No post-hoc coefficients or site removal.
