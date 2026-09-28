# Near-hard full ERC logits gradient gate

Existing development cases only:8BZN/control, alpha1e-4/1e-3, C4/S1 or S2, native fixed chemical graph, identity-keyed noise211, FP32. Exact hard is a replay/chemistry reference, not a central-difference point. Every q±hv recomputes live ESM and all input-dependent conditioning/caches. No training, optimization, source-combination expansion or loss smoothing.

Original random directions remain in logits space:seed731, Gaussian L×20, per-residue shift removed, global norm1; h=.3,.1,.03,.01,.003. Original gate:5%+1e-6, two adjacent h for every direction, finite nonzero and exactly repeated gradient. Actual q is FP32 log of intended interior probabilities, with softmax(q) fed to the model.

Informative is a separate conservative annotation: original tolerance pass, relative-only pass, nonzero loss/probability/coordinate response, and relative tolerance term larger than absolute (max(|AD|,|FD|)>2e-5), again at adjacent h in every direction. Low-signal/absolute-assisted passing rows remain original passes, not positive derivative evidence. This crossover is not a measured hardware noise bound.

## Original and signal-aware gates

Each count below is passing random directions out of3. A complete gate additionally checks gradient finiteness/nonzero/repeatability. The new objective retains its .01KL(p||p0) term; coordinate linearization includes the direct KL derivative.

| Arm | Objective | Nonlinear FD | Linearized FD | Informative nonlinear | Original gate | Signal label |
|---|---|---:|---:|---:|---|---|
| 8bzn_a0_s1 | old | 3/3 | 3/3 | 0/3 | True | pass_low_signal_or_absolute_tolerance_assisted |
| 8bzn_a0_s1 | new | 0/3 | 0/3 | 0/3 | False | fail |
| 8bzn_a0_s2 | old | 1/3 | 1/3 | 0/3 | False | fail |
| 8bzn_a0_s2 | new | 0/3 | 0/3 | 0/3 | False | fail |
| 8bzn_a1_s1 | old | 2/3 | 2/3 | 0/3 | False | fail |
| 8bzn_a1_s1 | new | 0/3 | 0/3 | 0/3 | False | fail |
| 8bzn_a1_s2 | old | 3/3 | 3/3 | 0/3 | True | pass_low_signal_or_absolute_tolerance_assisted |
| 8bzn_a1_s2 | new | 1/3 | 1/3 | 0/3 | False | fail |
| control_a0_s1 | old | 1/3 | 1/3 | 0/3 | False | fail |
| control_a0_s1 | new | 0/3 | 0/3 | 0/3 | False | fail |
| control_a0_s2 | old | 1/3 | 1/3 | 0/3 | False | fail |
| control_a0_s2 | new | 0/3 | 0/3 | 0/3 | False | fail |
| control_a1_s1 | old | 0/3 | 0/3 | 0/3 | False | fail |
| control_a1_s1 | new | 0/3 | 0/3 | 0/3 | False | fail |
| control_a1_s2 | old | 0/3 | 0/3 | 0/3 | False | fail |
| control_a1_s2 | new | 0/3 | 0/3 | 0/3 | False | fail |

## Geometry relative to same-sampler hard baseline

Absolute and nonregression requirements remain unchanged. A hard baseline failing chemistry is not exempted, and small displacement does not establish a usable design state.

| Arm | Hard/near severe pairs | Hard/near max penetration Å | Hard/near bond RMSE Å | Hard/near peptide MAE Å | Near chemistry gate | CA displacement Å |
|---|---|---|---|---|---|---:|
| 8bzn_a0_s1 | 8 / 8 | 2.8206 / 2.8304 | 0.28777 / 0.28789 | 0.17984 / 0.17988 | False | 0.0029805 |
| 8bzn_a0_s2 | 7 / 7 | 2.8431 / 2.8436 | 0.2862 / 0.28627 | 0.13583 / 0.13585 | False | 0.00275282 |
| 8bzn_a1_s1 | 8 / 8 | 2.8206 / 2.9095 | 0.28777 / 0.28895 | 0.17984 / 0.1802 | False | 0.0300737 |
| 8bzn_a1_s2 | 7 / 10 | 2.8431 / 2.8479 | 0.2862 / 0.28694 | 0.13583 / 0.13598 | False | 0.0277429 |
| control_a0_s1 | 19 / 19 | 3.2284 / 3.2499 | 0.23665 / 0.23665 | 0.12795 / 0.12778 | False | 0.0129477 |
| control_a0_s2 | 26 / 23 | 3.1255 / 3.1348 | 0.24598 / 0.2453 | 0.11758 / 0.11686 | False | 0.0329375 |
| control_a1_s1 | 19 / 19 | 3.2284 / 3.0417 | 0.23665 / 0.24173 | 0.12795 / 0.12849 | False | 0.156589 |
| control_a1_s2 | 26 / 25 | 3.1255 / 2.9835 | 0.24598 / 0.24159 | 0.11758 / 0.11326 | False | 0.299139 |

## Magnitudes and replay

Ranges cover all original random-direction h rows for the new objective; signs and individual numerators are retained in JSON. No direction or h is substituted after observing the results.

| Arm | abs(AD) range | abs(loss numerator) range | Probability delta norm range | Coordinate delta norm range | Grad/no-grad exact | Repeated gradient max error |
|---|---|---|---|---|---|---|
| 8bzn_a0_s1 | 1.06e-07–1.33e-06 | 1.7e-07–3.21e-06 | 3.4e-07–1.59e-05 | 0.000685–0.00163 | True | 0 |
| 8bzn_a0_s2 | 1.82e-07–3.63e-07 | 7.97e-09–3.2e-06 | 3.4e-07–1.59e-05 | 0.000733–0.00146 | True | 0 |
| 8bzn_a1_s1 | 8.79e-07–1.35e-05 | 2.33e-07–1.16e-05 | 1.53e-06–0.00016 | 0.00083–0.008 | True | 0 |
| 8bzn_a1_s2 | 1.44e-06–4.35e-06 | 2.87e-07–4.91e-06 | 1.53e-06–0.00016 | 0.000697–0.00681 | True | 0 |
| control_a0_s1 | 3.35e-07–1.14e-06 | 2.72e-07–1.85e-05 | 2.96e-07–1.52e-05 | 0.00412–0.09 | True | 0 |
| control_a0_s2 | 9.18e-07–6.17e-06 | 1.47e-06–7.75e-05 | 2.96e-07–1.52e-05 | 0.00383–0.117 | True | 0 |
| control_a1_s1 | 1.58e-05–0.000102 | 1.89e-05–0.000123 | 1.76e-06–0.000153 | 0.0262–0.178 | True | 0 |
| control_a1_s2 | 4.27e-06–3.16e-05 | 7.34e-06–4.47e-05 | 1.76e-06–0.000153 | 0.0334–0.222 | True | 0 |

Input traces (token mixture→ESM→projected ESM→s_inputs), all geometry metrics including chirality, gradients, probabilities and coordinates are archived per arm. CPU loss/geometry replay validates artifacts but never replaces recorded GPU values when computing the original FD verdict. A passing numerical gate on these fixed graphs would not certify cross-argmax transitions, hard-mutation utility or a globally continuous oracle.
