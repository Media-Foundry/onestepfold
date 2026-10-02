# Global s/z functional-rank v1 — completed, no model promotion

Primary narrative: [findings](../../docs/mini_global_response_rank_findings_2026-10-02.md).
Frozen definitions: [protocol](../../docs/mini_global_response_rank_v1.md).

- `report.md`, `global_rank_curves.png/.pdf`: all five variants and ten requested K.
- `report.json.gz`: complete per-site/per-AA/per-noise results, worker records, Gram/eigenspace evidence and full-rank checks. `summary.json` contains protein-averaged metrics and 10-protein bootstrap intervals.
- `per_prediction.csv.gz`: 104000 logical rows (includes shared WT replicated per site/arm). These are NOT 104000 unique predictions; actual NFE is 95020.
- `ranking_per_site.csv`: 20400 rank comparisons, separately to Exact/Baseline and with/without WT.
- `supplement.json`: both-noise Top1 counts, tails, spectra, paired balanced-minus-raw comparisons. `summarize.py ROOT` reproduces these tables/plots from `report.json.gz`.
- `lock.json`: source states/coordinates/weights/code hashes, fixed sites/arms/noises and scorer assignments.
- `controller*.json`, `execution.json`, `score_execution.json`, `handles.json`, `score_handles.json`, controller scripts: remote execution evidence. All phases complete with exit0.
- `basis_audit_*.json`: independent CPU NumPy FP64 chunked Gram/eigenspace audits on all50 sites. `basis_audit_execution.json` records all8 audit exits.
- `offline_output_audit.json`: 960 coordinate packets,4000 reference task/geometry comparisons,5200 independent lDDT,20400 ranking checks; all exact.
- `run_audit.json`: counters, full-rank max errors, runtime decoder field reads, peak GPU allocated memory and10 focused tests.
- `coordinate_manifest.json`, `storage.json`: SHA/byte counts and locations of raw coordinates outside Git; 13GB source conditioning is reused in place, not duplicated here.
- `graph_change_audit.json`: full/nonpartial/nontruncated precommit graph check. All-workspace changes include unrelated pre-existing edits; staged additions are this batch only.

K18 outputs are bitwise equal to the uncompressed **Baseline** (WT s_inputs + target s/z).
They are not all identical to **Exact** (target s_inputs + target s/z): Baseline's residual
s_inputs effect remains separately reported. No new ESM/C4, training, Jacobian, target,
model selection or speedup assertion. Oracle means/bases/coefficients use all19 hard teachers;
one-block controls keep the other block exact; separate-both may use up to2K coefficient directions.
Same10 TRAIN parents/50 sites are development data, not a new independent validation panel.
