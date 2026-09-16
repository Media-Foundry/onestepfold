# Stage 0D Predictive Recycling

Scope: temporal_dev_v1 only; frozen temporal test was not read.

The clean recycle label contains 126/1024 targets (12.3%) with `c1_s1` TM-style degradation greater than 0.05 relative to `c4_s1`.

Five-fold OOF predictions group 784 nearest-train-sequence proxies; this is a homology-aware proxy split, not a frozen family-cluster benchmark.

## Fixed Baselines

| setting | cycles | mean delta TM | catastrophic TM risk | mean delta all-atom lDDT | joint catastrophic risk |
| --- | ---: | ---: | ---: | ---: | ---: |
| c1_s1 | 1.0 | -0.0220 | 0.123 | -0.0284 | 0.233 |
| c2_s1 | 2.0 | -0.0095 | 0.070 | -0.0107 | 0.093 |
| c2_s2 | 2.0 | -0.0085 | 0.067 | -0.0019 | 0.076 |
| c4_s1 | 4.0 | 0.0000 | 0.000 | 0.0000 | 0.000 |

## Predictability

| policy | availability | AUROC | average precision |
| --- | --- | ---: | ---: |
| logistic_tier_a_sequence | cycle_1 | 0.625 | 0.225 |
| hist_gradient_boosting_tier_a_sequence | cycle_1 | 0.632 | 0.261 |
| logistic_tier_ab_confidence | cycle_1 | 0.870 | 0.466 |
| hist_gradient_boosting_tier_ab_confidence | cycle_1 | 0.881 | 0.433 |
| logistic_tier_ab_confidence_geometry | cycle_1 | 0.871 | 0.497 |
| hist_gradient_boosting_tier_ab_confidence_geometry | cycle_1 | 0.885 | 0.460 |
| logistic_tier_ab_confidence_internal | cycle_1 | 0.876 | 0.484 |
| hist_gradient_boosting_tier_ab_confidence_internal | cycle_1 | 0.895 | 0.477 |
| logistic_tier_ab_confidence_geometry_internal | cycle_1 | 0.871 | 0.503 |
| hist_gradient_boosting_tier_ab_confidence_geometry_internal | cycle_1 | 0.892 | 0.467 |
| length_threshold | cycle_1 | 0.605 | 0.269 |
| confidence_ptm_threshold | cycle_1 | 0.899 | 0.436 |
| oracle_c1_hardness | oracle | 1.000 | 1.000 |
| af_style_distance_convergence | after_cycle_2 | 0.906 | 0.491 |

## Minimum Compute At TM Catastrophic Risk <= 1%

| policy | mean cycles | routed deep | mean delta TM | mean delta all-atom lDDT |
| --- | ---: | ---: | ---: | ---: |
| logistic_tier_a_sequence | 3.848 | 94.9% | -0.0011 | -0.0013 |
| hist_gradient_boosting_tier_a_sequence | 3.742 | 91.4% | -0.0011 | -0.0018 |
| logistic_tier_ab_confidence | 2.400 | 46.7% | -0.0035 | -0.0089 |
| hist_gradient_boosting_tier_ab_confidence | 2.066 | 35.5% | -0.0040 | -0.0128 |
| logistic_tier_ab_confidence_geometry | 2.312 | 43.8% | -0.0037 | -0.0097 |
| hist_gradient_boosting_tier_ab_confidence_geometry | 2.140 | 38.0% | -0.0045 | -0.0124 |
| logistic_tier_ab_confidence_internal | 2.310 | 43.7% | -0.0036 | -0.0101 |
| hist_gradient_boosting_tier_ab_confidence_internal | 2.031 | 34.4% | -0.0044 | -0.0135 |
| logistic_tier_ab_confidence_geometry_internal | 2.415 | 47.2% | -0.0037 | -0.0093 |
| hist_gradient_boosting_tier_ab_confidence_geometry_internal | 2.055 | 35.2% | -0.0042 | -0.0132 |
| length_threshold | 3.789 | 93.0% | -0.0016 | -0.0015 |
| confidence_ptm_threshold | 2.102 | 36.7% | -0.0044 | -0.0133 |
| oracle_c1_hardness | 1.340 | 11.3% | -0.0042 | -0.0200 |
| af_style_distance_convergence | 2.465 | 23.2% | -0.0024 | -0.0061 |

## Minimum Compute At TM Catastrophic Risk <= 2%

| policy | mean cycles | routed deep | mean delta TM | mean delta all-atom lDDT |
| --- | ---: | ---: | ---: | ---: |
| logistic_tier_a_sequence | 3.458 | 81.9% | -0.0027 | -0.0039 |
| hist_gradient_boosting_tier_a_sequence | 3.350 | 78.3% | -0.0028 | -0.0046 |
| logistic_tier_ab_confidence | 1.870 | 29.0% | -0.0056 | -0.0143 |
| hist_gradient_boosting_tier_ab_confidence | 1.899 | 30.0% | -0.0054 | -0.0148 |
| logistic_tier_ab_confidence_geometry | 1.958 | 31.9% | -0.0059 | -0.0135 |
| hist_gradient_boosting_tier_ab_confidence_geometry | 1.938 | 31.2% | -0.0051 | -0.0143 |
| logistic_tier_ab_confidence_internal | 1.923 | 30.8% | -0.0062 | -0.0139 |
| hist_gradient_boosting_tier_ab_confidence_internal | 1.835 | 27.8% | -0.0058 | -0.0152 |
| logistic_tier_ab_confidence_geometry_internal | 1.996 | 33.2% | -0.0058 | -0.0130 |
| hist_gradient_boosting_tier_ab_confidence_geometry_internal | 1.832 | 27.7% | -0.0058 | -0.0152 |
| length_threshold | 3.490 | 83.0% | -0.0029 | -0.0030 |
| confidence_ptm_threshold | 1.779 | 26.0% | -0.0066 | -0.0170 |
| oracle_c1_hardness | 1.311 | 10.4% | -0.0047 | -0.0206 |
| af_style_distance_convergence | 2.320 | 16.0% | -0.0034 | -0.0072 |

## Minimum Compute At Joint TM/All-Atom Catastrophic Risk <= 1%

| policy | mean cycles | routed deep | mean delta TM | mean delta all-atom lDDT |
| --- | ---: | ---: | ---: | ---: |
| logistic_tier_a_sequence | 3.883 | 96.1% | -0.0009 | -0.0011 |
| hist_gradient_boosting_tier_a_sequence | 3.792 | 93.1% | -0.0011 | -0.0015 |
| logistic_tier_ab_confidence | 3.229 | 74.3% | -0.0010 | -0.0029 |
| hist_gradient_boosting_tier_ab_confidence | 3.177 | 72.6% | -0.0012 | -0.0044 |
| logistic_tier_ab_confidence_geometry | 3.259 | 75.3% | -0.0009 | -0.0030 |
| hist_gradient_boosting_tier_ab_confidence_geometry | 3.358 | 78.6% | -0.0009 | -0.0033 |
| logistic_tier_ab_confidence_internal | 3.171 | 72.4% | -0.0013 | -0.0037 |
| hist_gradient_boosting_tier_ab_confidence_internal | 3.156 | 71.9% | -0.0013 | -0.0041 |
| logistic_tier_ab_confidence_geometry_internal | 3.171 | 72.4% | -0.0012 | -0.0035 |
| hist_gradient_boosting_tier_ab_confidence_geometry_internal | 3.338 | 77.9% | -0.0011 | -0.0033 |
| length_threshold | 3.812 | 93.8% | -0.0014 | -0.0013 |
| confidence_ptm_threshold | 3.367 | 78.9% | -0.0007 | -0.0031 |
| oracle_c1_hardness | 2.617 | 53.9% | 0.0041 | -0.0042 |
| af_style_distance_convergence | 2.920 | 46.0% | -0.0008 | -0.0030 |

## Minimum Compute At Joint TM/All-Atom Catastrophic Risk <= 2%

| policy | mean cycles | routed deep | mean delta TM | mean delta all-atom lDDT |
| --- | ---: | ---: | ---: | ---: |
| logistic_tier_a_sequence | 3.558 | 85.3% | -0.0017 | -0.0029 |
| hist_gradient_boosting_tier_a_sequence | 3.578 | 85.9% | -0.0017 | -0.0031 |
| logistic_tier_ab_confidence | 2.805 | 60.2% | -0.0021 | -0.0057 |
| hist_gradient_boosting_tier_ab_confidence | 2.802 | 60.1% | -0.0021 | -0.0066 |
| logistic_tier_ab_confidence_geometry | 2.849 | 61.6% | -0.0020 | -0.0057 |
| hist_gradient_boosting_tier_ab_confidence_geometry | 3.065 | 68.8% | -0.0015 | -0.0052 |
| logistic_tier_ab_confidence_internal | 2.796 | 59.9% | -0.0021 | -0.0062 |
| hist_gradient_boosting_tier_ab_confidence_internal | 2.878 | 62.6% | -0.0018 | -0.0062 |
| logistic_tier_ab_confidence_geometry_internal | 2.787 | 59.6% | -0.0023 | -0.0064 |
| hist_gradient_boosting_tier_ab_confidence_geometry_internal | 3.004 | 66.8% | -0.0017 | -0.0056 |
| length_threshold | 3.616 | 87.2% | -0.0025 | -0.0024 |
| confidence_ptm_threshold | 2.863 | 62.1% | -0.0017 | -0.0061 |
| oracle_c1_hardness | 2.216 | 40.5% | 0.0031 | -0.0078 |
| af_style_distance_convergence | 2.596 | 29.8% | -0.0021 | -0.0051 |

All learned results are out-of-fold diagnostics on `temporal_dev_v1`. Thresholds are swept on those OOF predictions, so the selected operating points are not frozen-test estimates.
