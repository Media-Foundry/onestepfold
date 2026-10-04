# Read-only score-objective audit — 2026-10-05

**The objective is strongly amplitude-weighted, including within-site AA
contrasts. Actual residual and gradient concentration depends on checkpoint and
seed. This motivates a bounded objective comparison, not a claim of discovered
sole cause or guaranteed transfer.** No new loss training has started.

## Scope and checks

[Prospective audit protocol](mini_objective_audit_v1.md): all160sites/fournoise
labels, all12runs/all saved TRAIN snapshots. Fixed gradient subset: n32, both
heads, seeds231301/231303, initialization/32768/131072, all128TRAINsites =1536probes.
No optimizer updates or ESM/C4/S1 calls. Original globally scaled MSE confirmed:
`mean((prediction - old_two_noise_mean / 0.5759913630974075)^2)` on19nonWTAA.
Exposure is uniform; raw score amplitude retains unequal squared-error weight.

The gradient probes reused the exact frozen model and inputs. Checkpoint hashes,
parameter equality before/after and TRAINprediction replay (<1e-5) passed.
Full and score-module gradient norms use the same parameter sets at each site.
Mean-loss and centered-loss gradients are computed separately; their sum obeys
the norm/dot-product identity. Clip1 is simulated from the norm only: these are
not optimizer updates and do not include AdamW moments or weight decay. Gradient
norm sums/squared-norm sums are distinct descriptive statistics, not total causal
influence across training. Four snapshots per n32 run exist; gradients intentionally
use the preregistered three states only. None were picked by outcome.

For19scores y and p, both raw-unit identities are checked:
`mean(y²) = mean(y)² + mean((y-mean(y))²)` and
`MSE(p,y) = (mean(p)-mean(y))² + MSE(p-mean(p),y-mean(y))`.
Undefined constant-prediction rank correlations are counted, not assigned success.

## 1. Mean subtraction does not remove concentration

The previously disclosed heavy set is 2V66D43/L61/T75 (one-based sequence positions;
machine files store42/60/74). It is fixed throughout, not reselected per metric.

| Quantity over128TRAINsites | Heavy three share |
|---|---:|
|Raw label energy|87.6808%|
|Candidate-mean energy|84.0492%|
|Centered AA-specific energy|89.9248%|

Total raw energy decomposes into38.19% candidate-mean and61.81% centered energy.
T75 alone has raw mean-square60.2849, of which59.4631 is centered variation.
Thus this is primarily not a removable common-offset-only phenomenon. Merely
centering a globally scaled regression would retain heavy AA-contrast weighting.

## 2. Residuals differ sharply between seeds

n32context terminal, raw units; same128sites and target labels:

| Seed | Total MSE | Centered MSE | Heavy share total error | Heavy share centered error |
|---|---:|---:|---:|---:|
|231301|.00354|.00189|32.49%|17.49%|
|231303|.40181|.32628|96.18%|98.34%|

Seed231301 fits the heavy sites' old-noise rankings at.9947/.9947/.9982. The
remaining125sites averageρ .3562 (median.3193). Seed231303 heavy rankings remain
.9825/.9825/.9175 despite large score errors; remaining sites average.5484
(median.6257). Therefore low global score MSE and broad site-ranking quality are
already ordered differently across these seeds. Neither checkpoint is promoted.

| Seed | TRAIN old ρ | TRAIN new ρ | oldρ≤0 count /128 | oldρ>.9 count /128 |
|---|---:|---:|---:|---:|
|231301|.3711|.2975|28|23|
|231303|.5581|.4504|15|37|

There is incomplete old-label fitting plus an additional noise-transfer gap;
it is not solely a case of perfect old-noise fitting failing on new noise.

## 3. Gradient concentration is measurable, but clipping matters

Shares below are sums of per-site Euclidean gradient norms, not energy shares,
not norms of summed gradients and not integrated optimizer influence.

| Context seed/state | Heavy share before clip | Heavy share after simulated clip1 |
|---|---:|---:|
|231301 init|49.02%|4.91%|
|231301 32768|79.70%|15.78%|
|231301 terminal|65.49%|32.26%|
|231303 init|47.76%|4.98%|
|231303 32768|72.28%|17.39%|
|231303 terminal|93.83%|26.04%|

At terminal the three sites account for87.56%/99.53% of summed squared full
gradient norms; those are yet another normalization. Total clipped-site counts
are4/5. Centered-gradient norm shares are64.54%/96.81%. All per-site/readout values,
mean-centered gradient inner products, AA-only controls and replay errors are
retained. Small median norms at other sites do not by themselves prove zero useful
learning; architecture sensitivity, accumulated updates and clipping also matter.

## 4. Teacher contrasts are not uniformly noise-free or uniformly noise

| Heavy site | Old/new19AAρ | Centered cosine | Old-select/new regret |
|---|---:|---:|---:|
|D43|.4544|.7947|0|
|L61|.9509|.8612|0|
|T75|.9316|.9721|.36920|

TRAINold/newρ mean.7863; confirmation mean.7197. Corresponding teacher old-select/
new-eval regret means.04331/.04584. These are descriptive fournoise diagnostics,
not theoretical prediction ceilings. The heavy trio includes stable contrasts and
one less stable ranking; discarding all three as noise is not supported.

Post-hoc descriptive TRAINquartiles by centered old energy: bottom32sites have
old/newρ .6660 and median centered noise-MSE/signal .3270; middle64 have.8571/.0962;
top32 have.7650/.1042. Low-amplitude sites are noisier on this measure but are not
all uninformative. These quartiles are analysis only, not exclusion/weight rules.

## Decision and limits

Close the data-scale batch and this audit. Preserve every seed, site and historical
failure. There is now direct evidence that globally scaled MSE weights site
contrasts very unevenly, and the effect is not only a candidate-mean offset.
A fixed-model/fixed-data centered, floor-scaled objective comparison is warranted
as a separate proposal; it is not executed here. Any floor must use TRAIN-only
information and be frozen before new outputs; original regret, raw errors and
high-cost cases remain necessary. Centered-only supervision would target19mutant
ranking, not absolute improvement over WT or calibrated20AAprobabilities.

No proof of insufficient WT information, universal capacity failure, or a causal
explanation of transfer has been obtained. Confirmation results already observed
here cannot become a fresh independent test for subsequent method selection.

Artifacts: [summary](../reports/mini_objective_audit_2026-10-05/summary.json),
[per-site labels/noise](../reports/mini_objective_audit_2026-10-05/labels.csv),
[all TRAIN snapshots](../reports/mini_objective_audit_2026-10-05/training_decomposition.csv),
[gradient probes](../reports/mini_objective_audit_2026-10-05/gradients.csv).
Full probe packets/checkpoint hashes and artifact SHA256 inventory are alongside.
