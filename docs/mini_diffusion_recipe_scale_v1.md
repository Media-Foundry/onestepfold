# Next bounded comparison: objective calibration × optimizer scale

2026-09-30. Execution-ready scientific contract, **not started in the gradient-probe
batch**. The512 pilot and96point gradient diagnostic are closed, unchanged records.
This is one2×2 comparison of two hypotheses, not a rank/depth/seed/method search.

## Evidence and fixed objective

In the length-balanced TRAIN16 diagnostic, the oldteacher contribution hardly changes
the total gradient; bond/clash dominate most points. The previous total update was
also small. Changing both objective and learning rate in a single new run would not
separate these explanations. Use the three new arms below, reusing the old low-LR arm.

The calibrated weights are derived ONCE from the native zero-adapter state, only the
16TRAIN proteins/two old training noises. No terminal or validation performance used
to choose them. Define each statistic as median overproteins of mean overtwo noises
of a rawcomponent gradient norm. Preserve coordinate=.01,smooth_lddt=1,chirality=1.
For bond/clash/teacher, set weight to weightedcoordinate normmedian divided by that
component's rawnormmedian. Sparsechirality is intentionally not inverse-normalized.

| Component | Original | Calibrated |
|---|---:|---:|
| coordinate A | .01 | .01 |
| smooth-lDDT D | 1 | 1 |
| observed bond B | 10 | 1.505408125612628 |
| checked chirality C | 1 | 1 |
| clash R | .1 | .0006600251156855778 |
| frozenS2 T | .0025 | .025476389066842815 |

Exact provenance and values are in
`reports/mini_diffusion_gradient_budget_2026-09-30/objective_calibration.json`.
These match one initial Euclidean-gradient statistic, not per-target gradients or
Adam parameter updates. Lower penalties do not waive collision/stereo requirements.
S2 remains synthetic, sometimes wrong, and GT remains the structural anchor.

## Minimal factorial

| Arm | Objective | LR multiplier | Execution |
|---|---|---:|---|
| old_low | originalGT+S2 | 1 | reuse completed original`gt_s2`, update512 |
| old_high | originalGT+S2 | 10 | new run |
| calibrated_low | calibrated | 1 | new run |
| calibrated_high | calibrated | 10 | new run |

Allnewarms start from originalpublicMini, notoldterminal. Same128TRAIN, same frozen
C4 conditioning, same nativeFP32C4/S1, same835584rank8parameters andseed20260930.
Same saved2048exposure order, alternating600001/600011;16epochs, accumulation4,
512AdamW updates. Betas(.9,.999),eps1e-8,decay0,clip1 unchanged. LR multiplier applies
to the entire original32updatewarmup/cosine schedule: peaks1e-5/1e-4, ends1e-6/1e-5.
This intentionally changes LR only on that axis. No moreepochs, adaptiveweights,
checkpoint selection or retries with new targets. Engineering failure remains visible.

Use threeGCDs concurrently if free. Do not retrainold_low to occupy another card.
Firstzero-adapter cache replay, originalparameter immutability and terminal merge/reload
checks remain required. New trainer configuration must preserve original behavior when
calibration/LR multiplier are absent. Never modify frozenremoteoriginalrun code/locks.

## Assess fitting before spending a fresh independent set

First evaluate all128TRAIN at the two fixed training noises, separate nativeS1/S2,
old_low andthree newS1endpoints. Prior native andold_low predictions may be reused with
hash/replay evidence. Allmodels evaluated atterminal512, no best-of-noise.

Report paired AA/CA quality, tails, severe clashes/checkedstereo, observedGT bonds,
connection distributions, actual mergedweight/coordinate changes and percomponent
loss curves. Loss numbers across objectives are not directly comparable; evaluate
shared structural and chemical metrics. Report the two LR effects, two objective
effects and their interaction rather than claiming onechangedweight caused a result.

TRAIN outcomes are fitting evidence only. The already revealed32VALIDATION is not
used for choosing these weights/LR/endpoints, and this cycle does not reevaluate it.
If a useful quality/chemistry tradeoff emerges, preselect new isolated proteins and
new noises for confirmation before claiming generalization. Old protectedpanels and
temporaltest remain untouched. If no useful joint progress, stopthiscomparison and
reassess; no automatic LR escalation or dataset/method grid.

No deployment release, no LoRAclaim ofglobalsoftsequence continuity, no newchemical
gate. Any chemical improvement/precision loss or viceversa must remain explicit.
