# Output backbone reference calibration, bounded v1

2026-09-30. Follow-up to bda69034; no solver, inference, training or production
reference changes. Reuse exactly the64 archived connection-calibration sources
and their32calibration/32held-out roles. Never access the reserved independent32.
Previous seven development GTs motivated this question; do not fit on them.

Measure internal-residue N–CA, CA–C, C–O lengths and N–CA–C / CA–C–O angles from
observed GT N/CA/C/O. Exclude first/last residues from estimation to avoid pooling
terminal and interior chemistry; retain terminal rows separately. Keep all other
source selection, masks and failures, without screening on measured geometry.
Verify the existing archive and selected GT hashes. This reuses previously
mapped experimental coordinates; no claim of new raw-mmCIF mapping validation.

Export the actual runtime CCD reference N/CA/C/O coordinates for20standard amino
acids, with source/cache hashes. Match the previously audited cache hash. Compare
geometry to those reference values, not regenerated predictions. Inspect all20
residue types; do not extrapolate this backbone audit to side-chain stereochemistry.

Before reading held-out geometry, fit each amino-acid/metric median using only
internal calibration residues; record linear q05/q95, observations and distinct
proteins. Require at least30residues from8proteins for a supported estimate. Leave
unsupported entries null; no ad-hoc pooled fallback. Write fitted parameters
before processing held-out coordinates. The median parameters are a diagnostic
candidate, NOT newly validated chemical gates or a complete reference conformer.

On held-out internal residues compare reference and fitted absolute error and
signed bias separately for each metric/type. Report per-protein means and paired
MAE change with2000protein bootstrap draws(seed9302030), not independent-residue
confidence intervals. Retain sample counts and unsupported exclusions. Report
pooled results too; no refitting based on held-out results. Angle units are
degrees. Descriptive q05/q95 intervals are not acceptance thresholds.

As a secondary necessary-condition diagnostic, test held-out experimental Cα
spans using old connection windows, GT branch, and either original CCD lengths
or the calibration-only amino-acid medians for CA–C and N–CA. Include all chain
edges, explicitly marking terminal use as extrapolation from interior estimates.
Keep other geometry/windows fixed; unsupported endpoints remain untested, in
the denominator. This does not construct output or establish global feasibility.

Stop after calibration/held-out audit and source provenance. Use results to
decide whether a separate output-chemistry representation experiment is justified.
Do not inject target-specific GT lengths, modify original Protenix reference
features, rewrite old gates, or run correction on these64sources.
