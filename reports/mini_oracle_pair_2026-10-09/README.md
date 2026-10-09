# Fixed-single / oracle-pair evidence

Immutable source: DiamondHill
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/oracle_pair_audit_v1_20261009`.
All16 source artifacts in `manifest.json` are included verbatim and SHA256
verified. Six `scores_*.json.gz` include every output's continuous chirality
centers, fidelity, score and geometry transitions. `summary.json` holds all144
site-condition records and equal-parent summaries/paired descriptive intervals.
2736 coordinate NPZs remain at the source; `results.json` hashes each file.

`verify_results.py` uses numpy/scipy and prior committed noise-study records to
independently recompute432correlations,144regrets,384historical control/site
comparisons and verify all5472output geometry/tail counts and execution totals.
No optimizer update or input preparation occurred. Oracle target_z is diagnostic
information, not an available input to an accelerated deployment model.
