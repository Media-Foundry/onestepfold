# c4_s1 failure persistence and deterministic-oracle checks

Status: protocol draft following user discussion; no new inference, optimization,
or distillation submitted. Supersedes neither frozen Stage0 artifacts nor their
completed confirmation conclusions. Active research direction is pretrained Mini,
C4 retained, S1 deployment, K1. Exact deployment checkpoint is a separate choice:
old evidence and the matched extension concern mini_esm, not mini_default.

## Questions and causal limits

Distributional and paired tails answer different questions. Discovery-seed gains
and losses greater than0.05 against c4_s5 are TM50/25, AA7/14; against c4_s2 they
are TM44/26, AA4/16. This establishes target-wise score crossover, not distinct
physical basins or a demonstrated topological change. Inspect coordinates, domain
orientation, contacts and local versus global errors before naming a mechanism.
A TM-style drop can involve domain placement/alignment, not necessarily a new fold.
A good marginal tail can mask harmful redistribution and does not prove equal
failure rates at every absolute quality threshold.

## A: unchanged representative panel

Reuse exactly the128 target IDs and seeds103/107/109/113 in
reports/stage0_confirmation_2026-09-19/repeat_lock.json.
Manifest SHA d80eb1beb18d83a0110294c0f707193fb320a7e4490c74a0a36a855020d18628.
Do not replace or append targets. Discovery overlap:4 targets with either-metric
c4_s1-c4_s5 loss>.05,3 against c4_s2. These counts do not select the panel.

The completed repeat only covered c4_s5/c4_s2/c2_s2; adding c4_s1 requires a NEW
extension lock, not overwriting that protocol or claiming old c4_s1 confirmation.
Prefer512 new c4_s1 predictions with already accepted1024 reference predictions
from c4_s5/c4_s2 ONLY if checkpoint, features, runtime, RNG reset, dropout and
numeric policy can be matched and reference sentinel replays agree. Otherwise
run all three as a complete matched block and disclose protocol differences.
No best-of-seed. No new frozen-test access. Preselected does not imply an entirely
unseen test set or external-population unbiasedness; sampling weights would be
needed for prevalence claims beyond this panel/design.

Keep original MC dropout policy for this historical extension: seed103 off;
107/109/113 on in the accepted execution. This measures combined inference
randomness, not isolated diffusion variance.

## B: separate failure diagnostic panel

Before new runs, lock group IDs selected by a reproducible rule using discovery
scores, plus length-matched ordinary controls; use group IDs rather than PDB IDs.
Include key failure cases such as9QR4/8ZBL and any selected gain cases so that
both sides of the crossover can be examined. Diagnostic membership and selection
criteria must be reported. B is conditional on selected discovery failures; never
pool it into A to estimate prevalence. Reuse overlapping predictions without
counting the same target twice. Exact B membership remains to be locked before
execution; the user-listed PDB examples are not automatically an executable manifest.

## Persistence and uncertainty

For each target/reference/metric retain all four scores/deltas, target mean,
variance/range and k=sum(delta<-.05). Report k0..4 counts;3/4 or4/4 is an
operational persistent-failure label, not proof of a seed-invariant mechanism.
Also report severe threshold-.10, absolute quality and joint-failure unions.
0/4 alone is not neutral: distinguish stable gain and a predeclared neutral band.
Do not automatically ascribe non-recurrence to sampling only: discovery-tail
selection creates regression to the mean, and the native repeat varies dropout.

Primary CI: target-cluster bootstrap retaining each target's full seed/config block,
conditional on the four chosen seeds. For generalization across seeds, report a
separate crossed target/seed resampling sensitivity analysis, preserving common
seed columns across all targets and both references. Independent seed resampling
inside each target can erase shared seed/dropout effects in this protocol. Four
seeds give weak estimates of the seed distribution. Do not treat128x4 as512
independent proteins. With1-3% prevalence the128 panel contains only a handful
of expected failures; P01 and low failure-rate guarantees have limited precision.

## Controlled-noise mechanistic block

Use fixed checkpoint and immutable conditioning tensors for C4, no dropout.
For each target/replica explicitly store identical initial-coordinate noise and
rigid-transform inputs/hashes, disable churn(gamma0=0), eta1, and lock every
remaining RNG source. Same seed labels alone do not establish these equalities.
Changing S changes schedule and evaluation points; S1 output is not S5's first
Euler iterate. At sigma_next0 and eta1, Euler returns the denoiser output
algebraically. Full-step path truncation is a distinct question.

The native Mini default is already gamma0=0/eta1. Lambda affects a zero churn
term and cannot explain new quality under this configuration. Do not call the
controlled block a churn-off improvement. Native-versus-controlled differences
also include dropout/conditioning/augmentation; if attribution matters, first
freeze/replay the native conditioning/noise and only then vary schedules. Verify
forward equivalence of the new sampler before interpreting any new score.

Evaluate independent predeclared noise replicas without best-of-K selection.
Record first actual denoiser input/output hashes and all sigma values(NFE1/2/5),
then identify which errors recur with common inputs. Recurrence under fixed
inputs supports an integration-schedule-dependent problem, but does not prove
one-step network capacity is insufficient.

## Fixed-noise backward and optimization gate

Freeze all weights while preserving the complete input graph through all4 cycles.
Upstream final-cycle-only autograd and local detached_tree must be replaced in
an isolated implementation with forward replay checks. Discrete tokenization,
MSA/query features and residue-specific atomic graphs require an explicit soft-q
contract; q in one-hot fields with stale ESM/atom features is only a partial
surrogate derivative. First finite-difference fixed-inventory diagnostics must
not be presented as complete arbitrary amino-acid design.

Define q=softmax(logits/temperature), fixed noise and augmentations, then measure
repeatability, finite gradients, directional derivatives in logits, perturbation
sensitivity and backward cost. A frozen random realization is deterministic but
can still be rugged or exploitable. Small stable decrease tests and longer
optimization trajectories serve different purposes; no requirement of strict
monotonicity for every ordinary optimizer step. Monitor structure/geometry,
not just the optimized contact loss. Rebuild inputs after hardening the sequence,
evaluate unoptimized fixed-noise replicas and an independent multi-step reference.
Single monomer reconstruction is not binder-interface success.

K fixed-noise gradient replicas multiply NFE/cost; label K explicitly. They are
an optional later robustness control, not a free part of strict K1 deployment.

## Decision rule

No diffusion training now. Persistent poor quality is a reason to investigate
training, not the only admissible trigger: unusable q derivatives or repeated
hardening/independent-noise failures can also invalidate the design oracle.
Conversely, stable q gradients do not excuse degraded hard-sequence quality or
structural invalidity. GateA andGateB need numerical thresholds locked before
execution; the current discussion has not supplied them. Report uncertainty
rather than choose favorable thresholds after seeing new results.
