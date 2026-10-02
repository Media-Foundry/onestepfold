# WT/target conditioning swaps — complete

[Findings](../../docs/mini_conditioning_swaps_findings_2026-10-02.md) ·
[Locked protocol](../../docs/mini_conditioning_swaps_v1.md)

Ten development parents,50sites,19non-WT substitutions,two noises. Six arms;
chemistry always native target. Exact is MODEL reference, not mutant experimental
truth. Cached target states are oracle inputs, not outputs from a trained head.

- `report.md`, `summary.json`: full six-arm table, protein-bootstrap intervals,
  prespecified paired contrasts and geometry transitions.
- `report.json.gz`: complete per-output, per-site, response-scale and worker data.
- `ranking_per_site.csv`: both19-AA and20-AA rankings, ties/low-signal fields.
- `per_prediction.csv.gz`: every arm's task, fidelity and chemistry record;
  unchanged WT results are explicitly labeled and reused across sites.
- `tail_summary.json`: local tails, both-noise top1, response-scale summary.
- `offline_audit.json`:960 coordinate packets verified,2000 exact task/geometry
  records replayed,600 independent lDDT and60 geometry checks; all ranks checked.
- `lock.json`: original conditioning/coordinate/inventory, code and weight hashes.
- controller/execution files: zero C4/ESM,11520NFE, all workers and collector exit0.
- `coordinate_manifest.json`, `storage.json`: raw coordinate identity/locations;
  the13GB full-state source remains in the preceding experiment's directory.

19-AA Spearman: WT-trunk .2524, Chem-only .2512, Local-only .3324,
Global-only .9536, Target-trunk only .9993. Top1 respectively12,13,14,83,100 /100
site-noise comparisons. The global-complement increment over WT-trunk is .7012,
not simply a high score with other paths left uncontrolled. Conditional evidence
supports approximating global target s/z; it does not prove where upstream
propagation occurs or remove geometry/generalization requirements.
