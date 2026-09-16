# Stage 0B GT-Backed Evaluation

All 9,216 predictions were scored successfully against the frozen `temporal_dev_v1` Stage B GT (1,024 exact sequence groups per setting, zero evaluator errors). Metrics use exact residue correspondence within each sequence group. The reported Cα TM value is a fixed-correspondence Kabsch TM-style score; it is not a full TM-align re-optimization. RMSDs are Kabsch-aligned on common Cα atoms. lDDT is superposition-free and uses reference atom pairs within 15 Å with the standard 0.5/1/2/4 Å thresholds.

## Mean / Median Surface

| cycles \ steps | 1 TM / lDDT | 2 TM / lDDT | 5 TM / lDDT |
| --- | ---: | ---: | ---: |
| 1 | 0.8809 / 0.8181 | 0.8816 / 0.8285 | 0.8794 / 0.8197 |
| 2 | 0.8933 / 0.8358 | 0.8944 / 0.8446 | 0.8894 / 0.8367 |
| 4 | 0.9029 / 0.8465 | 0.9009 / 0.8529 | 0.8990 / 0.8458 |

Values are mean `Kabsch TM-style score Cα / all-atom lDDT`; full quantiles, CA-lDDT, backbone RMSD, sidechain RMSD, and per-group counts are in the JSON artifact.

## Paired Degradation vs `c4_s5`

| setting | common | median ΔTM | P(ΔTM < -0.05) | P(ΔTM < -0.10) | median Δall-atom lDDT |
| --- | ---: | ---: | ---: | ---: | ---: |
| c1_s1 | 1024 | -0.0051 | 0.115 | 0.066 | -0.0213 |
| c1_s2 | 1024 | -0.0039 | 0.116 | 0.065 | -0.0117 |
| c1_s5 | 1024 | -0.0066 | 0.151 | 0.056 | -0.0206 |
| c2_s1 | 1024 | -0.0010 | 0.074 | 0.030 | -0.0053 |
| c2_s2 | 1024 | 0.0002 | 0.069 | 0.026 | 0.0012 |
| c2_s5 | 1024 | -0.0019 | 0.088 | 0.045 | -0.0054 |
| c4_s1 | 1024 | 0.0011 | 0.024 | 0.011 | 0.0018 |
| c4_s2 | 1024 | 0.0014 | 0.044 | 0.015 | 0.0062 |
| c4_s5 | 1024 | 0.0000 | 0.000 | 0.000 | 0.0000 |

This is a collapse-surface diagnostic, not a final benchmark: the dev view was used to select operating points, and the frozen temporal test remains untouched.

The main observed effect is cycle depth. Mean Cα TM-style score rises from
about 0.881 at one cycle to 0.899--0.903 at four cycles. Within a fixed cycle,
additional structure steps are not monotonic on this dev view; `c4_s1` and
`c4_s2` are at least as strong as `c4_s5` on the aggregate metrics. Therefore
the current evidence supports prioritizing recycle/trunk collapse and internal
structure-module profiling before committing to a MeanFlow-specific method.
