# Stage 0C Paired Analysis

Paired deltas use the same 1,024 targets for each setting and the `c4_s5` output as anchor. Bootstrap intervals resample targets, not individual atoms.

## Key Paired Risks

| setting | metric | mean delta | bootstrap 95% CI | median delta | below -0.05 | below -0.10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| c1_s1 | tm_score_ca | -0.0181 | [-0.0222, -0.0142] | -0.0051 | 0.115 | 0.066 |
| c1_s1 | all_atom_lddt | -0.0277 | [-0.0298, -0.0258] | -0.0213 | 0.180 | 0.041 |
| c1_s5 | tm_score_ca | -0.0196 | [-0.0237, -0.0157] | -0.0066 | 0.151 | 0.056 |
| c1_s5 | all_atom_lddt | -0.0261 | [-0.0280, -0.0243] | -0.0207 | 0.153 | 0.024 |
| c2_s2 | tm_score_ca | -0.0047 | [-0.0080, -0.0016] | 0.0002 | 0.069 | 0.026 |
| c2_s2 | all_atom_lddt | -0.0012 | [-0.0023, -0.0002] | 0.0012 | 0.014 | 0.004 |
| c4_s1 | tm_score_ca | 0.0039 | [0.0017, 0.0060] | 0.0011 | 0.024 | 0.011 |
| c4_s1 | all_atom_lddt | 0.0007 | [-0.0004, 0.0017] | 0.0018 | 0.014 | 0.003 |
| c4_s2 | tm_score_ca | 0.0019 | [-0.0008, 0.0045] | 0.0014 | 0.044 | 0.015 |
| c4_s2 | all_atom_lddt | 0.0071 | [0.0065, 0.0077] | 0.0062 | 0.002 | 0.000 |

## `c1_s1` Hard Tail

Definition: fixed-correspondence TM-style delta versus `c4_s5` < -0.05. The tail contains 118 targets; the comparison set contains 906.

| subset | median length | median resolution | multi-record groups | apo-like |
| --- | ---: | ---: | ---: | ---: |
| tail | 369.5 | 2.00 | 26 | 37 |
| non-tail | 281.0 | 1.80 | 239 | 204 |

This is a diagnostic on the temporal dev view; it is not used to tune or report the frozen temporal test.

The hard-tail summaries are descriptive only. The `c1_s1` tail is longer and
slightly lower-resolution on this dev sample, but this does not establish a
causal predictor of recycle difficulty; it motivates testing internal
representation change and confidence signals next.
