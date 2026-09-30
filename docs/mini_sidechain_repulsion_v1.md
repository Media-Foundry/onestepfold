# Coupled raw-sidechain preservation and variable-pair repulsion

One bounded local follow-up to581d6d47. Retain old pure-MSE failure; no changing its
screen or replacing any source. Seven supported development proteins x2 saved C4/S1
noises12345/54321,3CR6 two unsupported slots retained. No model/training/GT fitting,
ind32/Y38 access, symmetry remapping, random restart or joint-solver execution.

Same WHOLE-ideal local chart, raw target, fixed per-residue pose and N/CA/C/O/OXT,
same legal sidechain bridge rotations. Start from original zero-angle local
construction, never from the previous fitted endpoint. Return final iterate.

Single predeclared objective:
  sidechain_raw_MSE + sum(ReLU(penetration-1.5)^2)/(0.25*N_atom)
                     + mean_top16((ReLU(penetration-1.9)/0.1)^2)
Repulsion shape, normalization and top16 are inherited from frozen prior geometry
objective; coefficient is fixed1 (its first-stage scale). No new weights/schedule
search. This is one test of the combined objective, not isolation of each term.

Optimize repulsion only over topology-defined potentially variable distances. For
any allowed rotation, one endpoint must belong to its rotating component excluding
the rotation-axis endpoints, and the other to its fixed side excluding the axis.
Union across rotations. Two atoms on the same rigid side, or an axis endpoint and
rotating atom, have invariant distance for that rotation. Support is conservative:
'included' is not a claim of nonzero derivative at the current point. Excluded pair
distances must be invariant under audited moves. Geometry scores always include
ALL original allowed nonbonded pairs, including immutable collisions.

Budget remains one L-BFGS60/max_eval90,history20,strong_wolfe,lr1,tolgrad1e-8,
tolchange1e-12;twoCPU FP64 workers one thread,900s ceiling. Keep the prior local
screen: positive protein-mean AA vs original ideal-local; exact backbone/CA score;
strict checked chirality/raw RMS budgets14/14;total severe<=37,zero-severe>=7,
all-pair maximum penetration<=2.8412365888979707+1e-6Å. Report aggregate and each
case; do not hide per-case worsening under a passing aggregate. Compare separately
to archived pure-MSE endpoints; no new gate retroactively applied to them.

Record coordinate MSE separately from composite objective and its mean/tail terms.
Report active/excluded pair counts, all-pair collisions and fixed-distance remainder,
quality, runtime, iterations, source errors. Independently reconstruct pair support,
replay poses and objective terms, geometry and quality. Re-audit old14 pure fits and
replay one archived pure-MSE endpoint with optional terms OFF to verify compatibility.
No production parameterization changes. Even a local-screen pass does not establish
full geometry, final joint-output quality or input derivatives through the optimizer;
any endpoint comparison requires another frozen protocol.
