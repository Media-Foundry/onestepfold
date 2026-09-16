# Stage 0D Oracle Recycle Frontier

temporal_dev_v1 only; frozen temporal test was not read.

Oracle points use experimental GT to select the shallowest acceptable setting. They are an unattainable upper bound, not a router result. Mean-cycle savings assume intermediate recycle states are reused rather than recomputed.

## Fixed Baselines

| setting | mean cycles | mean TM | mean delta TM vs c4_s5 | P(delta TM < -0.05) | mean all-atom lDDT |
| --- | ---: | ---: | ---: | ---: | ---: |
| c1_s1 | 1.000 | 0.8809 | -0.0181 | 0.115 | 0.8181 |
| c2_s2 | 2.000 | 0.8944 | -0.0047 | 0.069 | 0.8446 |
| c4_s5 | 4.000 | 0.8990 | 0.0000 | 0.000 | 0.8458 |

## `practical_1_or_4`

Choose c1_s1 or c4_s5 against the c4_s5 anchor.

| quality tolerance | protected metrics | c1 / c2 / c4 (%) | mean cycles | cycle reduction vs c4 | mean steps | mean delta TM | P(delta TM < -0.05) | mean delta all-atom lDDT |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.005 | tm_score_ca | 49.6/0.0/50.4 | 2.512 | 37.2% | 3.016 | 0.0064 | 0.000 | -0.0050 |
| 0.010 | tm_score_ca | 61.3/0.0/38.7 | 2.160 | 46.0% | 2.547 | 0.0056 | 0.000 | -0.0083 |
| 0.020 | tm_score_ca | 75.1/0.0/24.9 | 1.747 | 56.3% | 1.996 | 0.0036 | 0.000 | -0.0129 |
| 0.030 | tm_score_ca | 81.4/0.0/18.6 | 1.557 | 61.1% | 1.742 | 0.0020 | 0.000 | -0.0157 |
| 0.050 | tm_score_ca | 88.5/0.0/11.5 | 1.346 | 66.4% | 1.461 | -0.0007 | 0.000 | -0.0192 |

## `practical_1_2_4`

Choose c1_s1, c2_s2, or c4_s5 against the c4_s5 anchor.

| quality tolerance | protected metrics | c1 / c2 / c4 (%) | mean cycles | cycle reduction vs c4 | mean steps | mean delta TM | P(delta TM < -0.05) | mean delta all-atom lDDT |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.005 | tm_score_ca | 49.6/27.1/23.2 | 1.969 | 50.8% | 2.201 | 0.0075 | 0.000 | -0.0052 |
| 0.010 | tm_score_ca | 61.3/22.1/16.6 | 1.719 | 57.0% | 1.885 | 0.0063 | 0.000 | -0.0089 |
| 0.020 | tm_score_ca | 75.1/14.9/10.0 | 1.448 | 63.8% | 1.548 | 0.0037 | 0.000 | -0.0138 |
| 0.030 | tm_score_ca | 81.4/11.3/7.2 | 1.330 | 66.7% | 1.402 | 0.0019 | 0.000 | -0.0165 |
| 0.050 | tm_score_ca | 88.5/6.7/4.8 | 1.211 | 69.7% | 1.259 | -0.0010 | 0.000 | -0.0198 |

## `practical_joint_1_2_4`

Choose c1_s1, c2_s2, or c4_s5 while protecting both TM-style score and all-atom lDDT against the c4_s5 anchor.

| quality tolerance | protected metrics | c1 / c2 / c4 (%) | mean cycles | cycle reduction vs c4 | mean steps | mean delta TM | P(delta TM < -0.05) | mean delta all-atom lDDT |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.005 | tm_score_ca, all_atom_lddt | 20.9/42.9/36.2 | 2.516 | 37.1% | 2.878 | 0.0071 | 0.000 | 0.0027 |
| 0.010 | tm_score_ca, all_atom_lddt | 29.6/44.0/26.4 | 2.231 | 44.2% | 2.495 | 0.0067 | 0.000 | 0.0012 |
| 0.020 | tm_score_ca, all_atom_lddt | 44.4/41.0/14.6 | 1.847 | 53.8% | 1.992 | 0.0058 | 0.000 | -0.0024 |
| 0.030 | tm_score_ca, all_atom_lddt | 60.3/29.6/10.2 | 1.601 | 60.0% | 1.702 | 0.0041 | 0.000 | -0.0069 |
| 0.050 | tm_score_ca, all_atom_lddt | 78.1/15.9/6.0 | 1.338 | 66.6% | 1.397 | 0.0006 | 0.000 | -0.0134 |

## `step1_recycle_only_1_2_4`

Hold structure steps at one and choose c1_s1, c2_s1, or c4_s1 against c4_s1.

| quality tolerance | protected metrics | c1 / c2 / c4 (%) | mean cycles | cycle reduction vs c4 | mean steps | mean delta TM | P(delta TM < -0.05) | mean delta all-atom lDDT |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.005 | tm_score_ca | 43.1/24.9/32.0 | 2.210 | 44.8% | 1.000 | 0.0052 | 0.000 | -0.0054 |
| 0.010 | tm_score_ca | 58.8/21.4/19.8 | 1.809 | 54.8% | 1.000 | 0.0035 | 0.000 | -0.0100 |
| 0.020 | tm_score_ca | 72.8/15.4/11.8 | 1.509 | 62.3% | 1.000 | 0.0009 | 0.000 | -0.0146 |
| 0.030 | tm_score_ca | 79.9/10.5/9.6 | 1.393 | 65.2% | 1.000 | -0.0009 | 0.000 | -0.0171 |
| 0.050 | tm_score_ca | 87.7/6.9/5.4 | 1.230 | 69.2% | 1.000 | -0.0044 | 0.000 | -0.0209 |

## `step1_joint_recycle_only_1_2_4`

Hold structure steps at one and protect both TM-style score and all-atom lDDT against c4_s1.

| quality tolerance | protected metrics | c1 / c2 / c4 (%) | mean cycles | cycle reduction vs c4 | mean steps | mean delta TM | P(delta TM < -0.05) | mean delta all-atom lDDT |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.005 | tm_score_ca, all_atom_lddt | 17.9/24.6/57.5 | 2.972 | 25.7% | 1.000 | 0.0042 | 0.000 | 0.0015 |
| 0.010 | tm_score_ca, all_atom_lddt | 26.6/31.7/41.7 | 2.568 | 35.8% | 1.000 | 0.0040 | 0.000 | -0.0000 |
| 0.020 | tm_score_ca, all_atom_lddt | 42.6/34.2/23.2 | 2.039 | 49.0% | 1.000 | 0.0028 | 0.000 | -0.0041 |
| 0.030 | tm_score_ca, all_atom_lddt | 57.6/27.8/14.6 | 1.715 | 57.1% | 1.000 | 0.0014 | 0.000 | -0.0083 |
| 0.050 | tm_score_ca, all_atom_lddt | 76.7/16.2/7.1 | 1.376 | 65.6% | 1.000 | -0.0022 | 0.000 | -0.0148 |

The `practical` frontier mixes cycle and structure-step settings and therefore measures the best existing operating path, not a pure recycle effect. The `step1_recycle_only` frontier holds structure NFE at one and uses `c4_s1` as its anchor.
