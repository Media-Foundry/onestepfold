# Frozen raw-contact preservation: one bounded objective intervention

Following afa79dc7, same7 supported development proteins ×2 saved C4/S1 predictions;
3CR6 four unsupported comparison slots retained.14 new joint solves versus14 reused
whole-ideal ZERO-start controls from c4_ideal_reference_v1_20260930 odd cases. No
failed warm starts, new inference/training, independent32/Y38 use, GT selection,
coordinate repair after solver, extra iterations or weight search.

Change only J=J_calibrated + E_contact, coefficient1 outside the rho multiplier.
All original raw coordinate/angle anchors, calibrated connections, all-pair repulsion,
top16, branches, whole-CCD-ideal templates, zero parameters and3×60LBFGS remain.

Contact graph is frozen from ORIGINALRAW and original native allowed nonbonded
pairs:sequence separation>=5,4Å<=rawdistance<15Å. No GT/mask-dependent neighbour
selection, including no reuse of last turn's GT-defined attribution pairs. Lower
cut excludes very short raw overlaps from preservation, upper bounds locality.
These are fixed design choices, not physically guaranteed optimal thresholds.
All original nonbonded pairs remain in chemistry loss and scoring.

Let n_i be degrees on selected graph and N_active count its nonisolated atoms.
Each unordered pair weight w_ij=(1/n_i+1/n_j)/N_active;sum weights1 for nonempty
support. Empty support gives differentiable zero and is recorded, not replaced.
For e=||X_i-X_j||-d_raw and delta=1Å:
  E_contact=sum w_ij * 2*delta²*(sqrt(1+(e/delta)²)-1).
Use stable equivalent2*e²/(sqrt(1+e²)+1) in Angstrom units. Quadratic nearzero,
linear for largeerror;not an lDDT substitute or strict contact guarantee. Original
coordinate anchor remains. This tests one complete formula,not an ablation of
window,normalization orrobustness independently.

TwoCPU FP64 workers1thread,900s/slot,same final-iterate rule. Freeze code and source
hashes and preflight14zero charts beforelaunch. Tests check raw-only selection,
normalization,rigid invariance,gradcheck,empty support and coefficientindependentofrho.
Independent audit reconstructs selected pairs/distances/degrees in NumPy, checks
saved initial/final poses, contactcost and totalobjective, originalGTscores/geometry;
paired base-objective andchart hashes match. Record contactcost on BOTH saved final
arms without reoptimizingcontrol. Re-audit prior wholeideal andsidechain-start paths.

Old bounded screen unchanged:positive protein-mean AA AND CA difference, no drop
of zero-severe+strict checkedchirality+rawRMS passcount. Old absolute/connection/full
jointacceptance separatelyretained. All14cases,7proteins,source failures andcosts
reported. Runtime term hasno GT; GTusedonlyforevaluation. If fails, close this
incrementalraw-preservation version, no samepanelweight sweep. A pass is development
evidence only; detachedsolver isnot a differentiableone-step output/designoracle.
