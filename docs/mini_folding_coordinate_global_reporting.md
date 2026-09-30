# Aligned-Cα RMSD reporting supplement

Recorded before terminal evaluation preparation. The scientific ablation protocol
already requires aligned Cα RMSD. The underlying scorer has always computed it;
this supplement exposes those existing scores in the terminal Markdown report,
where the previous presentation showed only AA/Cα-lDDT and chemistry tables.

`summarize_global_structure` reads the completed evaluation's unchanged per-case
`ca_aligned_rmsd` values. It does not run inference, refit an alignment, change
observed masks, rescore coordinates or alter a training/acceptance threshold.
It rejects missing/duplicate records, nonfinite scores and inconsistent cohorts.

For each existing cohort and model, average the two assigned noises within each
protein, then report mean, median, P95, P99 and worst-5% mean. For the already
locked candidate/reference pairs, report paired mean differences, the same
protein-bootstrap rule, P95/P99, worst-5% mean and number of proteins whose RMSD
increased. **Positive differences mean worse RMSD**, opposite to lDDT. All
per-protein and per-noise differences are retained in `global_structure.json`.

This presentation gap became material in the intermediate TRAIN32 probe:
coordinate-zero improved local-distance scores but increased aligned-Cα RMSD.
No new candidate or acceptance rule is chosen from that result. The supplement
does not amend old reports or change the current model recommendation.

The pending evaluation code is updated before its prepare job creates `lock.json`;
its new source hashes will be bound by that lock. Active training code and its
lock remain unchanged. The original deployment observation remains historical;
a separate reporting supplement deployment record captures this addition.
