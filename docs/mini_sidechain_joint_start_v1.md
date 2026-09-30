# Saved repulsive-sidechain initialization: bounded joint endpoint comparison

Frozen before execution, following1ab2fb55's local-screen pass. Seven supported
existing development proteins × C4/S1 seeds12345/54321. Eight-source denominator
retains3CR6 (unsupported native covalent topology), four comparison slots.
No new proteins, predictions, GT fitting, local fits, training, independent32/Y38
access, random restart, loss/threshold change, symmetry remapping or budget search.

Control: reuse14 audited whole-CCD-ideal zero-angle joint endpoints from
`c4_ideal_reference_v1_20260930/cases/{2*i+1:02d}`, arm`ideal_ref`.
Candidate: load full saved angle vectors from
`sidechain_repulsion_v1_20260930/cases/{i:02d}/values.pt` into the SAME originalraw
PoseVariables chart. Only legally allowed sidechain angles may be nonzero initially;
per-residue pose and all other angles start zero. Do not rebuild around fitted
coordinates, shift raw anchors or subtract fitted values from regularization.

Both arms retain exactly the same whole-ideal output templates, calibrated
connection objective, raw cis/trans branches, full allowed nonbonded pair list,
mean and top16 repulsion, parameter regularization, RMS budgets and final-iterate
selection. Same three L-BFGS stages rho1/10/100,60 iterations each;two CPU FP64
workers,one thread each,900s per slot.14 new joint solves only. Separately report
archived local-fit cost and actual new joint cost; this is not equal-total-compute.

Preflight all14 saved starts: original raw/GT/inventory/reference equality, chart
buffer hash equal to zero control, saved-angle replay error<1e-8Å. The local fitter
preserved fixed atoms bitwise via a mask; the full pose replay can incur roundoff,
so also record actual replay error rather than silently redefining the coordinates.
Independently replay initial/final poses and recompute original scoring, raw RMS,
checked CA/ILE/THR chirality, connection residuals, branches and objectives. Reused
controls must retain coordinate and value hashes; paired chart/objective hashes
must match. Shadow-audit archived whole-ideal and older fitted-start experiments.

Screen (development only): complete14 pairs/7 proteins, strictly positive paired
protein-mean AA AND CA lDDT differences, no decrease in number simultaneously
zero-severe, strict checked chirality and original raw RMS budgets. Preserve old
absolute/connection/full joint gates separately; do not relabel this screen as
chemical or deployment acceptance. Report each protein/noise, not just aggregate.
A failure closes this initialization variant without increasing iterations or
changing the screen. A pass supports a bounded follow-up decision, not restored
independent-set reliability or differentiability through the detached solver.
