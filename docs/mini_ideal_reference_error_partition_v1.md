# Saved-output error partition after whole CCD ideal intervention

Read-only development diagnosis of e034567a. No model/solver execution, optimization,
new seeds, source selection, symmetry renaming or scoring threshold changes. Reuse
only verified artifacts from `mini_c4_ideal_reference_2026-09-30`: seven supported
proteins × two noises × native/ideal references. Keep unsupported3CR6 in the source
ledger. Verify archive members, source report/audit bindings and all old scores.

Report raw, native local/final, ideal local/final against the same experimental GT.
Use the existing inter-residue <15Å, strict {.5,1,2,4}Å thresholds, per-atom mean.
For a GT-neighbour pair i,j, weight=(1/n_i+1/n_j)/N_evaluable; partitions must sum
to the original score. Conditional subgroup means are separate from additive
contributions. Equal protein weights, with two noises averaged within each protein.

Fixed disjoint atom partitions: N,CA,C,O,terminal OXT,other sidechain; residue AA;
terminal vs interior; connection-active neighbourhood vs other; raw/GT branch-
mismatch neighbourhood vs other. The last two use frozen raw connection residuals
and saved calibrated onsets, and GT only for branch labelling. Neighbourhood of
connection i→i+1 includes residues i−1..i+2 clipped to the sequence. These are
observational strata, not causes or deployment features. Record coverage and
per-protein results; do not report a pooled conditional mean as protein mean.

Fixed pair partitions: backbone/backbone, backbone/other, other/other (backbone
is N/CA/C/O, matching previous report; OXT belongs to other here); residue separation
1,2–4,≥5. Retain additive contributions at each of four lDDT thresholds. Output
per-residue changes and complete atom score vectors, including negative cases.
Changes: native/ideal local−raw, final−raw, final−local; ideal−native at local/final.
Global precision checks sum partitions back to source scores. Independent dense
matrix audit verifies every atom vector and pair partition, not only means.

Interpretation: identify which atoms/contacts carry the remaining loss and how the
stage differences change. This does not prove force-term causality, physical
symmetry equivalence, or applicability outside these development proteins. Close
this analysis before choosing a new method intervention; no automatic weight sweep.
