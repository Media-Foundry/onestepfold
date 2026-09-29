# Independent32 read-only reporting supplement

2026-09-30. Original eight-GCD batch is running. This supplement implements the
already requested descriptive reporting; it does not change the source panel,
model, coordinate generation, objective, solver, masks or continuation screen.
Run only after authoritative pipeline `exit.json` and completed scored report.
Keep the original runtime/code directory unchanged; use a separate analysis copy.

Report complete3-seed means per protein, then group mean/median/P01/P05/P95/P99 and
ceil(5%*N) lower/upper-tail means. Paired differences use the same protein means.
Bootstrap whole proteins10000 times, seed20260929, only when every protein has its
complete triplet; missingness stays explicit. A four-protein source subgroup is
not broad evidence of generalization; its summaries/intervals are descriptive.
RMSD lower is better, lDDT/TM higher is better; lower tails aren't always worse.

Separately tabulate raw-pass retention, raw-fail repair, newly introduced failures,
unknown geometry, and all3-seed success. Existing gate failures and source subgroup
labels stay fixed. Derive these from serialized geometry metrics, independently
of whether the experimental-quality computation succeeded.

Read saved topology and raw/final coordinates; stream all allowed unordered atom
pairs, retain zero-overlap counts and full positive-depth distribution/histogram
(edges0,.25,.5,1,1.5,1.9,2,2.5,3,inf Å). These are descriptive bins, not new gates.
Do not resample or filter pairs to the largest clashes. Existing named maximum and
severe atom pairs remain available. Legacy residue38 proximity fields in archived
collision records are not used for any validation conclusion.

Record per-residue backbone/sidechain/CA movement and observed per-residue local
lDDT changes. This local score averages the same observed-atom scores within a
residue; it is descriptive, not a replacement for the atom-averaged protein score.
Record new CA and checked ILE/THR handedness violations vs raw independently of
summary fractions. No chemical-validity claim beyond the locked checks.

Tabulate actual raw model-load/conditioning/forward and repair time, closure count,
iteration caps and peak memory by length/source. Matched iteration caps are not
matched FLOPs; process walltime includes non-GPU overhead. Do not infer convergence
from solver success or claim deployment acceleration from these timings.

Original continuation screen is copied verbatim. Supplement errors prevent claims
about the corresponding descriptive evidence, not automatic redefinition of the
original gate. No additional predictions, repairs, trials or threshold tuning.
