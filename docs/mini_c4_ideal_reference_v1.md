# Frozen whole CCD ideal-reference C4/S1 development comparison

This is one bounded output-representation experiment following the positive local
GT-oracle template screen in e8de8479. It does not reopen independent32, generate
new predictions, train weights, or change production Mini input chemistry.

Use all20 frozen templates in
`reports/mini_ccd_ideal_template_2026-09-30/reference/templates.json`, explicitly
exported from CCD ideal coordinate fields. Replace every complete interior residue
by its named ideal template, properly rotated into the native N/CA/C frame and
translated to native CA. Keep first/last residue references exactly native. Check
atom inventory and named covalent adjacency; preserve native bond-order graph.
Do not select native vs ideal by residue class, optimize atom renaming, select
conformers using GT, fit starts, or combine with the previous two-length changes.

Use seven supported development proteins, two archived C4/S1 noise predictions
12345/54321 each. Preserve eighth source3CR6 unsupported topology in all4 slots.
The control is the archived calibrated zero-start native-reference result from
`c4_connection_confirmation_v1_20260930`; reuse14 outputs hash-exactly. Compute14
ideal-reference solves with the unchanged raw anchor, calibrated connection
objective, raw cis/trans branch, top16 repulsion,3×60 L-BFGS final-iterate budget.
Two CPU FP64 workers, one thread each,900s ceiling per slot. No parameter search,
extra iterations, contact objective, source replacement or candidate search.

Only the output reference and consequent local chart change. Native model features,
raw coordinates, scoring reference, masks, topology, radii and objective buffers
remain unchanged. Zero pose parameters and original raw anchors are mandatory.
Preflight: all20 template inventory; seven actual inputs; proper rotation,
idempotence, equivariance, terminal and CA retention, checked stereo signs,
reference bonded lengths, no constructor fallback. Fixed templates are computed
chemical references, not experimental GT or guaranteed energy minima.

Audit all28 supported results against saved poses with NumPy, independently
reconstruct ideal-reference frame alignment, verify bonded-length invariance,
old gates, all-atom/CA lDDT against experimental GT, complete VJP unrelated/no
new derivative claim. Re-audit old C4, fitted-start and two-length archives to
verify opt-in compatibility. Save final coords/parameters and content hashes.

Predeclared screen: positive paired protein-mean changes in BOTH all-atom and CA
lDDT vs native-reference calibrated control, with no decrease in zero severe
collision + all checked chirality + existing RMS-budget count. Retain old joint
connection/absolute gates independently; screen success is not deployment or full
geometry acceptance. Report raw/local/final, per-protein and per-prediction results,
failures in denominators, branch mismatch, worst overlap, displacement and cost.
This is seven development proteins, not fourteen independent proteins. No method
tuning on these results within this batch. Close batch after audit and analysis.
