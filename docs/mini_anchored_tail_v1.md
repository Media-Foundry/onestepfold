# Worst-pair anchored feasibility contrast v1

2026-09-29 authorized mainline continuation. One new diagnostic; same six already-seen
parent raw inputs, same chemical reference, cis/trans modes, initial local projection,
three penalty stages1/10/100 and60 LBFGS iterations per stage,900s ceiling and final-only
acceptance. No warm start from previous solutions, no candidate search/training/Mini
forward/contact objective. Original archived results and sources remain immutable.

Sole objective change: original JointObjective plus rho times mean of
[relu(depth-1.9)/0.1]^2 over the16 largest current nonbonded penetrations. Scan all
archived graph-distance>3 pairs, retain exact top16 across chunks. Original mean
repulsion stays present.16,1.9A,.1A scale fixed before outputs. Ties make top-k
piecewise smooth; do not claim global smoothness or through-solver differentiation.
Use matched iteration budget, report actual closures/time separately (extra work per
closure means not equal FLOPs). S5 cases remain protection controls. Same old absolute,
all-checked-handedness, connection and displacement gates; no single-atom gate added
post hoc. Single-atom/rotation maxima continue to be reported.

Test streamed top-k vs dense value and gradient, finite differences away from ties,
empty/satisfied pair behavior; reuse pose/connection tests. Freeze source/input hashes
before six independent DiamondHill GCD jobs. Independently replay output parameters
and recompute final metrics using previous NumPy audit. Compare every case to the
archived mean-only result, including regressions. Stop after these six; do not tune
k, weights or iterations after results. Passing means local feasibility on regression
cases only, not design usefulness, generalization or one-step output. If it fails,
record residual type and stop this contrast without claiming nearby infeasibility.
