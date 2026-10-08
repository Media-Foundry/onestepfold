# Compensated final recycle evidence

Final collection2026-10-08: both fixed-budget runs, independent scoring and
checkpoint replay/timing completed. No model promotion.

`collection_manifest.json` verifies byte size/SHA256 of21remote files (79,349,266bytes).
`compensation_lock.json` fixes1110 source files, protocol, original archive
metadata, seeds and budgets. `compensation_preflight.json` records all input-only
caches, WT3 prefixes,912 two-noise baselines and replay/gradient audits.
`protocol.md` is the immutable executed protocol. `controller.json` is closed.
Per-seed summaries, exposure tables, reports, replay/timing and compact site
matrices are tracked. Large `scores.json.gz` and `history.jsonl` remain collected
locally and remotely, outside the commit. `independent_collection_check.json`
records864 independently recomputed site/arm Spearman and raw-regret checks.
`timing_summary.json` gives five-post-warmup medians, not pipeline speed.

Full input caches, prefixes, coordinates and later checkpoints remain in
`DiamondHill:/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/compensated_recycle_v1d_20261007`.
See [final findings](../../docs/mini_compensated_recycle_findings_2026-10-08.md)
and the historical [status](../../docs/mini_compensated_recycle_status_2026-10-07.md)
for boundaries and preserved pre-outcome implementation failures.
