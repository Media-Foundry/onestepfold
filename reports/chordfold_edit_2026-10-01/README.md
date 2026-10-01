# ChordFold hard-condition edit pilot — complete

See [findings](../../docs/chordfold_edit_findings_2026-10-01.md) and
[frozen protocol](../../docs/chordfold_edit_pilot_v1.md).

`report.json` contains all four experimental pairs, eight noise cases, full and
backbone-only arms, chemistry, contact changes, actual query counts and timings.
`lock.json` binds data/code/weights, sequences and full provenance metadata.
`execution.json` / `controller_execution.json` show all workers and scoring exited0.
`selection_audit.json` independently reproduces the candidate inventory/selection;
`independent_audit.json` checks saved coordinates with separate CPU formulas.

`complete_artifacts.tar.gz` includes native source/target inputs, source coordinates,
separate target GT mappings, every prediction, code/protocol snapshot, controllers,
logs and audit scripts. `archive_manifest.json` binds every member except itself;
all members were independently SHA256-verified after download. `SHA256SUMS` binds
the local files, including the archive. No weights are embedded.

Remote physical root:
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/chordfold_edit_pilot_v1_20261001`

Execution alias: `/data/user/shuang886/Folding/chordfold_edit_pilot_v1_20261001`.
Controller450975 completed. No active Chord jobs and no automatic follow-on run.
This is a four-pair development experiment, not independent generalization,
comprehensive chemistry certification or a source of causal mutation-effect labels.
