# Hard-mutant C4 local response rank — complete

[Findings](../../docs/mini_hard_response_rank_findings_2026-10-02.md) and
[frozen protocol](../../docs/mini_hard_response_rank_v1.md).

- `report.md`: all14 spectral summary variants.
- `report.json.gz`: complete machine-readable results,50 sites and8 worker reports.
- `per_site.csv`: every site/normalization/centering result.
- `lock.json`: exact sequences, positions, code/weight hashes and budgets.
- `gram_evidence.npz`: each site's FP64 Gram matrices for s,row,column and duplicated
  diagonal; enough to reconstruct every reported spectrum without GPU inference.
- `independent_audit.json`:700 Gram and100 direct rectangular-SVD checks.
- `endpoint_manifest.json`, `storage.json`: FP32 endpoint locations and hashes.
- `execution.json`, `controller_execution.json`: all workers/collector exited0.
- `controller.py`: exact bounded remote launcher.

The50 FP32 endpoint archives (148,922,936bytes) and full execution snapshot are
preserved outside Git, at both locations in `storage.json`. Every local endpoint
was verified against its remote recorded SHA256. They are not silently converted
to FP16 or replaced by Gram matrices. The latter are compact additional evidence.

Load full results with Python `json.load(gzip.open('report.json.gz','rt'))`.
Endpoint AA order is `ACDEFGHIKLMNPQRSTVWY`; remove the WT row before differencing.
Indices in file names are1-based; position_0based is recorded separately.
Counts use10 proteins/50 sites/960 unique hard sequences/20 replay forwards;
there are no diffusion predictions, new trained weights or speedup claims.
