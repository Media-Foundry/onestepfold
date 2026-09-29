# Local projection fitting: bounded development diagnostic (draft)

2026-09-30. The independent32 experiment is closed. Its continuation screen failed.
This document specifies a possible next development diagnostic; **no protein batch
has been launched under this draft**. A user preference question about this direction
is pending. Code and synthetic tests are prepared for review.

## Question and scope

The saved initialization already accounts for most of the observed all-atom lDDT
loss. The current constructor extracts a pose from N/CA/C and selected torsion
probes; it does not minimize whole-residue coordinate error. First ask whether the
same chemical manifold admits a noticeably closer fit to raw coordinates. A closer
fit is neither a guarantee of better experimental accuracy nor chemical/chain
validity. This is a test of initialization fitting, not a replacement design oracle.

Use the six old development inputs from `anchored_tail_v1_20260929`: the same parent,
controlled S1/native S5, noises211/200003/200009. They are regression cases, not six
independent proteins. Load the original raw coordinates, not the repaired output.
Do not access independent32, its near-sequence reservations, new temporal structures,
or any candidate mutation data. No new Mini/ESM forward, model training, contact
optimization, tail-weight tuning, or rerun of the closed validation set.

## Prepared implementation

`src/fastglycan/local_projection_fit.py` reuses unmodified `PoseVariables`. The
chemical reference, inventories, allowed bond bridges, local bond lengths/angles,
ring geometry and checked handedness are unchanged. It allows independent proper
residue rotations/translations and the existing internal bond rotations.

Minimize the single objective

\[
E=\frac{1}{N_{\rm atom}}\sum_a\|X_a(\theta)-X_{a,\rm raw}\|^2.
\]

All native heavy atoms have equal weight; experimental coordinates and masks do
not enter this fit. The optimization is separable in residues mathematically, but
the numerical L-BFGS solve acts on the combined parameter vector. A lower overall
error does not imply lower error at every residue.

One existing-constructor initialization; one L-BFGS solve, lr1, at most60 iterations,
max_eval90, history20, strong-Wolfe, tolerance_grad1e-8/tolerance_change1e-12.
Proposed diagnostic execution: FP64 CPU on DiamondHill, one thread, 900s external
ceiling per case. This is a small numerical fitting reference, not a proposed FP64
deployment mode. Record actual closure count, time and final gradient norm.
Final iterate only: no best iterate, restart, fallback, or post-result budget change.
Failure/nonfinite output stays a failure; absence of improvement does not establish
that the chemical manifold has no better fit.

The function intentionally detaches raw and returns detached coordinates. Its
optimization gradients are with respect to residue variables. It does **not**
compute d(output)/d(raw), impose chain connections or remove nonbonded clashes.
Do not join its forward output to the old raw backward and call that exact.

## Checks before any development batch

Three focused CPU synthetic tests pass:

1. A known representable chemical input stays fixed; input tensor is unchanged and
   no through-solver gradient is exposed.
2. Distortion of one pose anchor permits a closer all-atom fit, with unchanged
   local bond/angle invariants and both checked THR stereocentres; proper rigid
   transformation of the problem yields the corresponding transformed result.
3. Nonfinite input, degenerate frames and invalid budgets fail explicitly.

These synthetic tests are implementation evidence only. They say nothing about
the independent32 quality loss being recovered.

## What a subsequently authorized batch would report

Lock code/input/reference hashes before reading new fit outputs; preserve old files.
For every old development case report raw/old initialization/new fit, full atom and
backbone/side-chain/residue errors vs raw, atom movement extremes, local chemical
invariants, checked chirality, chain residuals and collisions under unchanged rules.
Separate fitting error from chemical acceptance. No GT accuracy claim if a verified
experimental mapping is absent. No generalization claim from this single parent.

If raw-fit improvement is negligible, inspect the residual and stopping evidence
before expanding representation. If substantial, the next unresolved question is
whether fitting preserves experimental accuracy on a separately locked development
source. That requires its own dataset contract and joint-geometry comparison;
do not automatically run it on independent32 or assume this standalone fit fixes
the already measured chain and collision failures.

Stop after the proposed six-case diagnosis. Do not turn it into an unbounded search
for weights or a sequence-design trial. Any integration with joint repair or a
short differentiable map remains a separate method decision.
