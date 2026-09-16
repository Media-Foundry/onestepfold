# Stage 0E c2-to-c4 Predictive Recycling

temporal_dev_v1 only; frozen temporal test was not read.

The joint hard-target label contains 76/1024 targets.
All learned results are family-proxy grouped out-of-fold diagnostics; frozen temporal test was not read.
The c1_s1 to c2_s2 coordinate feature is a matched-setting proxy, not a saved intermediate structure from one c2 forward.
Risk-constrained thresholds are swept on the same OOF predictions for this dev diagnostic; they are not frozen-test estimates.

## Fixed Baselines

| policy | mean cycles | joint catastrophe risk | mean delta TM | mean delta all-atom lDDT |
| --- | ---: | ---: | ---: | ---: |
| c2_s2 | 2.000 | 0.074 | -0.0047 | -0.0012 |
| c4_s5 | 4.000 | 0.000 | 0.0000 | 0.0000 |

## Predictors

| policy | AUROC | average precision | joint-risk <=1% mean cycles | joint-risk <=1% deep fraction |
| --- | ---: | ---: | ---: | ---: |
| logistic_tier_a_sequence | 0.542 | 0.086 | 3.549 | 0.774 |
| hist_gradient_boosting_tier_a_sequence | 0.549 | 0.096 | 3.664 | 0.832 |
| logistic_tier_b_c2_confidence | 0.856 | 0.324 | 2.719 | 0.359 |
| hist_gradient_boosting_tier_b_c2_confidence | 0.864 | 0.245 | 2.465 | 0.232 |
| logistic_tier_b_c2_confidence_delta | 0.868 | 0.332 | 2.660 | 0.330 |
| hist_gradient_boosting_tier_b_c2_confidence_delta | 0.875 | 0.280 | 2.475 | 0.237 |
| logistic_tier_c_trajectory | 0.833 | 0.320 | 2.807 | 0.403 |
| hist_gradient_boosting_tier_c_trajectory | 0.885 | 0.305 | 2.477 | 0.238 |
| logistic_tier_c_trajectory_geometry | 0.827 | 0.331 | 2.857 | 0.429 |
| hist_gradient_boosting_tier_c_trajectory_geometry | 0.895 | 0.355 | 2.508 | 0.254 |
| reactive_c1_c2_distance | 0.873 | 0.401 | 2.551 | 0.275 |
| reactive_c1_s1_to_c2_s2_distance_proxy | 0.859 | 0.337 | 2.729 | 0.364 |

## Oracle

| joint-risk limit | mean cycles | deep fraction | catastrophe risk |
| ---: | ---: | ---: | ---: |
| 0.00 | 2.148 | 0.074 | 0.000 |
| 0.01 | 2.129 | 0.064 | 0.010 |
| 0.02 | 2.109 | 0.055 | 0.020 |
| 0.05 | 2.049 | 0.024 | 0.050 |
