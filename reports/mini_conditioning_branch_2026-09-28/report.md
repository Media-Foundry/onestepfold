# Conditioning branch / objective backtrace

No model, objective weights or deployment thresholds changed. Existing control and8BZN only; no sequence optimization or temporal test. All folding calls FP32. Original failed gates remain archived.

## Replay guard attribution

First four jobs stopped at a guard that compared packed-gradient inputs against an original no-grad tuple. The follow-up layout audit holds these factors apart. Packed grad/no-grad/repeated forwards are exactly equal; original grad/no-grad also match. Original and packed inputs have identical values/shapes/strides, but different storage arrangements and slightly different outputs. This establishes packing sensitivity, not random execution or a backward defect; a specific kernel has not been identified. v2 fixes the guard to compare packed inputs on both sides, retaining exact equality.

## Per-branch random-direction checks

Three original Gaussian directions are restricted to each branch, retaining their original RMS scale. An additional gradient-aligned direction is labelled separately and never substitutes for random-direction gates. Each pass requires two adjacent h values under the unchanged 5%+1e-6 criterion.

| Target / branch | Objective | Linearized FD random | Objective FD random | Aligned linear / objective |
|---|---|---:|---:|---|
| control_s_inputs | old | 2/3 | 2/3 | True / True |
| control_s_inputs | new | 0/3 | 0/3 | True / True |
| control_s_inputs | contact | 3/3 | 3/3 | True / True |
| control_s_inputs | ca_clash | 3/3 | 3/3 | True / True |
| control_s_inputs | ca_chain | 2/3 | 2/3 | True / True |
| control_s_inputs | bond | 0/3 | 0/3 | True / True |
| control_s_inputs | peptide | 0/3 | 0/3 | True / True |
| control_s_inputs | clash | 1/3 | 1/3 | True / True |
| control_s_inputs | chirality | 3/3 | 3/3 | True / True |
| control_s | old | 1/3 | 1/3 | True / False |
| control_s | new | 2/3 | 2/3 | True / False |
| control_s | contact | 3/3 | 3/3 | True / True |
| control_s | ca_clash | 3/3 | 3/3 | True / False |
| control_s | ca_chain | 3/3 | 3/3 | True / True |
| control_s | bond | 2/3 | 2/3 | True / True |
| control_s | peptide | 3/3 | 3/3 | True / True |
| control_s | clash | 3/3 | 2/3 | True / False |
| control_s | chirality | 3/3 | 3/3 | True / False |
| control_z | old | 2/3 | 2/3 | True / False |
| control_z | new | 2/3 | 2/3 | True / False |
| control_z | contact | 3/3 | 3/3 | True / False |
| control_z | ca_clash | 3/3 | 3/3 | True / False |
| control_z | ca_chain | 2/3 | 2/3 | True / True |
| control_z | bond | 2/3 | 2/3 | True / False |
| control_z | peptide | 2/3 | 2/3 | True / False |
| control_z | clash | 3/3 | 3/3 | True / False |
| control_z | chirality | 3/3 | 3/3 | True / False |
| 8bzn_all | old | 3/3 | 3/3 | True / False |
| 8bzn_all | new | 3/3 | 1/3 | True / False |
| 8bzn_all | contact | 3/3 | 3/3 | True / True |
| 8bzn_all | ca_clash | 3/3 | 3/3 | True / False |
| 8bzn_all | ca_chain | 3/3 | 3/3 | True / False |
| 8bzn_all | bond | 3/3 | 3/3 | True / False |
| 8bzn_all | peptide | 3/3 | 3/3 | True / False |
| 8bzn_all | clash | 3/3 | 2/3 | True / False |
| 8bzn_all | chirality | 3/3 | 3/3 | False / False |

## Cross-branch cancellation

The three isolated derivatives sum back to the previous mixed derivative within 1e-6+1e-4 relative tolerance. Ratios below describe cancellation between branches, not a condition-number bound.

| Direction | Objective | s_inputs | s | z | Sum | Sum abs / abs sum |
|---:|---|---:|---:|---:|---:|---:|
| 0 | old | -0.0001219326 | -0.0003456239 | 0.0001597672 | -0.0003077892 | 2.04 |
| 0 | new | 0.0009936828 | -0.1421728 | -0.001456995 | -0.1426361 | 1.01 |
| 1 | old | -0.0002323881 | 0.04123738 | 0.00290217 | 0.04390716 | 1.01 |
| 1 | new | 0.001141152 | 0.006621029 | -0.01342162 | -0.005659444 | 3.74 |
| 2 | old | 2.123369e-05 | -0.0003069233 | 0.003748122 | 0.003462433 | 1.18 |
| 2 | new | 0.00134572 | -0.2137267 | -0.02073416 | -0.2331151 | 1.01 |

## Numerical detail

Per-term analytic/linearized/nonlinear responses, absolute dot-product sums, h scans and pointer alignment are retained in JSON. These are local conditioning tests; they do not certify end-to-end sequence derivatives or cross-graph mutations. Zero-signal terms passing absolute tolerance are not positive gradient evidence. The helper decomposition is tested against original total values and coordinate gradients.

## Localized clash mechanism

This is the soft chart at softmax(4×onehot): native amino-acid probability≈0.742 at every position, before optimization. It is not the native hard prediction. Atom inventory and identity-keyed initial noise211 are fixed.

HIS42-CE1 / THR43-OG1 distance: soft chart 0.031421 Å, archived native hard seed211 6.266585 Å. The latter is a matched atom/noise comparison, not an experimental GT distance.

| h | Pair contribution to clash remainder | Total clash remainder | Signed fraction | Hinge active at base/plus/minus |
|---:|---:|---:|---:|---|
| 0.003 | -0.0533945 | -0.0719804 | 74.2% | True/True/True |
| 0.001 | -0.0252630 | -0.0279258 | 90.5% | True/True/True |

The dominant pair never crosses the hinge threshold in this test. Its near-zero separation makes the distance response strongly nonlinear at these finite perturbations. Other pairs do cross the hinge; this is not a claim that all hinge effects vanish. Pair attribution recomputes distances in FP64 from saved FP32 coordinates; it is not FP64 model inference.

At h=.003, all-atom clash accounts for99.6% of the total new-objective nonlinear-minus-linearized remainder. The dominant pair alone accounts for74.2% of the clash remainder; at h=.001 this rises to90.5%. These are signed remainder ratios for the selected failing direction, not population estimates.

## Updated conclusion

The current soft input already produces a severely overlapping state before any sequence optimization. Together with the nonzero, reproducible branch derivatives, this supports investigating the soft input interpolation and geometry objective before altering diffusion weights. It does not certify all derivatives: control random-direction checks still fail, with smaller signals degrading as h shrinks. Its three branch derivatives add back to the prior mixed derivative; new-objective direction1 also has3.74× cross-branch cancellation.

All three control branches pass the new-objective linearized check on the separately labelled gradient-aligned direction. The nonlinear objective still fails there for s and z, so this is not a usable optimizer gate or proof that simply following the gradient is safe.

Next proposed bounded experiment: measure hard-neighborhood input interpolation (and individual ESM/reference-feature paths) against native geometry, keeping graph and noise fixed. Any change to distance regularization should be an explicit ablation, retaining hard physical-geometry acceptance. Do not equate a smoother loss with chemically valid structures. No such new experiment or model training has been launched in this batch.
