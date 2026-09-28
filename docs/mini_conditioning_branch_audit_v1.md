# Fixed conditioning branch and objective attribution

Follow-up to the 2026-09-28 native geometry/pullback audit. No policy or model change.

Before results: run control separately for s_inputs, s, z; run 8BZN with all three
blocks as the finite-perturbation-loss comparison. Keep original frozen chart,
softmax(4*onehot), noise211, C4/S1, FP32, seed731 and first three Gaussian block-RMS
directions. For control retain only the chosen block of each original direction.
Keep h=.01,.003,.001,.0003,.0001 and 5%relative+1e-6 with adjacent-step requirement.
Do not replace original failures with this exploratory decomposition.

Split old into weighted contact, Cα clash, Cα chain, and new auxiliaries into
bond, 2*peptide, clash, .2*chirality. Preserve original old/new accumulation order.
Compare analytic, linearized-coordinate FD and nonlinear-objective FD for each.
Record absolute dot products to expose cancellation. Add one gradient-aligned
new-objective direction with the first random direction's norm, separately labelled
as a high-signal diagnostic; it is not a replacement random-direction gate.
Require frozen source hashes, exact repeated coordinates, and previous loss-value
replay. No precision escalation, training, candidate search, or temporal test.

Four independent bounded jobs on DiamondHill GCD0–3, each capped at 30 minutes.
Results determine any further bounded diagnostic; do not expand the method tree.

## Replay guard finding (before branch outcomes)

All four first-attempt jobs stopped at the exact replay guard. That comparison
changed both grad mode and conditioning tensor layout: packed contiguous inputs
versus original tuple. Preserve these failures. Two bounded layout diagnostics
(control and8BZN) now separate original/packed/contiguous inputs, grad/no_grad,
and repeated no_grad. Any corrected guard must hold input layout constant,
not simply loosen the numerical tolerance. Branch FD remains pending.

## Corrected replay guard v2

Layout audit completed: packed grad/no_grad/repeated outputs are bitwise equal.
Original and packed values and strides are identical, but outputs differ by
4.65e-5A(8BZN)/5.82e-5A(control) maximum. Original-grad matches original-no_grad;
thus grad mode does not explain the difference. Allocation/storage alignment is
a candidate, not a traced kernel cause. v2 holds packed inputs fixed for both
sides of the exact guard and records offsets/pointer alignment. No tolerance
relaxation or change to FD directions/objectives. Preserve failed v1 logs.

## Bounded follow-up selected from component evidence

v2 complete: control branch derivatives sum to the prior mixed derivative.
8BZN direction1,h=.003 shows99.6% of total nonlinear-minus-linearized FD
remainder from weighted all-atom clash. Run exactly one further8BZN diagnostic
on that same direction at h=.003/.001: attribute the clash remainder per pair,
record baseline/perturbed pair distances and hinge activity. Save coordinates;
no objective changes or relaxed derivative gate.
