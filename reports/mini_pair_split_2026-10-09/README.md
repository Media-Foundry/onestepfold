# Mini terminal conditioning split evidence

Source: DiamondHill `/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/pair_split_audit_v1_20261009`.
Protocol: `docs/mini_pair_split_v1.md`; findings: `docs/mini_pair_split_findings_2026-10-09.md`.

`manifest.json` records ten verbatim source JSONs in this directory and six
full remote `scores_*.json.gz` SHA256 values. All sixteen were fetched and
hash-verified at collection. Full scores (all chirality centers) and all15504
coordinate NPZs remain at the immutable source; the NPZ hashes are in results.
Full scores are omitted from git to avoid approximately 83MiB of repeated per-center arrays.

`output_records.json.gz` derives all32832 output records, retaining every task,
fidelity, geometry count, transition and the minimum oriented-volume center.
The remaining per-center arrays are available in the full source scores.
`derived_manifest.json` hashes this compact derivative. `summary.json` includes
864 site-arm rows, per-parent means, fixed paired intervals and geometry totals.
`verify_results.py` independently checks2592 correlations,864regrets,576prior
endpoint/site comparisons and all geometry/tail counts. Run from repo Python
with numpy/scipy; uses the previous committed noise-study site_records.json.

Controller's terminal `complete=true` is authoritative alongside six complete
shards and summaries. One per-job display status remained `running` from its
last poll; it does not indicate a remaining GPU process. Original metadata is
not edited. All counts and complete shard records were verified independently.

All data are development diagnostics, not independent confirmation or a new
inference speed benchmark. No optimizer updates or input preparation occurred.
