# Read-only experimental connection audit v1

2026-09-30. Follow the closed adcc7c1a initialization comparison. No new prediction,
optimization, weight/threshold change, repair or independent32 access. Use the same
seven supported development sources and preserve 3CR6's source failure.

Audit each unique experimental GT once, all14 cached raw C1/S1 predictions, and
their28 archived joint outputs. Seven GT proteins are not14 independent samples.
Verify source hashes, native atom identity and complete masks. Independently join
GT atoms to the original mmCIF by source chain, label sequence ID, atom name and
the recorded altloc selection; account for assembly rigid transforms by fitting
one proper rigid transform, with maximum coordinate discrepancy <1e-3 Å.

For every adjacent residue pair, compute C–N distance, CA–C–N/C–N–CA angles,
CA–C–N–CA omega, and N(next)–CA–C–O phase. Use an independent NumPy implementation
(law of cosines and plane normals), cross-check dihedrals with Gemmi and residuals
with frozen JointObjective. Report actual units, signed angular deviations, source
author residue labels, resolution, residual quantiles and per-edge records.
Degenerate plane normals are outside the independent dihedral reference domain;
retain such structures as unauditable for that comparison rather than silently
normalizing with a new epsilon or dropping them from the structure denominator.

Keep current gate tolerances (.03 Å,.04,.04,.1,.1) and the actual objective onset
at half those tolerances distinct. Count activity at the onset and rejection at
the existing gate, per protein and pooled over edges. Decompose the connection
energy into its five terms; this is an objective decomposition, not a causal
attribution of final lDDT loss. For GT use its own closest cis/trans branch for
the intrinsic-shape summary; separately count the branch selected by each raw
prediction and any disagreement with GT. Do not quietly replace raw's fixed branch
when checking saved final predictions.

Compare the three length/angle scales descriptively with the named standard
deviations in the primary AlphaFold residue_constants source; store immutable
source URL/commit/content hashes and values. A12-sigma residual overlay may be
reported for those three terms only, clearly labelled a reference-scale comparison,
not a full AlphaFold violation rerun or proposed new acceptance rule. Omega and
carbonyl are not covered by that overlay. No empirical Gaussian claim.

Look at all existing edges, not only the largest failures. Report high-resolution
sources as descriptive context, not a replacement panel. Cross-protein claims and
threshold calibration require broader data; these seven repeatedly used development
proteins cannot certify a new geometry protocol. Preserve all previous pass/fail
results and the rejected warm-start candidate. Stop after the read-only audit.
