# One-batch hard mutation utility: completed

The frozen batch was recovered after a DiamondHill host reboot. All99 hard
predictions completed successfully on GCD2–5; the controller then completed CPU
recomputation of99 saved coordinates, objective components and geometry scores.
Maximum CPU/GPU scalar discrepancy:2.38419e−7. Proposal ranking and probability/
logit chain audit were also reconstructed. No candidate, noise, threshold or
ranking changes were made during recovery. All jobs are finished; do not restart.

Protocol: [mini_hard_mutation_utility_v1.md](mini_hard_mutation_utility_v1.md).
Execution history: [status](mini_hard_mutation_utility_status_2026-09-28.md).

## Confirmation outcomes

Lower task delta is better. Each candidate's two confirmation-noise deltas are
averaged only to summarize its distribution; success requires BOTH noises to
pass individually. No best-of-noise selection.

| Proposals | Count | Mean task delta | Median task delta | Task+nonregression both | Full hard acceptance both |
|---|---:|---:|---:|---:|---:|
| Gradient | 16 | +0.00053495 | −0.00016116 | 1 | 0 |
| Random | 16 | +0.00278479 | +0.00096734 | 0 | 0 |

| Noise | Gradient task improvements / utility | Random task improvements / utility |
|---|---:|---:|
| 211 (proposal/development) | 7 / 4 | 4 / 1 |
| 200003 (confirmation) | 9 / 5 | 3 / 0 |
| 200009 (confirmation) | 7 / 1 | 6 / 0 |

Each denominator is16. Full hard acceptance is zero for every arm/noise.
All per-candidate losses, objective components and geometry, plus full delta
vectors and quantiles, are retained in the JSON report. Both arm means are
positive: the average evaluated mutation worsened this task. The gradient arm's
smaller mean degradation is a relative comparison, not an average improvement.

The one utility-positive candidate is Y38T (one-based numbering), with task
deltas−0.000181095 and−0.001326579 on the two confirmation noises; it also
passes task+nonregression on211. It fails absolute maximum penetration in all
three noises. It is not an accepted chemically valid design. The matched parent
already has maximum penetration2.9791/3.0359Å on the confirmation noises,
above the unchanged2Å pilot cutoff; this does not waive candidate acceptance.

## Interpretation

This single-parent batch provides a small, descriptive indication that the local
gradient can propose a hard mutation retaining task benefit without additional
geometry regression. It does not establish a general advantage: only1 vs0 joint
utility success, no accepted designs, and15 of16 gradient proposals concern the
sameY38 site (the remaining isR45P). Mutations are not independent proteins.
There is no basis here to reopen backward repairs or train diffusion LoRA.
Absolute geometry and useful discrete-design outcomes remain unresolved.
Deployment remains rejected. No binder/interface objective or experimental
binding success was measured.

## Compute and evidence

Frozen candidates:16+16 with zero overlap, plus parent, all three noises.
Proposal full forward/backward:8.393s excluding loading, setup and preflight
failures. Recovered four-worker hard batch:136.625s wall time including model
loading with20s staggering. Equal candidate budget is not equal total compute;
these timings are not a demonstrated design speedup.

Before freezing candidates, the hand FP32 softmax algebra check failed. Saved
gq matched an independent native softmax pullback exactly, and the FP64 formula
was within a declared FP32 rounding bound. The original failure, intervening
ROCm launch failure and later host reboot are preserved, not relabelled as
successful attempts. No candidate score or model arithmetic was changed.

Compact evidence: `reports/mini_hard_mutation_utility_2026-09-28/report.json`,
`audit.json`, `exit.json`, `score_exit.json`, frozen candidate and source hashes.
Large tensors/topology/coordinates remain at DiamondHill:
`/media/PM982/onestepfold/mini_hard_mutation_utility_v1_20260928/`.
