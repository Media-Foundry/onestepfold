# Completed paired reference-anchor experiment

Primary endpoint:128 updates; both seeds272001/272003 completed all train,
coordinate-score and independent tensor-verification jobs. No promotion.
Report: `docs/mini_reference_anchor_training_findings_2026-10-10.md`.

This is a compact review bundle, not a standalone copy of all original inputs.
It contains full analysis, optimization ledgers, fixed-node latent evaluations
and summaries, tensor-verification records, training histories, publication
tables and PNG/PDF figures. `manifest.json` and `postprocess_manifest.json` are
the manifests of the complete archive and retain its original relative paths;
they should not be applied to this reduced bundle as if no files were omitted.
The initial/interim launch artifacts elsewhere in the parent directory remain
historical records and are superseded for completion status by this bundle.

Full archive on DiamondHill:
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/reference_anchor_training_v1_20261010/reference_anchor_training_export.tar.gz`

Archive SHA256:
`f71a111886df535642c6b3ea0e50bdb37a06734db336d01dd2aa18cf9c9782d4`

Archive bytes:247,838,833. Scientific lock SHA256:
`13cda88bacb0bca93f93c59fad801428d120b37f124bcdc022d915127c4cdeff`.
Postprocessing lock SHA256:
`c82688ab304f74053b317352844afa2484524ef3c5111f6615cd145ec512df3f`.

The archive includes full scored rows, frozen source, original locks and reused
controls. Large model checkpoints, cached tensors and individual coordinate
files remain in the original hash-bound remote runtime. They were used in the
successful independent tensor and coordinate checks, not silently recreated
from new model versions.

Local immutable extraction:
`/tmp/anchor_paired_terminal_20261010/export`.
Independent local recomputation:
`/tmp/anchor_paired_terminal_20261010/local_recheck`.
`local_recheck.json` records exact agreement of verification, ledger and analysis.
No geometry recomputation from coordinates was performed locally.

To reproduce tables/figures, verify the full extracted archive with
`fastglycan.anchor_results.verify_anchor_results`, run
`fastglycan.anchor_results.analyze_anchor_results`, then invoke
`scripts/render_anchor_report.py --root <full-export> --output <new-directory>`.
`figures/manifest.json` binds all figures and both CSV tables to the analysis.
All fixed nodes are retained; 128 is primary. The CSV selection details keep
student old-noise margins distinct from Exact old/new regret and choices.

All panels are reused development data. Model C4 fidelity and the distance
proxy are not experimental mutation accuracy or calibrated thermodynamics.
