# Mini editor candidate-correspondence intervention — CLOSED

All four fixed terminal workspace runs and independent CPU audits passed.
8,208 S1 calls; zero optimizer updates, C4 or input-encoder calls.
All 2,736 original outputs replayed bitwise; full correct summaries reproduce
previous independent scoring. Six focused tests passed. No promotion.

[Findings](../../docs/mini_reference_editor_intervention_findings_2026-10-07.md)
and [locked protocol](../../docs/mini_reference_editor_intervention_v1.md).
Implementation/protocol commit: `141570e0`; source experiment: `d2da9617`.

The same nine reused development proteins / eighteen sites are used for all four
runs. A single fixed derangement per site is shared across runs/noises/blocks.
Actual receiver chemistry/noise stays unchanged. No target conditioning used.
This is a no-training intervention, not a new model or speed benchmark.

Evidence:

- `intervention_lock.json`, `protocol.md`: frozen 1,108-file audit snapshot,
  checkpoint/source hashes, exact panel and AA donor maps, fixed budgets.
- `controller.json`, `aggregate.json`, run reports and summaries: all jobs complete;
  runtime/device integrity, counts, full output hashes and original replay checks.
- `collection_manifest.json`, `collection_verification.json`: all 29 collected
  files verified; site ranks and raw cross-noise regrets recomputed separately.
- `summary.csv`, `sites.csv`, `paired_contrasts.csv`: all conditions and all seeds;
  equal-parent means, pooled structural tails, descriptive parent bootstrap.
- `regret_contributions.csv`, `parent_regret_contributions.csv`: every site's
  selection and each site's/protein's contribution to the parent-equal mean
  difference; no exclusion of high-cost sites.
- `conditioning_energy.csv`: student-only common/AA-centered delta energy by block.
- `worst_outputs.json`: named worst cases; full geometry/continuous volumes remain
  in the larger score archive. `analysis.json`: summaries and contrasts.
- `intervention_comparison.png` / `.pdf`: fixed endpoints, no checkpoint selection.
  `analysis_source.py.txt` and `plot_source.py.txt`: exact postprocessing sources.

Large coordinates and full `scores.json.gz` remain at:
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/reference_intervention_v1_20261007`.
Their collected hashes are in the manifest. Local transfer archive SHA-256:
`948dde00d54cbfb0fbf9f3620eae413fcb57a8e6cb71d5091016869de4537eca`.
Original training/checkpoint archive is unchanged; new runtime writes belong to
this separate intervention root. GPU decode and CPU audit logs are retained.

Correct correspondence does not consistently beat both interventions. Common
improves mean ranking and centered structure-response error for all four models;
correct still has lower mean regret for both second-seed models. These mixed
findings do not establish reliable mutation-response transfer or folding speedup.
