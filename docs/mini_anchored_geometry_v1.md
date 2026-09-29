# Anchored residue-pose geometry feasibility v1

2026-09-29, follows user proposal after c1badd49. Fixed graph, no sequence changes,
Mini weights, folding forward, contact objective, teacher-label creation or training.
This is an iterative diagnostic, NOT a differentiable one-step output oracle.

## Representation
Initialize with unchanged ArticulatedOutput using archived CCD reference. Every
residue keeps its own raw CA origin and proper N/CA/C frame. Optimize local-basis
translation (3), rotation-vector (3), and supported graph-bridge torsions (including
carbonyl rotation). Proper rotations/whole distal components preserve local reference
bond lengths, angles, rings and represented stereochemistry. No Cartesian free-atom
updates. phi/psi may change. OXT is terminal only; crosslinks/multiple chains unsupported.

## Joint objective and fixed solver budget
One objective throughout: heavy-atom squared displacement from raw (mean per atom)
+ 0.1*mean(rotation-vector norm squared) + 0.01*mean(1-cos(torsion changes))
+ rho*(connection violation + nonbonded repulsion + displacement-budget penalty).
All weights/normalizations fixed before runs. rho=1,10,100 in that order; no grid.
Each stage fresh torch LBFGS, lr=1, strong_wolfe, history_size=20, max_iter=60,
max_eval=90 (PyTorch line search can exceed nominal evaluation bound), tolerance_grad
1e-7, tolerance_change1e-10. External per-case ceiling900s, record actual closure counts
and stages. Do not select intermediate candidates by task/geometry. Final iterate only.
A solver stopping is not a feasibility proof nor a recorded convergence certificate.

Connection targets: C-N1.329 A (1.341 before PRO), cos(CA-C-N)=-.4473,
cos(C-N-CA)=-.5203 (same sourced AlphaFold constants as connected_v1).
Acceptance tolerances: length .03 A, angle cosine .04, omega phase chord .10,
carbonyl phase chord .10. Optimization uses HALF these tolerances as an interior
margin: sum of per-kind means of relu(abs(residual)/(0.5*tolerance)-1)^2.
This avoids deliberately placing finite-penalty optima on the acceptance boundary.
For omega, cis/trans is selected ONCE from raw cosine>=0 vs<0; log positions and freeze
mode during optimization. This is a prediction-derived discrete mode assumption,
not a validated experimental label. Carbonyl O is opposite next N about CA-C.
Nonbonded pairs: exact archived graph-distance>3 list, no spatial truncation.
Repulsion=sum(relu(r_i+r_j-distance-1.5)^2)/N_atoms, divided by .5^2.
Displacement penalty=relu(CA mean squared displacement-1)^2 +
relu(heavy mean squared displacement-4)^2. These are penalties, not hard guarantees.

## Inputs, checks and stopping
Same six archived parent controlled_s1/native_s5 x seeds211/200003/200009 as prior
probe. Replay inputs/chemistry hashes; use original raw coordinates, not connected or
force-field-repaired outputs. This is a regression/feasibility set, not independent data.
GPU FP64 local solver on DiamondHill; no whole folding-model precision change.
Six independent cases, max six GCD, one bounded job each. No automatic restarts/tuning.

Before submission: zero-update local reconstruction parity; proper rigid equivariance;
local bond/angle and CA/ILE/THR chirality preservation under joint pose/torsion changes;
FP64 parameter gradcheck; feasible synthetic input stationary/replayed by solver.

Acceptance jointly requires unchanged GeometryRules, raw-frame CA RMS<=1 A/heavy<=2 A,
all CA and checked ILE/THR centres correct, all connection residuals within above
new tolerances (numerical slack1e-6). No relaxation of old gates. Record every maximum
residual, named collision, displacement, rotation/torsion magnitude and derivative
finite status. Initial/final results and optimizer progress retained. No design-utility
claim or contact ranking. Independent CPU/NumPy final metric recomputation required.

If feasible, it justifies a later speed/differentiability study; it does not establish
sequence gradients through this optimizer. If not, stop this solver configuration;
report unresolved residuals, not 'no nearby solution exists'. A future output Pi(X,c)
needs its own derivative through X and chemical inputs; raw gradients cannot stand in.
