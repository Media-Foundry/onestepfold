# C4/S1 calibrated objective with fitted initialization: bounded development test

2026-09-30. Freeze before new solves. Previous C4 confirmation bbbd3eea was positive
for calibrated vs original connection onsets, but calibrated AA remains0.012459
below raw. Test whether the already implemented local coordinate fit can preserve
more quality when followed by this frozen calibrated objective. No new inference,
training, targets, noise, branch choices, empirical windows or acceptance thresholds.

Use exactly the previous eight source slots and seeds12345/54321.3CR6 remains
unsupported and contributes four skipped comparison slots. Reuse the14 audited
calibrated zero-start controls, copying immutable coordinates/parameters with source
hashes and explicit reused_control provenance; this is NOT14new solves or independent
replay evidence. Independently audit them again alongside14new fitted-start outputs.

For the candidate only, run the existing equal-heavy-atom fit_local_projection on
the raw MODEL coordinates, max_iter60/max_eval90, CPU FP64, final iterate only.
Then build PoseVariables(adapter, ORIGINAL_RAW), copy the fitted parameters into
that same chart, and start a fresh joint optimizer. Do not construct a new chart,
change regularization origins, anchor to fitted coordinates, choose a best iterate,
or replace raw-selected cis/trans branches. Record fit MSE, gradients, closures,
iterations and time. Experimental GT is used only for scoring, never fitting.

Both arms use the exact CalibratedConnectionObjective and calibration file from
bbbd3eea. Frozen chemistry, repulsion/top16, weights, rho1/10/100,3x60L-BFGS and
final-state scoring. Match chart/objective buffers and raw input hashes across arms.
Two single-thread CPU workers,900s ceiling including fit for each new case. Preserve
every timeout/failure. The candidate pays an additional60iteration fit: report its
cost separately; equal joint budget does not mean equal total compute. Control
timings are historical and must not support a new speed comparison.

Score raw, local constructor, actual start and final against the same experimental
atom masks. Retain all original geometry/connection gates, strict checked chirality,
serious collisions, penetration, overall/per-atom displacement, branch mismatches,
AA/Cα-lDDT per noise and protein means. Add fitted-start retention: quality gained
at initialization may be lost again during joint solve. Do not equate better raw
coordinate MSE with better experimental structure accuracy.

Independent NumPy parameter replay and metric/objective recomputation must cover
all28available outputs. Check fit-start MSE independently and verify copied control
artifacts against prior hashes. The only allowed across-arm input difference is the
starting parameter values: raw, local chart, objective, chemical topology and GT
correspondence remain identical. Original C1 and C4 audit paths retain their checks.

Stop after this batch. Carry the previous bounded development screen: both paired
protein-mean AA and Cα improve and zero-severe+strict-checked-chirality+RMS-budget
count does not decline. Report old joint-pass separately. No deployment/generalization
claim, no reserved independent32 reuse, no implicit differentiation claim. If the
screen fails, close this combination without selecting alternate weights or more
iterations on the panel. Branch uncertainty remains a separate method question.
