**DESCRIPTIVE DIAGNOSTIC ONLY: the original exact terminal-coordinate replay gate failed. Its failure and original outputs are preserved. This report is not a protocol acceptance, model promotion, or deployment release.**

# C4/S1 matched ROCm global-distance weight comparison

Same retained512 parent, TRAIN423, ordered 8192 exposures, 2048 updates and ROCm backend. Only global-distance weight differs: weak 0.0329065568, strong 0.1810138829. Frozen ESM2/C4, native FP32 diffusion, C4/S1/K1. Experimental GT is the quality reference; cached S2 supervision is a model prediction, not experimental truth.

Scores use observed experimental GT. Each protein contributes the mean of its two fixed noises; no best-of-noise or intermediate-checkpoint selection. Geometry counts describe the explicit severe-collision and checked-stereocentre criteria, not comprehensive chemical correctness or deployment approval.

## observed_validation32: 32 proteins

|Model|AA-lDDT|Cα-lDDT|Zero severe + strict stereo, instances|Both noises, proteins|Severe pairs total|
|---|---:|---:|---:|---:|---:|
|weak|0.819746|0.905274|46/64|22/32|432|
|strong|0.819054|0.904546|47/64|22/32|346|

Positive quality differences favor the candidate. Intervals resample proteins, conditional on the two locked noises; they do not establish independence from pretraining.

|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|
|---|---|---:|---|---:|---:|---:|---:|
|strong − weak|AA|-0.000691|[-0.001118, -0.000312]|-0.004470|-0.001971|-0.003926|0/32|
|strong − weak|Cα|-0.000728|[-0.001328, -0.000187]|-0.005534|-0.003053|-0.004855|0/32|

|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|
|---|---:|---:|
|strong − weak|0|1|

Descriptive length/assembly subsets; overlapping views, not additional independent tests.

|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|
|---|---:|---|---:|---:|
|length_50_255|16|strong − weak|-0.000704|-0.000878|
|length_256_511|15|strong − weak|-0.000558|-0.000482|
|length_512_1024|1|strong − weak|-0.002494|-0.002010|
|monomer|1|strong − weak|+0.000499|+0.000648|
|multimer_single_chain|31|strong − weak|-0.000730|-0.000772|

## original_train128: 128 proteins

|Model|AA-lDDT|Cα-lDDT|Zero severe + strict stereo, instances|Both noises, proteins|Severe pairs total|
|---|---:|---:|---:|---:|---:|
|weak|0.809796|0.888952|191/256|86/128|2851|
|strong|0.808957|0.888139|189/256|86/128|2364|

Positive quality differences favor the candidate. Intervals resample proteins, conditional on the two locked noises; they do not establish independence from pretraining.

|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|
|---|---|---:|---|---:|---:|---:|---:|
|strong − weak|AA|-0.000839|[-0.001317, -0.000311]|-0.010692|-0.004683|-0.008076|0/128|
|strong − weak|Cα|-0.000812|[-0.001511, +0.000101]|-0.012377|-0.005283|-0.009449|0/128|

|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|
|---|---:|---:|
|strong − weak|9|12|

Descriptive length/assembly subsets; overlapping views, not additional independent tests.

|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|
|---|---:|---|---:|---:|
|length_50_255|64|strong − weak|-0.000758|-0.000702|
|length_256_511|55|strong − weak|-0.000705|-0.000725|
|length_512_1024|9|strong − weak|-0.002239|-0.002129|
|monomer|5|strong − weak|-0.001541|-0.002045|
|multimer_single_chain|123|strong − weak|-0.000811|-0.000762|

## added_train295: 295 proteins

|Model|AA-lDDT|Cα-lDDT|Zero severe + strict stereo, instances|Both noises, proteins|Severe pairs total|
|---|---:|---:|---:|---:|---:|
|weak|0.809996|0.890735|466/590|219/295|4324|
|strong|0.809425|0.890162|449/590|206/295|3336|

Positive quality differences favor the candidate. Intervals resample proteins, conditional on the two locked noises; they do not establish independence from pretraining.

|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|
|---|---|---:|---|---:|---:|---:|---:|
|strong − weak|AA|-0.000571|[-0.000906, -0.000219]|-0.011966|-0.003146|-0.008225|0/295|
|strong − weak|Cα|-0.000573|[-0.001043, -0.000035]|-0.011832|-0.004812|-0.010125|0/295|

|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|
|---|---:|---:|
|strong − weak|22|23|

Descriptive length/assembly subsets; overlapping views, not additional independent tests.

|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|
|---|---:|---|---:|---:|
|length_50_255|242|strong − weak|-0.000472|-0.000468|
|length_256_511|48|strong − weak|-0.001024|-0.001053|
|length_512_1024|5|strong − weak|-0.001003|-0.001075|
|monomer|8|strong − weak|-0.000554|-0.000420|
|multimer_single_chain|287|strong − weak|-0.000571|-0.000578|

## Matched original-TRAIN32 learning curves

Identical original-TRAIN32 inputs and initial predictions; no checkpoint selection.

|Arm|New update|AA-lDDT|Cα-lDDT|Zero severe + strict stereo / 64|Severe pairs|
|---|---:|---:|---:|---:|---:|
|strong|0|0.804774|0.885657|41/64|394|
|strong|512|0.805113|0.886733|40/64|245|
|strong|1024|0.805946|0.887406|42/64|192|
|strong|2048|0.806441|0.887677|46/64|177|
|weak|0|0.804774|0.885657|41/64|394|
|weak|512|0.806051|0.887710|41/64|290|
|weak|1024|0.806935|0.888391|45/64|220|
|weak|2048|0.807564|0.889052|48/64|190|

## Cost and provenance

|Arm|Training seconds|Allocated peak GiB|Samples per protein, min–max|Clipped updates|
|---|---:|---:|---|---:|
|strong|2837.0|16.797|19–20|1211|
|weak|2916.9|16.797|19–20|999|

Complete outputs: **1820** over **455 proteins**. New evaluation prediction NFEs: **1820**; engineering probes: **56**. Independent dense-distance metric maximum absolute discrepancy: **3.33e-16**.

Inference timings in evaluation.json cover diffusion with cached conditioning only. They omit live ESM2 and Pairformer, and are not end-to-end folding speed. Equal updates/exposures are not equal GPU time, FLOPs, or per-protein exposure.

Original TRAIN128 and added TRAIN295 remain separate. The previously observed validation32 is now development evidence, not an independent confirmation set. Most sources are complete chains from homooligomers; assembly context and pretraining exposure remain limitations. A promising result requires later fresh confirmation.

No model is automatically promoted by this report. Review mean quality, paired tails and newly introduced chemical failures jointly. This experiment does not establish BindCraft utility, binding affinity or a gradient through a changed output function.

## Global structure: aligned Cα RMSD (Å)

Lower RMSD is better. Positive candidate − reference differences mean deterioration, opposite to lDDT. These are the existing GT-aligned RMSD scores, without a new alignment or atom mask. Average both locked noises within each protein before aggregation. Intervals resample proteins, conditional on the fixed noises. This adds no acceptance threshold.

### added_train295: 295 proteins

|Model|Mean|Median|P95|P99|Worst5% mean|
|---|---:|---:|---:|---:|---:|
|weak|3.973963|1.935340|14.871430|29.171204|24.116171|
|strong|3.868318|1.854651|14.267810|28.643423|23.353828|

|Candidate − reference|Mean Δ|95% CI|P95 Δ|P99 Δ|Worst5% Δ mean|RMSD increased, proteins|
|---|---:|---|---:|---:|---:|---:|
|strong − weak|-0.105644|[-0.153297, -0.068844]|+0.033026|+0.115839|+0.071804|73/295|

### observed_validation32: 32 proteins

|Model|Mean|Median|P95|P99|Worst5% mean|
|---|---:|---:|---:|---:|---:|
|weak|3.510030|1.764514|11.837487|21.255979|19.159497|
|strong|3.492923|1.797387|11.994503|21.043490|19.099406|

|Candidate − reference|Mean Δ|95% CI|P95 Δ|P99 Δ|Worst5% Δ mean|RMSD increased, proteins|
|---|---:|---|---:|---:|---:|---:|
|strong − weak|-0.017107|[-0.061171, +0.022927]|+0.079690|+0.267756|+0.222891|15/32|

### original_train128: 128 proteins

|Model|Mean|Median|P95|P99|Worst5% mean|
|---|---:|---:|---:|---:|---:|
|weak|4.507625|1.795946|20.334080|28.649889|26.090648|
|strong|4.404454|1.815962|20.072239|27.771282|25.528786|

|Candidate − reference|Mean Δ|95% CI|P95 Δ|P99 Δ|Worst5% Δ mean|RMSD increased, proteins|
|---|---:|---|---:|---:|---:|---:|
|strong − weak|-0.103171|[-0.146263, -0.065365]|+0.025763|+0.049495|+0.065584|29/128|

## Far experimental-distance MAE (sequence gap ≥24, GT ≥30 Å)

|Cohort|Weak|Strong|Strong−weak|95% CI|
|---|---:|---:|---:|---|
|observed_validation32|2.5484612901038055|2.4450666957061333|-0.10339459439767176|[-0.2049684627305607, -0.025135868739373107]|
|original_train128|3.5069727302258267|3.2523183513524927|-0.2546543788733341|[-0.36157102487157716, -0.15747745027946075]|
|added_train295|3.770857191834124|3.4812020452830894|-0.2896551465510352|[-0.3765324105470268, -0.21469677516826277]|

Distance and RMSD increases are worse; empty-band support and all per-protein statistics are in JSON.
