# Mini compensated final recycle — complete, not promoted

Both fixed seeds completed8,208updates, independent coordinate scoring and
checkpoint replay. Controller closed successfully after13,445.44s (3.73h).
No replacement seeds, extra steps or intermediate-checkpoint selection.
Implementation `fda8f488`; [locked protocol](mini_compensated_recycle_v1.md);
[evidence](../reports/mini_compensated_recycle_2026-10-07/README.md).

**The compensator learned correct AA correspondence in training environments.
It did not establish a reliable improvement over unadapted WT3→Target1 on new
proteins. Retaining one native recycle has measurable cached-folding cost
benefits, but the learned compensation is not ready to promote.**

## What actually ran

Frozen Mini v0.5.0, FP32, WT completed cycle3 state and RNG; a1,420,160-parameter
hard-edit compensator; one frozen native candidate recycle; frozen S1 with actual
candidate chemistry. Candidate **archived s_inputs** are legal inputs to the
native path. The compensator sees only WT3 state and edit identity. No target
final s/z enters inference or training. This is not strict WT-only inference:
candidate ESM/input computation has already occurred and is excluded here.
No new ESM/MSA preparation or input-encoder calls occurred. Native MSA module
execution remains within the folding computation.

Fifteen TRAIN parents/27sites/513mutants; three same-parent unseen sites;
nine unseen-parent development proteins/18sites/342mutants. These panels have
development history. Two original noises230201/230211; train only230201.
Each mutant received32exposures; checkpoints0/4,104/8,208 all evaluated.

Correct query versus disabled compensator versus a single pre-fixed wrong-AA
query. Actual candidate s_inputs, chemistry and noise remain unchanged in every
arm. Wrong query tests the **additional compensator**, not removal of all AA
information. Terminal8,208 is primary;4,104 is descriptive only.

All preflight24WT/912candidate C4 tensor/two-noise coordinate replays passed.
Both full-panel step0 correct/wrong outputs replay disabled bitwise. All six
saved checkpoints replay fixedT37A/two-noise coordinates bitwise; terminal
no-edit and serial candidate-order checks pass. Frozen native weights remain
unchanged. Ten focused local tests passed before execution.

Actual totals:16,416training updates,49,922native recycle passes and59,120S1
calls, including preflight, evaluation and timing. Four discarded preflight
optimizer updates are separate. The inherited `c4=0` counter does **not** mean
no native trunk computation; use the explicit recycle count.

Twenty-one remote artifact files /79,349,266bytes were collected and SHA256
verified. Independently recomputed all864site/arm ranking and raw-regret records
from their saved score matrices; verified27×19candidate exposures per seed,
all fixed checkpoints and counters. Full scored geometry/coordinate evidence
remains available remotely; compact summaries/site matrices are tracked here.

## Training: correct correspondence is now demonstrable

Parent-equal means;27sites/15parents. Structure tails/counts pool1,026outputs.

| Metric | Disabled WT3→Target1 | Correct272001 | Correct272003 | Wrong272001 | Wrong272003 |
|---|---:|---:|---:|---:|---:|
| Two-noise-mean Spearman | .56363 | .69725 | .72374 | .56637 | .55333 |
| Old-choice/new-Exact regret | .24790 | .06151 | .04718 | .24780 | .21741 |
| Centered AA distance-response RMSE, Å | .41115 | .29683 | .29945 | .49707 | .50419 |
| All-atom lDDT to same-noise Exact | .95787 | .97113 | .97261 | .96554 | .96580 |
| Local RMSD P95, Å | 2.07615 | .80522 | .79728 | 1.35910 | 1.40877 |
| Local deviations >1Å | 139 | 33 | 35 | 80 | 89 |
| Geometry passes | 427 | 485 | 481 | 480 | 475 |

Both correct-minus-wrong TRAIN Spearman bootstrap intervals are positive;
both correct-minus-disabled and correct-minus-wrong centered-response intervals
are negative. Thus this is stronger than merely producing different outputs
for different AA. It is still imperfect fitting, not convergence or experimental
mutation accuracy. Teacher itself passes geometry only412/1,026 here.

## Held proteins: no reliable net gain over native continuation

Nine development parents/18sites;684mutant/noise outputs. Higher Spearman and
lower regret/response RMSE are desirable. Parent-level means, not independent
mutant-level replicates.

| Metric | Disabled WT3→Target1 | Correct272001 | Correct272003 | Wrong272001 | Wrong272003 |
|---|---:|---:|---:|---:|---:|
| Spearman | .54142 | .54123 | .52807 | .44756 | .49240 |
| Top1, out of18 | 6 | 6 | 7 | 4 | 5 |
| Cross-noise raw regret | .04631 | .19816 | .03934 | .04697 | .13565 |
| Parent regret median | .00897 | .02630 | .00474 | .02091 | .00897 |
| Worst parent mean regret | .19607 | 1.28428 | .22500 | .24611 | 1.07859 |
| Centered AA response RMSE, Å | .44818 | .46956 | .46595 | .47792 | .47122 |
| All-atom lDDT | .92705 | .92704 | .92702 | .92665 | .92671 |
| Geometry passes /684 | 432 | 395 | 397 | 399 | 391 |
| Disabled-pass→method-fail | 0 | 49 | 46 | 46 | 49 |
| Local RMSD P95, Å | 3.43950 | 3.79163 | 3.85498 | 3.79993 | 3.74402 |
| Local RMSD maximum, Å | 6.93855 | 6.45690 | 5.90755 | 7.34454 | 6.47004 |
| Local deviations >1Å | 141 | 137 | 134 | 143 | 135 |

The second seed retains a positive selection observation: regret falls about15%
and Top1 rises6→7. The first seed instead incurs about4.28×disabled regret.
Both correct-minus-disabled regret intervals crosszero, as do their Spearman
and centered-response intervals. Point-estimate response errors worsen in both
seeds; do not claim a statistically established universal worsening from this
nine-parent panel.

Correct beats wrong in held Spearman and response-RMSE point estimates for both
seeds. Only the first seed's Spearman interval excludeszero. This is weak held
identity signal, not stable added utility over disabled. In particular, wrong
query gives lower regret for seed272001, whereas correct wins for272003.

Reference-only, with WT final conditioning and candidate chemistry but no
candidate recycle, has Spearman.15244/regret.23250/responseRMSE.47805. Native
continuation accounts for substantial improvement over that reference. Giving
the learned adapter credit for this already-present native gain would be wrong.
Exact's old-choice/new-noise self-regret is.008366, not zero.

These are different parents/sites from the earlier eight-parent ADLT+2V66
prefix experiment. The present disabled regret.04631 does not overturn that
experiment or justify a cross-panel numerical comparison.

## High-cost cases and geometry

Seed272001, correct versus disabled:

- 6ZRW T45 selectsI instead ofV; regret .06648→2.00195.
- 2EBE A30 selectsP instead ofD; regret 0→.69692.
- 6ZRW P80 selectsS instead ofC; regret .15522→.56661.

Seed272003 is less damaging overall but still worsens P80 to.42574 (selectsV)
and A30 to.08420 (selectsG). Do not erase these errors using average Top1.

The two correct seeds introduce49/46 failures from disabled's passing outputs,
while repairing12/11. Relative to Exact, both introduce67 failures and repair
24/26. Exact itself passes438/684. Absolute quality, transitions and structural
deviations remain separate quantities; teacher is not chemical truth.

Worst correct held deviations occur at2EBE E47F/noise230201 (6.45690Å) and
E47V/noise230201 (5.90755Å). Maxima and >1Å counts improve slightly over disabled,
but P95 worsens; neither "all tails improved" nor "all tails worsened" is accurate.

## Same-reference new sites

Only three sites/three parents. Disabled Spearman.68830 and regret.11885;
correct gives.57661/.60526 and.11226/.12034. ResponseRMSE .47523 becomes
.47439/.48169. No consistent correspondence/quality gain; small subgroup
intervals and reused development cases cannot establish transfer.

At4,104updates held correct Spearman was.57719/.59532, above terminal values,
but regret was.17222/.14130 and responseRMSE.46259/.46771. Do not retrospectively
promote the earlier checkpoint: it already exhibited quality tradeoffs.

## Cached folding timing, narrowly scoped

Serial audit on one MI250 GCD after training workers closed; fixed1W53,L84,
19non-WT candidates, one S1 noise. Rotate arm order, first repetition warmup,
median of five subsequent repetitions. Input/chemical packets are already
device-resident. Include native initialization, native recycle, prefix capture,
compensation and diffusion-cache/S1 work. Warm arms pay one fresh WT C4 capture.
Exclude ESM/MSA preparation, model load, disk, host output/scoring. This is not
whole-pipeline timing or a length-diverse performance confirmation.

| Cached folding workload | Seed272001 audit | Seed272003 audit |
|---|---:|---:|
| Cold19×C4+S1 | 6.21123s | 6.18036s |
| WT C4 once +19×unadapted lastcycle+S1 | 2.19995s | 2.18973s |
| WT C4 once +19×compensated lastcycle+S1 | 2.25036s | 2.22861s |
| Cold/compensated ratio | 2.76× | 2.77× |

Adapter overhead over unadapted continuation is about2.29%/1.78%. Native work
reduction is real under this boundary; it does not compensate for unmet quality.
The two audits use two learned endpoints of the same architecture, not two
independent hardware platforms. No deployment speed claim is supported.

## Decision

Close this fixed-budget batch without promotion or automatic extension. Preserve
the positive training correspondence and measured cached-folding cost reduction.
The remaining limitation is transfer and quality of the learned pre-recycle
correction; one native recycle did not by itself guarantee that correction is
safe on unseen proteins. This does not prove every compensated-recycle model
unlearnable, nor justify a new rank/LR/prefix-length sweep on these same cases.
