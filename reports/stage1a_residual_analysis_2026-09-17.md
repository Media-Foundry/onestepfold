# Stage 1A Recycle Residual Characterization

temporal_dev_v1 only; frozen temporal test was not read.

Records: 1024; joint hard targets: 76.
Only compact hook summaries are used; full Pairformer tensors are not stored.

## Residual Magnitudes

| transition | single Fro norm median | pair Fro norm median | pair spatial rank-8 energy median | local (<=8) energy median |
| --- | ---: | ---: | ---: | ---: |
| c1_to_c2 | 1374 | 2.607e+04 | 0.9918 | 0.1099 |
| c2_to_c3 | 665.2 | 1.483e+04 | 0.9924 | 0.1131 |
| c3_to_c4 | 494.9 | 1.061e+04 | 0.9927 | 0.1156 |

## Easy/Hard Comparison

| subgroup | count | transition | single norm median | pair norm median |
| --- | ---: | --- | ---: | ---: |
| hard_joint | 76 | c1_to_c2 | 1487 | 3.966e+04 |
| hard_joint | 76 | c2_to_c3 | 740.9 | 2.521e+04 |
| hard_joint | 76 | c3_to_c4 | 567.9 | 1.966e+04 |
| nonhard_joint | 948 | c1_to_c2 | 1364 | 2.571e+04 |
| nonhard_joint | 948 | c2_to_c3 | 654 | 1.449e+04 |
| nonhard_joint | 948 | c3_to_c4 | 487.3 | 1.006e+04 |

## Correlation With c2 All-Atom Degradation

| transition | single norm | pair norm | spatial rank-8 energy |
| --- | ---: | ---: | ---: |
| c2_to_c3 | -0.09557578444239119 | -0.3033339033456585 | -0.039324769965070124 |
| c3_to_c4 | -0.08870262049289648 | -0.33306631358150496 | -0.07040802334944138 |

Length-controlled correlations are reported in the JSON under `correlations_with_c2_all_atom_delta.*.length_controlled`; pair norm means and residue-normalized single norms are less sensitive to the raw L and L^2 scaling than Frobenius norms.
