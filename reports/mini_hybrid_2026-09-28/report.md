# Hybrid mutation / segmented derivative pilot

Locked protocol; no model training. New seeds211(selection)/223(confirmation). Six S1 proposal targets and two S2 derivative-only references.

Each cell below is the original fixed unit-direction FD gate result, not proof of an autograd bug. Low directional signal and perturbation scaling must be considered. Coordinate FP64 tests only the coordinate-to-loss segment, never the full folding model.

| Case | Steps | Coordinate old32/64 | Coordinate new32/64 | Conditioning old/new | Sequence old/new |
|---|---:|---|---|---|---|
| initial100_s1 | 1 | pass/pass | pass/pass | pass/fail | pass/pass |
| 8bzn_s1 | 1 | pass/pass | pass/pass | fail/fail | pass/pass |
| control_s1 | 1 | pass/pass | pass/pass | pass/fail | fail/pass |
| 9qr4_s1 | 1 | pass/pass | pass/pass | pass/pass | pass/fail |
| confirmation1_s1 | 1 | pass/pass | pass/pass | fail/fail | pass/pass |
| confirmation2_s1 | 1 | pass/pass | pass/pass | fail/fail | pass/fail |
| 8bzn_s2 | 2 | pass/pass | pass/pass | pass/fail | pass/pass |
| control_s2 | 2 | pass/pass | pass/pass | pass/fail | fail/fail |

## Equal-budget hard proposals

Geometry acceptance is conjunctive: task gains cannot compensate for failed absolute or nonregression geometry limits. These are conservative pilot limits, not universal chemical standards. No thresholds were relaxed after observing results.

| Case | Panel | Baseline geometry valid211/223 | Arm | Task improves211 | Geometry valid211 | Joint accepted211 | Confirmed223 |
|---|---|---|---|---:|---:|---:|---:|
| initial100_s1 | development | fail/fail | gradient | 1/8 | 0/8 | 0/8 | 0/8 |
| initial100_s1 | development | fail/fail | random | 6/8 | 0/8 | 0/8 | 0/8 |
| 8bzn_s1 | development | fail/fail | gradient | 7/8 | 0/8 | 0/8 | 0/8 |
| 8bzn_s1 | development | fail/fail | random | 6/8 | 0/8 | 0/8 | 0/8 |
| control_s1 | development | fail/fail | gradient | 3/8 | 0/8 | 0/8 | 0/8 |
| control_s1 | development | fail/fail | random | 2/8 | 0/8 | 0/8 | 0/8 |
| 9qr4_s1 | development | fail/fail | gradient | 5/8 | 0/8 | 0/8 | 0/8 |
| 9qr4_s1 | development | fail/fail | random | 3/8 | 0/8 | 0/8 | 0/8 |
| confirmation1_s1 | new_objective_confirmation | fail/fail | gradient | 7/8 | 0/8 | 0/8 | 0/8 |
| confirmation1_s1 | new_objective_confirmation | fail/fail | random | 4/8 | 0/8 | 0/8 | 0/8 |
| confirmation2_s1 | new_objective_confirmation | fail/fail | gradient | 0/8 | 0/8 | 0/8 | 0/8 |
| confirmation2_s1 | new_objective_confirmation | fail/fail | random | 2/8 | 0/8 | 0/8 | 0/8 |

Reasons can overlap; rejection counts: `{"bond_rmse_absolute": 64, "bond_rmse_regression": 32, "chirality_absolute": 30, "chirality_regression": 22, "max_penetration_absolute": 96, "max_penetration_regression": 38, "no_task_improvement": 50, "peptide_mae_absolute": 57, "peptide_mae_regression": 37, "severe_pairs_per_atom_absolute": 36, "severe_pairs_per_atom_regression": 30}`.

If the baseline and all candidates violate absolute geometry constraints, this pilot does not establish whether gradient proposals are superior on a valid design starting point. Zero joint acceptance is not evidence that gradients are useless. Task-only gains remain diagnostic, not design successes.

Old8BZN/control collapse regressions were rescored with graph-distance≤3 exclusions and all rejected. Raw severe counts therefore differ from the earlier direct-bond-only metric; compare new-policy baseline and candidate values within the same report.

The two confirmation targets were selected before candidate results and near-duplicate filtered, but originate from existing development data. They are new-to-this-objective confirmations, not a frozen temporal/homology-independent test.

## Additional relative-scale conditioning FD: 8bzn

Three Gaussian directions scaled separately by the RMS of s_inputs,s,z; original unit-direction outcomes are unchanged. Same5% relative+1e-6 absolute criterion, with relative h=.03,.01,.003,.001,.0003. This is a numerical diagnostic, not acceptance-rule retuning.

Old objective: pass. New objective: fail.

## Additional relative-scale conditioning FD: control

Three Gaussian directions scaled separately by the RMS of s_inputs,s,z; original unit-direction outcomes are unchanged. Same5% relative+1e-6 absolute criterion, with relative h=.03,.01,.003,.001,.0003. This is a numerical diagnostic, not acceptance-rule retuning.

Old objective: fail. New objective: fail.
