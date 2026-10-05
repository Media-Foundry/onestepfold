# Fixed-data A/B/C objectives — complete, 2026-10-05

**C improves the breadth of TRAIN ranking, but does not establish new-protein
context benefit and increases mean cross-noise selection regret in both seeds.
The batch is closed, no model promoted and no further training started.**

## Execution

[Locked protocol](mini_score_objectives_v1.md), source84ed5ca9. A raw MSE;
B separately centered prediction/teacher MSE; C B times TRAIN-only inverse floored
variance weights (mean1). Same32TRAINproteins/128sites,8previously observedDEV
proteins/32sites, nineteen nonWTAA, two heads and seeds231301/231303. Model,
optimizer, ordered exposures, scale, initialization and noise protocol unchanged.
No new teacher, ESM/C4/S1 calls or student-generated coordinates.

All12fresh runs reached131072updates (1024exposures/site):1,572,864updates total.
All1920terminalsite records, audit and summaries completed; wall4520.795s=75.35min.
`active_step=130560` in periodic training logs is the last logging interval;
terminalcheckpoints/optimizer states are131072. No timeout/retry/replacement.

Independent audit passed12initializations,36checkpoints,6144loss reconstructions,
2640clipping trace checks,5760selection checks and7680selectedgeometry retrievals.
FreshA terminal TRAIN predictions match preceding n32A predictions **exactly** for both
heads and seeds (maximum absolute difference0), supporting the matched reference.
Geometry audit verifies archived selected records, not newly recomputed chemistry.

## Ranking and selection

Rows show seeds231301 /231303. Ranking is fournoise mean-score Spearman,
site-within-protein then equalprotein average. TRAIN32proteins128sites;DEV8/32.
Do not interpret mutant×noise counts as independent proteins.

| Objective | Context TRAINρ | Context DEVρ | AA-only DEVρ | Context DEVTop1 /32 |
|---|---|---|---|---|
|A raw|.3462 / .5162|.0370 / .0137|.0527 / .0546|2 / 1|
|B centered|.3199 / .0996|.0957 / .0242|.0610 / .0652|0 / 1|
|C centered+weighted|.7219 / .5951|−.0416 / .0207|.1432 / .1373|4 / 1|

C beats A and B on TRAINρ for both seeds. Only centering does not reliably improve
TRAIN; seed231303B has low but nonconstant ranking, not evidence of the prior GELU
collapse mechanism. No new mechanistic attribution is made.

| Objective | Context oldnoise TRAINρ | Median site oldρ | oldρ≤0 sites /128 |
|---|---|---|---|
|A|.3711 / .5581|.3316 / .6789|28 / 15|
|B|.3479 / .1096|.3289 / .1026|28 / 50|
|C|.7847 / .6369|.8798 / .7061|2 / 3|

This is genuine improvement in breadth of training candidate ranking, not simply
comparison of incomparable loss values. It is not near-perfect training recovery.

| Objective | Context DEV old-select/new-eval regret | AA-only same-objective regret | Context worst-protein mean regret |
|---|---|---|---|
|A|.27527 / .36840|.30321 / .30321|.90031 /1.07201|
|B|.30432 / .33932|.31113 / .31113|.93875 /1.07416|
|C|.51387 / .46724|.41242 / .41242|1.73826 /1.59014|

Ccontext is below CAA-only in DEVρ for both seeds, differences−.18479/−.11664;
descriptive paired8protein bootstrap95% intervals[−.27533,−.10233] and
[−.18986,−.05378]. This is a development-panel observation, not independent
confirmation or a universal context impossibility result. C−Amean regret increases
+.23860/+.09884. Cprotein-regret medians .07072/.09625 are below A .08290/.13830,
so mean deterioration and better medians coexist; tails cannot be suppressed.
Bcontext−BAA-only is positive for one seed and negative for the other.

Ccontext worst-site errors include4LR3T4→V (regret3.8676 bothseeds),5OI7A50→V
(3.7098 seed231301),5OI7T80→S (2.9556 seed231301) and→G (2.8218 seed231303).
No case is dropped. Full per-protein/sourceAA errors and paired contrasts are saved.
No historicalWT-z number from a different cohort is used.

## Weighting was not erased by clipping

Every trainingupdate recorded actualweighted preclip norm; the unweighted value
is a same-state scalar counterfactual, not a separately trained trajectory.
For C, bothweighted/unweighted norms exceeded1 in only.02289%/.05188% ofupdates.
Weighted clip frequency was.02899%/.05264%, compared with A6.2523%/6.6650% and
B4.8866%/8.1223%. Therefore failure cannot be explained by near-universal cancellation
of the scalar weights by clipping.

At the actual Cstates, heavy2V66D43/L61/T75 account for26.944%/30.701% of the
summed unweighted postclip norm, versus1.547%/11.779% after weighting+clip.
Across A's own trajectory their postclip shares are16.770%/14.845%.
These sums describe gradient magnitude, not AdamW cumulative parameter influence:
state differences, moments, decay and direction remain relevant. Meanweight1
also does not match total gradient scale or effective optimization across arms.

## High-amplitude training cases lost fidelity

| Case | A oldρ, seed301/303 | C oldρ, seed301/303 | C old-select/new regret, seed301/303 |
|---|---|---|---|
|2V66D43|.9947/.9825|.4140/.0737|0 /6.2832|
|2V66L61|.9947/.9825|.1561/.1053|3.7071 /5.0754|
|2V66T75|.9982/.9175|.1070/.2649|6.4589 /2.5953|

The TRAIN Cmean regret rises to.12921/.22888, from A .06762/.08986, despite
much better broad ranking. Seed301C improves TRAINmedian proteinregret to.00351
from.02666; seed303 changes.01154→.01314. Both common and high-cost cases matter.
This is a concrete tradeoff from this fixed objective choice, not a reason to
retroactively delete high-amplitude sites or change the floor.

## Geometry, score scale and system boundary

DEVselectednativecandidate passes on bothnewnoises (zero severe overlap + strictly
checked chirality) are A9/10, B8/8, C10/10 of32sites; CAA-only11/11.
Those are selection outcomes, not coordinate repair or comprehensive chemistry.
B/C leave mutant common offset unsupervised; raw score errors remain in files,
but no WTbenefit/calibrated probability claim is made. Explicit reference backbone
is still a legal task input; task labels are a model distance proxy, not measured
mutation utility. Scorers have no oracle target s, but are not structure generators.

## Decision

The experiment separates two questions: changing the objective can improve TRAIN
site-ranking breadth, yet this did not yield stable DEVcontext benefit and worsened
mean selection risk. Amplitude imbalance is therefore not a sufficient explanation
or demonstrated repair of transfer in this setup. Do not automatically try another
floor, add steps or expand this same recipe. No architecture or model is promoted.
Further work requires a separately defined question; stronger native-model priors
or retaining some actual mutant computation are possible future directions, not
experiments launched by this report. No claim final-state prediction is impossible.

[Machine-readable summary](../reports/mini_score_objectives_2026-10-05/final/summary.json),
[per-site selections](../reports/mini_score_objectives_2026-10-05/final/selection.csv),
[gradient accounting](../reports/mini_score_objectives_2026-10-05/final/gradient_summary.json),
[independent audit](../reports/mini_score_objectives_2026-10-05/final/independent_audit.json).
Compressed original report/TRAINhistories and SHA256 inventory accompany them.
Large checkpoints remain in DiamondHill `score_objectives_v1_20261005`;
metadata at `/home/husrcf/Code/onestepfold_runtime/score_objectives_v1_20261005`.
The launch status file is historical; execution now says complete/closed.
