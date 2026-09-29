# Joint geometry with fitted initialization: bounded development comparison

2026-09-30. Continue the locked experimental-GT development source selection from
953b40fe. Retain all eight sources and the 3CR6 unsupported covalent-link failure.
Use only the two archived native model predictions per source, not GT self-inputs.
These remain historical C1/S1 with their recorded sampling settings, not C4.
No new model inference, training, mutation search, or independent32 access.

For each of16 planned prediction inputs run two arms: original zero parameters,
or the saved equal-atom fit parameters. Four source/arm slots for 3CR6 are skipped
and retained; 28 solves are expected across14 supported predictions. Freeze this
protocol and file hashes before solving. Do not replace failed sources or seeds.

Both arms MUST construct PoseVariables(adapter, original_raw) and
TailObjective(original_raw, ...), with identical native topology, local chemistry,
omega targets and all regularizer definitions. The fitted arm copies saved q into
this original chart. Do not use fitted coordinates to create a new zero chart.
Check chart-buffer and objective-buffer hashes across arms, zero-start replay,
saved-fit replay and input/code hashes. Start with fresh L-BFGS state in both arms.

Use unchanged anchored_geometry.solve and anchored_tail.TailObjective: rho1/10/100,
60 iterations/90 max_eval per stage, history20, lr1, strong-Wolfe, original
tolerances, mean repulsion plus top16 tail penalty. Final iterate only. No GT,
task loss, tuning, extra stages, best iterate or fallback in the solver. CPU FP64,
two single-thread workers,900s external ceiling per solve. Preserve the historical
60-iteration local-fit time, closures and iterations as EXTRA cost for the fitted
arm; this is equal joint-solver budget, not equal total compute.

Score raw, original local projection, actual start and final coordinates against
the same fixed experimental masks. Use the prior inter-residue observed AA/Cα
lDDT, same atom correspondence and FP64 distance evaluation. Keep both noises,
protein means, paired differences, all geometry/connection residuals, chirality,
structural displacement and worst atom moves. Existing joint thresholds remain
unchanged. Report source-instance and protein denominators explicitly; missing
cases cannot disappear or support a positive screen.

Independently replay final parameters in the original chart and recompute saved
coordinate scores/geometry. Compare fitted vs zero-start final outcomes, and each
vs raw. Better raw MSE or lDDT alone cannot substitute for joint geometry; better
geometry alone cannot substitute for experimental accuracy. No claim of optimizer
convergence, input derivatives, one-step correction or generalization.

Stop after this batch. If fitted initialization improves paired mean AA quality
without reducing joint-pass count, it is a candidate for further bounded C4
development, with CA tradeoffs and cost still explicit. Otherwise do not iterate
weights/budgets on this panel. Neither result authorizes reopening reserved32.
