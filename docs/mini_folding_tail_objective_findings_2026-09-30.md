# Saved-prediction objective audit: 1MV8

**The observed lDDT regression is reproducible, and the frozen training objective
assigns it a lower total loss.** This supports a concrete objective-tradeoff concern;
it does not identify the causal training dynamics or justify tuning on this one case.
The two ongoing training arms and their fixed-terminal evaluation remain unchanged.

## Scope and numerical checks

1MV8 (436 residues) was selected post hoc as the largest protein-mean AA decline
in the common original-TRAIN32 probe for TRAIN128 at1024 new updates. The audit
uses all12 saved outputs: two arms × two fixed TRAIN noises ×0/512/1024. It makes
no model calls, takes no gradients and performs no optimizer steps. Experimental
GT identity/masks/coordinates are matched back to the source atom37 arrays; S2
coordinates are explicitly only the native synthetic auxiliary.

HPC3 job662369 completed0:0 in12s, with the CPU audit itself taking3.95s. It checks
saved coordinate and label hashes, and the exact frozen objective source hashes.
Independent SciPy rigid fits and dense distance calculations agree with:

|Quantity|Maximum absolute discrepancy, all12 outputs|
|---|---:|
|AA/Cα lDDT versus archived scores|3.33e−16|
|Cα aligned RMSD versus archived score|1.07e−14 Å|
|Aligned AA MSE versus production objective|5.68e−13 Å²|

Five existing experimental-label/objective tests also pass. These results provide
no evidence of an alignment or lDDT scoring error for this case. Loss values are
CPU recomputations of the frozen objective, not claimed bitwise GPU-loss replay.

## The declining noise instance is rewarded by the total objective

For TRAIN128, noise600011:

|Measure|Start|+512 updates|+1024 updates|
|---|---:|---:|---:|
|AA-lDDT|0.794474|0.737522|0.658448|
|Cα-lDDT|0.869626|0.800855|0.700710|
|Cα aligned RMSD / Å|23.390919|21.907535|19.975652|
|Aligned AA MSE / Å²|555.883360|487.299775|404.535364|
|Smooth-lDDT loss|0.213035|0.267752|0.344580|
|Total frozen objective|5.926910|5.601335|5.532412|
|Severe nonbonded pairs|2|3|11|

The weighted component changes from start to1024 are:

|Component|Weighted change; negative lowers training loss|
|---|---:|
|Aligned coordinate|−1.513480|
|Smooth-lDDT|+0.131544|
|Observed GT bonds|+0.059979|
|Checked chirality penalty|+0.000038|
|Clash penalty|+0.022342|
|Native S2 preservation|+0.905078|
|**Total**|**−0.394498**|

Thus the coordinate-term reduction exceeds the increases in all other terms in
this observed transition. Lower global aligned coordinate error coexists with
worse local distance accuracy and more severe collisions. Both are real measured
changes; neither metric can substitute for the other. The smooth-lDDT loss moves
in the expected adverse direction here, so this is not explained by the surrogate
silently reporting an improvement while hard lDDT deteriorates.

These signed loss-value differences are not gradient-contribution percentages,
nor a causal decomposition of parameter updates. No alternative loss was used to
produce a prediction, and no claim is made that a particular coefficient fixes it.
The coordinate coefficient remains0.01 and all other locked weights remain intact.

## Contrasts and limits

For the other fixed noise600001, TRAIN128 has near-neutral AA change−0.000269 and
total-loss change−0.100249. For the expanded arm at noise600011, AA changes only
−0.010489 while total loss increases+0.044309. The same story therefore does not
describe every arm/noise, even for this protein. Shared-parameter optimization,
exposure count, finite movements and several loss terms remain involved.

This is one already inspected TRAIN protein, not an estimate of failure prevalence.
It does not disprove one-step diffusion, establish an ESMC advantage, or reopen
the resolved backward-numerics investigation. The final all-TRAIN/new-VAL comparison
must finish before selecting a model or the next bounded intervention. If its
tail evidence warrants an objective control, preregister that separately and
retain both global and local accuracy plus chemistry; do not simply tune a weight
until1MV8 passes.

Artifacts: `reports/mini_folding_tail_objective_2026-09-30/`; remote root
`/data/user/shuang886/Folding/folding_tail_objective_audit_v1_20260930`.
