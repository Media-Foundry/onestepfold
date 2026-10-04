# Repeated-context learning curve — completed 2026-10-05

The frozen batch is **complete and closed**, not waiting for evaluation. No model
is promoted. Repeating source-AA types across more environments did not establish
a stable new-protein advantage for this context score head over AA-only.

## Execution and scope

Protocol: [mini_context_replication_v1.md](mini_context_replication_v1.md), source
88f6330c. Forty parents: nested8/16/32TRAIN and8new confirmation candidates,
each one A/D/L/Tsite. All3080native sequences passed preflight. Executed3120C4,
12480recycles,12360S1 including40WTreplays; no sample replacement. Twelve fresh
training runs (2heads×2seeds×3sizes) and3200checkpoint/site evaluation records.
All stages exited0; wall3155.65s (52.59min).

Independent audit passed12320coordinate-to-task checks,12800label checks,
12initializations,28checkpoints,9600selection checks and12800selected geometry
retrieval checks. Geometry retrieval is not independent recomputation of every
geometry metric. All failures remain in denominators.

The scorer uses WT context, explicit parent reference backbone and hardAA query;
no oracle mutant s/z/s_inputs. It generates no coordinates. Geometry describes
selected native teacher structures, not repairs. This is a parent-reference
Cα-distance proxy, not experimental mutant utility, binder activity or a complete
20-mutant structure accelerator. Operational homology isolation does not prove
pretraining independence. Confirmation has only8proteins and is now observed.

## Main fixed-exposure endpoints

Each site received1024full19AA batches. Updates32768/65536/131072 respectively.
Ranking is on four-noise mean candidate scores, site-then-protein averaged;
32confirmation sites are not32independent proteins. Two entries are seeds231301/231303.

| TRAIN proteins | Context TRAIN ρ | Context confirmation ρ | AA-only confirmation ρ | Context Top1 /32 |
|---|---|---|---|---|
|8|.4699 / .5013|.0054 / .0010|.0235 / .0302|4 / 1|
|16|.7067 / .4194|.0162 / −.0337|.0357 / .0363|2 / 3|
|32|.3462 / .5162|.0370 / .0137|.0527 / .0546|2 / 1|

All six endpoint contextρ values are below their paired AA-only. This is a
finite-panel result, not a proof context is intrinsically uninformative.

| TRAIN proteins | Context old-select/new-eval regret | AA-only regret |
|---|---|---|
|8|.38359 / .26814|.36779 / .36779|
|16|.28865 / .23523|.28715 / .28715|
|32|.27527 / .36840|.30321 / .30321|

At32, one seed reduces regret and one increases it. Descriptive paired protein
bootstrap intervals for all six endpointρ and regret contrasts cross zero.
No seed/checkpoint is discarded or chosen as the winner. At common32768updates,
contextρ for n16 is.0939/−.0179 and n32 .0740/.0399; AA-only is.0397/.0344 and
.0468/.0385. This alternative budget view also fails to establish stable benefit.
Full per-protein/source/category/seed tables retain other-TRAIN-pool predictions,
medians, worst-protein regret, raw score errors and selected geometry counts.

## What changed in the data

A/D/L/T each have8/16/32TRAIN contexts, no singleton source type. Unrestricted
AA-pair table irreducible normalized error is.782901/.899858/.957822; this removes
the earlier near-identity shortcut, without ensuring the neural head learns context.

Atn32, 2V66D43/L61/T75 contribute87.6808% raw label squared energy. This is label
energy, not residual or optimizer contribution. The subsequent read-only
[objective audit](mini_objective_audit_findings_2026-10-05.md) separates these quantities.
No architecture, loss, sampling or extra training is introduced by that audit.

## Artifacts

[Final curve](../reports/mini_context_replication_2026-10-05/final/curve.csv),
[complete aggregates](../reports/mini_context_replication_2026-10-05/final/analysis.json),
[execution](../reports/mini_context_replication_2026-10-05/final/execution.json),
[independent audit](../reports/mini_context_replication_2026-10-05/final/independent_audit.json).
Compressed original report/labels plus SHA256 inventory are in the same directory.
Large checkpoints, WTconditioning and coordinates remain under
`context_replication_v1_20261005` in the usual DiamondHill runtime;
metadata mirrored at `/home/husrcf/Code/onestepfold_runtime/context_replication_v1_20261005`.
The separate startup status document is historical, not current execution state.
