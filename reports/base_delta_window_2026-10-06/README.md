# Base delta window audit artifacts

Completed bounded run `base_delta_window_v1_20261006`; finalized 2026-10-07.
See [findings](../../docs/base_delta_window_findings_2026-10-06.md) and
[locked protocol](../../docs/base_delta_window_v1.md).

- `lock.json`: frozen inputs, source and asset hashes, selected panel.
- `execution.json`, `controller.json`, `worker.log`: completed execution evidence.
- `report.json.gz`: lossless gzip of the complete worker report; per-input,
  per-stage, all128-channel statistics, replay checks and raw timing records.
- `independent_audit.json`, `.log`: separate CPU Gram-spectrum recomputation,
  integrity checks, parent/stage summaries and non-overlapping timing sums.
- `window_summary.csv`, `window_cost.png`: descriptive summaries; no decoder
  fidelity or measured acceleration claim.
- `local_tests.txt`: focused local validation.
- `manifest.sha256`: artifact checksums (excludes itself).

Full66-tensor snapshots perinput, frozen source and input references remain at
`pc@DiamondHill:/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/base_delta_window_v1_20261006/`.
Local runtime mirror: `/home/husrcf/Code/onestepfold_runtime/base_delta_window_v1_20261006`.
Snapshots are referenced by full SHA256 in the report, not stored in Git.
The independent auditor verifies all76,032 channel spectra from those snapshots.
The uncompressed report SHA256 is recorded in `independent_audit.json`.

Scope: 3 development sites × (WT+C/V/W), 76 native C4 executions, 304 recycles;
no ESM/MSA preparation, diffusion, training, approximation or new kernel.
Whole TriMul event timings overlap their child contraction timings: do not sum
these levels. Event/plain time ratios are descriptive, not measured speedups.
