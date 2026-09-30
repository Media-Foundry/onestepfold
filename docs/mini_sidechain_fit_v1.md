# Fixed-backbone sidechain torsion fit: bounded local development screen

Follow f028e9f6's read-only loss partition. No new model predictions, GT fitting,
sequence search, independent32 reuse, joint-solver execution or default promotion.
Use the14 raw C4/S1 predictions and archived WHOLE-ideal local constructions from
`c4_ideal_reference_v1_20260930`, same seven supported proteins, two seeds12345/54321;
retain3CR6 unsupported in two local-fit slots. Validate prior report/audit/code/data
hashes before launch. Freeze this protocol and all runtime code in lock.json.

Construct the same whole-ideal chart from raw. Optimize only single-bond bridge
rotations whose moving set contains none of N/CA/C/O/OXT. All per-residue translations,
rotations and other angles fixed zero. Pro/ring-only and no-DOF residues unchanged;
no ring breaking, flexible bond geometry, symmetry atom remapping or class-specific
template choice. Nonmobile coordinates are exactly retained from local initialization.
Mask parameters in the forward map, and save full zero-pose angle vectors for audit.

Fit equal-weight non-backbone/OXT heavy-atom squared coordinate error to raw, using
one zero-start L-BFGS: lr1,max_iter60,max_eval90,history20,strong_wolfe,
tolerance_grad1e-8,tolerance_change1e-12. Fixed final iterate, no best selection or
fallback. No-GT objective, no random restart, no budget escalation. Two CPU FP64
workers, one thread,900s ceiling. No-DOF case returns exact initialization with zero
iterations, not failure. Final vectors and raw/local/fitted/GT saved.

Evaluation: same original observed all-atom/CA lDDT; original scoring topology,
radii and bond references. Strict checked CA/ILE/THR signs, severe count, penetration,
bond/peptide geometry, original raw displacement budgets and all old connection
windows. Preserve full local baseline failures. Report per-protein and per-seed,
source skips, eligible DOFs, no-DOF residues, atom displacements, closure/time/RSS.

Predeclared LOCAL continuation screen (not deployment): all14 supported fits
finish/verify; exact N/CA/C/O/OXT preservation and unchanged CA lDDT; positive paired
protein-mean AA change; all14 retain strict checked chirality and original raw RMS
budgets. Aggregate collision burden must not increase: total severe pairs<=37,
zero-severe instances>=7,max penetration<=2.8412365888979707+1e-6Å (archived ideal
local baseline). Also report each case's increases; aggregate screen does NOT imply
per-case nonregression, good chemistry, or solved chain connections. Failed screen
closes this local version without automatically launching joint solves. Even success
requires a separately frozen endpoint comparison before any claim of final utility.

Independent NumPy saved-pose replay and score/geometry recomputation; verify all
forbidden parameters zero, mobile sets match topology, bond lengths/local angles and
checked chirality preserved. No derivative-through-optimizer claim. This tests one
coordinate-fitting proposal, not the full chemical manifold capacity or a minimum.
