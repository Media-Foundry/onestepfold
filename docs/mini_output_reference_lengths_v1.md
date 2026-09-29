# Bounded C4 output-reference CA–C / C–O intervention

2026-09-30. Follow abe62a7d. Change ONLY output-constructor reference lengths on
the existing eight development source slots/seeds12345,54321. No model inference,
training, new protein selection, independent32 access, or calibration refitting.

Interior residues only (2..L-1): move C along the original CA→C ray to the frozen
amino-acid CA–C median. Place O relative to the new C along the original C→O ray,
at the frozen C–O median. Keep every other reference coordinate bitwise unchanged.
Both terminal residues remain wholly unchanged; no unvalidated terminal extrapolation.
Require the CA–C bond to be a bridge with carbonyl-side component exactly{C,O} in
each changed local graph. Reject other chemistry; do not silently move connected
side chains or ring atoms. All medians are from the32calibration sources only.
No N–CA/angle/side-chain changes, input-feature changes, or target-specificGT values.

Before solving, verify original parameters/cache bindings and preflight all seven
supported inventories: unchanged topology/non-carbonyl atoms/Pro ring/termini;
correct target lengths; preserved angle directions, CA handedness and ILE/THR
centres; proper rigid-transform covariance and idempotence. Check local projection
retains original raw Cα positions and changes only intended carbonyl coordinates
within numeric tolerance. Retain3CR6unsupported source failure; no substitution.

Compare native_ref (14 audited archived calibrated-zero controls, NO new solve)
with length_ref (14 new solves). Original raw C4/S1 inputs, native topology/radii,
geometric scoring reference and all gates remain unchanged. The new reference is
used ONLY by ArticulatedOutput. Start with zero pose/torsion parameters anchored
to the original raw prediction; no fitted start. CalibratedConnectionObjective,
onsets/branches/repulsion/top16/regularization/rho1,10,100 and3x60L-BFGS unchanged.
900s ceiling, two single-thread CPU FP64 workers, final iterate only. Parameter
chart geometry may change; objective buffers and raw inputs must remain identical.

Report raw/local/start/final AA/Cα lDDT, old geometry and connection outcomes,
strict checked stereocentres, raw displacement, timings, iterations, failures.
Keep old bond-RMSE reference even though it is imperfect; do not silently redefine
an acceptance metric to favour new lengths. Also verify output-constructor target
lengths separately. Native input package is immutable. GT used only for scoring.

NumPy saved-parameter replay and independent metric/objective recomputation cover
all28 available outputs. Verify new references independently from the two radial
updates and old archives/control hashes. Re-run prior C4/fitted-start audits in
shadow folders to ensure the new opt-in contract did not change old audit semantics.

Carry the prior bounded screen: positive paired protein-mean AA AND Cα improvement,
and no reduction in zero-severe+strict-checked-chirality+RMS-budget count. Old joint
pass is separate. Equal solver budget is not equal wall time; historical controls
do not establish speedup. Stop after this one batch. A failure closes this version,
not all reference-geometry methods; no weight sweep, iteration extension or
per-target parameter adjustment. No solver-input gradient or deployment claim.
