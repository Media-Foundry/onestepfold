# Completed reference-anchor audit

See `docs/mini_reference_anchor_audit_findings_2026-10-10.md` and the locked
protocol. `collected/manifest.json` covers the full exported artifact. All files
were verified locally, including both gradient-vector NPZ files. The two
approximately39MB NPZ files are retained locally and on DiamondHill but excluded
from the source commit; no training tensors or checkpoints are committed.

Full archive location on DiamondHill:
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/reference_anchor_audit_v1_20261010/reference_anchor_audit_export.tar.gz`.
SHA256: `a6f1298f01f7e400044abe6b29032a76507f3b9e297b4ef911c34654e1530ec1`.

The local `local_verification.json` records independent NumPy arithmetic and
manifest checks; it does not claim another native backward run. The audit
performed zero optimizer updates and zero S1 evaluations. Its positive gradient
result is the rationale for a separate training trial, not a quality result.
