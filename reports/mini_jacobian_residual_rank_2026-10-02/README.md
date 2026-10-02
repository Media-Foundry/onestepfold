# Fixed-WT Jacobian + residual functional rank — complete

[Findings](../../docs/mini_jacobian_residual_rank_findings_2026-10-02.md) ·
[Locked protocol](../../docs/mini_jacobian_residual_rank_v1.md).

Valid full run: `jacobian_residual_rank_v1_20261002_retry1`.
Same10 TRAIN parents/50sites and archived19nonWT endpoints per site. The earlier failed
launches are engineering history, not missing/scientifically rejected samples in this run.

- `report.json.gz`: all23arms,50sites,2noises,20AA including shared WT; worker evidence includes complete residual Gram/eigenspaces and1900full-rank checks.
- `summary.json`, `report.md`: functional metrics with Exact/Baseline references. In this directory, `raw_k*` and `balanced_k*` mean **tangent plus residual PCA**, not direct PCA. `tangent_only` is separate from K0.
- `comparison.json`: matched K/metric differences vs direct PCA (10e40e2e),10-protein bootstrap10000(seed228101). Per-arm summaries reuse the prior scorer's seed227101.
- `per_prediction.csv.gz`:46000logical rows,including reused WT. `ranking_per_site.csv`:8800comparisons including19AA/20AA andboth references. These are not independent proteins or actual NFE counts.
- `supplement.json`, `residual_rank_curves.png/.pdf`: both-noise top1, tails, spectra and paired curves. `summarize.py ROOT` reproduces them with direct-control folder adjacent to ROOT.
- `tangent_fit.json`: uncentered hard/tangent/residual energies, ratios and cosines. Ratios are not causal information fractions.
- `lock.json`: fixed source hashes, weights, schema, sites, noise, code and budgets. `controller.py` and execution/handles files record all8GPU+32CPU+collector exit0.
- `basis_audit_*.json`: independentCPU FP64 hard-WT-T reconstruction, chunked Gram/eigh/projector audit ofall50sites. `basis_audit_execution.json`:all8exits0.
- `offline_output_audit.json`:960coordinatepackets,4000reference task/geometry,2300independent lDDT,8800rank checks exactly reproduce.
- `run_audit.json`:950JVP,20projection checks,3880recycle,41820NFE,full-rank errors,timing/memory and9focusedtests.
- `coordinate_manifest.json`, `tangent_manifest.json`, `storage.json`: raw data SHA/bytes/locations. Full50tangent packets(12.606GB) remain on DiamondHill; source13.005GBconditioning remains in its prior archive. Raw arrays are outsideGit.
- `preflight_history/`: short-chain native preflight success; long-chain uncheckpointed VJP OOM after JVP success; checkpointed long preflight success; packaging and WT-axis assertion failures before the complete retry. No functional result was used to select a rerun or alter definitions.
- `graph_change_audit.json`: full nonpartial/nontruncated check. The whole workspace includes unrelated older edits; staged code only adds this diagnostic. Staged risk is medium for its reconstruction/evidence flows; no existing production function changed.

All approximations use WT s_inputs+TARGET native chemistry. K18 is bitwise equal to
Baseline, not necessarily Exact. Tangent is probability-space at one-hot WT on the
fixed WT graph, full current continuous ERC+ESM+C4; it is not a derivative through
hard graph switching. Reverse checks use activation checkpointing without truncation.
Frozen runtime source/tar are retained remotely with hashes; use that snapshot for exact replay, rather than assuming every pre-existing workspace dependency is represented by this commit.
No FD surrogate, training, model promotion, speedup or design-success claim.
Stop AA-axis linear compression as the next-model direction; preserve partial selection
benefits and numerical evidence. Low-dimensional nonlinear AA queries remain untested.
