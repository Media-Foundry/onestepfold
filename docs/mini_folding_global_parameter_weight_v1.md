# C4/S1 global-distance parameter-budget trial v1

Decision from completed TRAIN-only parameter-budget diagnostic, not a DEV-selected
weight grid. Implementation/training not started at protocol creation.

## Single intervention

Same retained512 parent, TRAIN423 membership, all8192 ordered exposures/noises,
2048updates, accumulation4, Adam/schedule/clipping/zero optimizer initialization,
nativeFP32, frozen ESM2/C4 and288dense diffusion tensors. Keep coordinate weight0,
all5 remaining original terms,globalCAdistance definition (sequencegap>=24,
no spatial cutoff,SmoothL1 beta10Å),atom maps/GT masks/chemistry unchanged.

Only replace global_distance coefficient:
 .03290655679814053 → .1810138829332775.
Rule: formerweight × median over8fixedTRAIN initial-state ratios of weighted
old.01coordinate parameter-VJP norm to formerweightedglobal parameter-VJP norm.
Factor5.5008454407331415. Source is retry1/report.json SHA
ce7157462408ab78a627bbc281424e694204b3c8ed673ae5b7b49e03d9e2c1a0;
calibration uses retained512 only, noise600001, no terminal or validation quality.
This is Euclidean parameter-norm matching,not Adam-step matching or equivalent
objectives. The8proteins are53–488residues; extrapolationto longerTRAIN is unproven.
No second strength, beta change, newdata, ESMC bridge, repair or design experiment.

## Execution and preflight

Use an isolated root and protocol; do not modify original completed training or
verification contracts. Reuse unchanged train_folding_scale and label hooks after
explicitly verifying only the allowed coefficient/scientific field changed.
Copy frozen production sources. Bind every new label/checkpoint/code artifact.
On original short/long engineering examples replay the parent, verify old raw
components unchanged and new weighted total formula; all selected gradients must
be finite, parameter values unchanged before release. Preserve initial TRAIN32
probe hashes. Keep 0/512/1024/2048 TRAIN probes, no checkpoint selection.

HPC3 acd_u, original validated node preferred, no automatic requeue. One training
candidate only,2048updates,4h schedulerlimit(not open-ended sciencebudget).
Record clipping,all losscomponents,exposures/runtimes/peakmemory; audit terminal
against exact order/initialstate/selectedparameter scope. If failure, preserve it
and investigate before any separate infrastructure retry. No silent restart.

## Terminal evaluation

Same455proteins×2noises. Reuse six audited previous outputs: nativeS1/nativeS2,
retained,expanded,coordinate_zero,global_distance. New semantic arm
`global_parameter_matched`;910newpredictions plus bounded engineeringchecks.
Seven-model full denominator6370. Existing GT/masks and scoring unchanged.
Same whole-chain RMSD,localAA/CA lDDT,far distanceMAE/bias,Rg/fragment/remaining95%,
pairedtails,newclashes/stereocentrefailures,typedconnections,actualcost.

Primary contrasts candidate−global_distance ANDcandidate−expanded; alsozero,
retained,nativeS1/nativeS2. Keep TRAIN128/295 andobservedDEV32 separate. Average
locked noises perprotein,neverbest-of. DEV remains development,notfresh confirmation.
No automaticdefaultpromotion or claimC4S1matchesS2. Stop at fixedterminal;
new result determines next action,not another automatic coefficient grid.
