# Fixed-data score-objective A/B/C comparison — v1, 2026-10-05

Authorized after175552c4. This is a new experiment, not an extension/reclassification
of completed runs. Only the objective changes. No new teacher, ESM/C4/S1, rank,
architecture, activation, optimizer, source-AA selection or data expansion.

## Fixed data/model/exposure

Reuse exact context_replication_v1_20261005 n32TRAIN:32parents128ADLTsites,19nonWT
candidates/site. Same archived WTconditioning, supplied parent GT reference,
original heads ContextTaskReadout3,780,994 / AATaskReadout21,377parameters.
No oracle mutant s/z/s_inputs. Original8confirmationparents32sites are now **DEV**,
not fresh independent confirmation. Old16/otherpanels are not added.
Oldlabelnoises230201/230211;newevaluation310003/310019. Outputscale unchanged
0.5759913630974075. Predictor receives no teacher means, scales or labels.

3objectives×2heads×2seeds231301/231303 =12fresh runs. Each131072updates =1024full
19AA exposures per site, same ordered128site cycle. AdamWlr.001,weight_decay.0001,
eps1e-8,clip_global_norm1; no schedule/retry/seed replacement. Initial weights
must match across A/B/C per head/seed and the preceding n32 initialstate.
Snapshots0/32768/65536/131072. Terminal is primary; intermediate TRAIN diagnostics
are not used for selection. All12runs finish before DEV evaluation.

## Three objectives

p is model output in original normalized units; y is oldnoise mean Δtask divided
by originalscale. On nineteen nonWTcandidates:
A=mean((p-y)^2).
B=mean(((p-mean(p))-(y-mean(y)))^2).
C=w_i*B.

For each TRAINsite compute v_i=mean((raw_old_delta-mean(raw_old_delta))²) in raw
task units. floor=max(linear25thpercentile(v),1e-12). rawweight_i=1/max(v_i,floor),
w_i=rawweight_i/mean(rawweight). No other quantile search. Compute weights inFP64,
store/hash before any updates. Same weights across seeds/heads. Newnoise/DEVlabels
cannot influence weights. A/B weight1; all arms retain the same outputscale.
B/C leave nineteen-mutant common offset unsupervised even though outputWT=0;
no absoluteWTgain, calibration or20AAprobability claim. No mean/scale predictor.

## Gradient observations and clipping

Everyupdate records norm from actual weighted backward before clip. The unweighted
base norm is weighted_norm/w_i (same parameter point); this follows positive
scalar loss scaling, not a second optimization trajectory. Compute clip coefficients
using PyTorch's1e-6 denominator convention. Aggregate per site, and per32768update
window, before/after norms, sums of squared norms, clip counts, post-vector ratio,
and count with both weighted/unweighted gradients clipped. Preserve first16 and
periodic scalar traces. A/B w=1. A uses raw base; B/C use centered base.
This measures gradient changes under the current recipe, not AdamW causal
contribution; moment history and decay remain unchanged.

## Locked evaluation

All terminal12checkpoints ×160sites =1920rows. Same19AAordering/tie handling,
old/new/fournoise mean-score Spearman,Top1,top3/top5recall,rawMAE/RMSE,
old-select/new-eval regret and extra regret vsExactoldchoice. Deterministic scorer
selects once; no reselection using newlabels. Report TRAIN and DEV separately,
site-within-protein then equalproteinweight; sourceAAstrata, per-site ranks,
median/nonpositivecount, centered/rawerror, worstprotein/high-regret cases.
Fixed2V66D43/L61/T75 reported individually. No cases are removed by amplitude/noise.
Selected native teacher geometry retrieved for bothnewnoises; student generates
no coordinates, no new repair or geometry claim. No imported historicalWT-zscores.

Primary contrasts: B−A and C−B for eachhead/seed; Ccontext−Acontext;
context−AA-only within eacharm. Keep bothseeds, including collapse/failure.
Descriptive pairedproteinbootstrap (10000draws,seed314159) on8DEVproteins is not
an independent-confirmation claim. Improvement must be judged jointly with raw
regret/tails, not newloss values. No automatic promotion/training extension.

## Execution bounds and audit

New immutable source/label/weight/model hash lock; prior archive untouched.
Native device guard reused; controller queues at most4 GPU jobs plus a separate
CPU AA-only stage. Pertraining job7200s, evaluation/audit1800s; stage failure halts
dependent execution and preserves partial outputs, no outcome-dependent retries.
Independent audit checks initialpairing, optimizersteps/exposure, recomputed
weights and losses, TRAINpredictionreplay, counts/selections/geometry retrieval,
and zero additionalC4/S1. No trainedcheckpoint is installed as a default.
