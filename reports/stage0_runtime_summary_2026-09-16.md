# Stage 0A Runtime Yield

The nine-point Protenix-Mini-ESM factorial sweep completed on the A800
partition `i64m1tga800ue` with one independent GPU job per `(cycle, step)`
setting. Every setting produced all 1,024 requested predictions and all 1,024
confidence summaries. The run logs reported exit status 0, an empty Protenix
error list, zero confidence parse errors, and zero `has_clash` flags in the
confidence summaries.

Across the nine one-GPU jobs, the summed wall time was 4.80 GPU-hours (the
jobs ran independently and overlapped in the scheduler), and the summed
Protenix inference time was 4.59 hours.

This is a runtime and model-confidence report, not a structural accuracy
report. TM-score, lDDT, RMSD, and geometry metrics require comparing the CIF
outputs with the frozen GT records and are intentionally not inferred from
pLDDT or pTM.

| setting | CIF / target | wall (min) | internal (min) | peak RSS (GiB) | mean pLDDT | mean pTM | mean GPDE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| c1_s1 | 1024 / 1024 | 25.67 | 22.16 | 17.19 | 84.66 | 0.8543 | 0.6656 |
| c1_s2 | 1024 / 1024 | 21.92 | 21.00 | 17.25 | 85.23 | 0.8599 | 0.6168 |
| c1_s5 | 1024 / 1024 | 24.00 | 23.05 | 17.21 | 86.03 | 0.8775 | 0.5320 |
| c2_s1 | 1024 / 1024 | 29.34 | 28.04 | 17.21 | 86.15 | 0.8661 | 0.6252 |
| c2_s2 | 1024 / 1024 | 29.74 | 28.43 | 17.21 | 86.63 | 0.8705 | 0.5825 |
| c2_s5 | 1024 / 1024 | 31.82 | 30.80 | 17.24 | 87.33 | 0.8872 | 0.5051 |
| c4_s1 | 1024 / 1024 | 41.81 | 40.52 | 17.22 | 87.08 | 0.8741 | 0.5961 |
| c4_s2 | 1024 / 1024 | 41.66 | 40.62 | 17.21 | 87.38 | 0.8761 | 0.5665 |
| c4_s5 | 1024 / 1024 | 41.92 | 41.00 | 17.20 | 88.11 | 0.8934 | 0.4905 |

The complete machine-readable rows are in
[`stage0_runtime_summary_2026-09-16.csv`](stage0_runtime_summary_2026-09-16.csv)
and the nested statistics are in
[`stage0_runtime_summary_2026-09-16.json`](stage0_runtime_summary_2026-09-16.json).
The reproducible summarizer is
[`scripts/summarize_stage0_runs.py`](../scripts/summarize_stage0_runs.py).

Raw predictions remain on HPC under:

```text
/hpc2hdd/home/shuang886/Folding/stage0_v1/protenix_runs
```

They are not copied into Git because the CIF/JSON tree is multi-gigabyte.
The next required step is GT-backed evaluation against `temporal_dev_v1`,
followed by the paired degradation analysis relative to `c4_s5`.
