# Base delta propagation audit artifacts

Completed model-only Base C4 audit. See ../../docs/base_delta_propagation_findings_2026-10-06.md.

`report_compact.json.gz` retains every candidate/stage summary, identity/hash,
replay assertion, timing and configuration. Only individual singular-value
arrays were removed. Full singular spectra are in `report.json.gz` in the
local runtime mirror and `report.json` on DiamondHill. The uncompressed full
report SHA256 is recorded in independent_audit.json and manifest.json.

Snapshots retain eight fixed pair channels (0,16,...,112); full token/projection
vectors are retained. All60 snapshots and input packets remain in the remote
runtime named by the findings report. Independent Gram-eigenvalue checks use
these snapshots and do not run the model again. Full-tensor equality statistics
are worker measurements, while final conditioning full hashes are independently
cross-checked against plain output hashes.

Source freeze is in lock.json; the independent postprocessing script version is
recorded separately in asset_verification.json. Its later outside-row/column
energy analysis is explicitly post-hoc, with no additional GPU runs.
