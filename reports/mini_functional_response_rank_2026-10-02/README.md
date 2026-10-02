# Conditional local functional-rank experiment — complete

Read [interpretation](../../docs/mini_functional_response_rank_findings_2026-10-02.md)
and the [pre-run protocol](../../docs/mini_functional_response_rank_v1.md).

50 development sites, 10 parents, 19 non-WT substitutions, two matched noises.
Only local s_i/z_row/z_col are reconstructed; all other conditioning is exact
hard-target. Bases and coefficients use all endpoints. This is not a global
compression/prediction benchmark, a mutant experimental validation, or speedup.

- `report.md`: primary curve; `summary.json`: protein bootstrap intervals,
  geometry transitions and both 19-AA /20-AA rankings.
- `report.json.gz`: complete 50-site scoring and execution evidence.
- `ranking_per_site.csv`: all site/noise/rank ranking results.
- `per_prediction.csv.gz`: every reference/intervention metric (WT reused and
  explicitly labeled); structure reference is exact model output, NOT GT.
- `tail_summary.json`: local tails and both-noise top1 consistency.
- `offline_audit.json`: coordinate SHA verification, 1100 independent lDDT
  recalculations, Spearman cross-check and descriptive response-scale supplement.
- `projection_audit.json`: 500 direct rectangular-SVD comparisons; documents
  FP32 quantization-bound audit and the initially overstrict absolute audit check.
- `lock.json`, controller /execution files: immutable runtime inputs and counts.
- `coordinate_manifest.json`, `conditioning_manifest.json`, `storage.json`:
  large data identity and location. Full native conditioning is remote only;
  coordinate/inventory packets are also on the local runtime path.

K5: AA fidelity lDDT .999534, 19-AA Spearman .979965, top1 90/100 comparisons
(42/50 sites on both noises). K0 already .959193 and85/100. K5 has24/1900
local RMSD>1A (all6UFE site92, max6.19344A) and24 newly failed chemistry screens.
No training, checkpoint promotion, low-rank deployment or design-success claim.
