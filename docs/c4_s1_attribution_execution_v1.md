# C4S1 confirmation, attribution and FP32 control — execution v1

User authorized execution, then added an FP32 inference control. No weight training
or distillation. The checkpoint remains protenix_mini_esm_v0.5.0; retain C4 and K1.
This is a matched extension of existing Mini-ESM evidence, not a Mini-default result.

Root: `/data/user/shuang886/Folding/c4_s1_attribution_v1_20260927` on HPC3.
GPU partition `acd_u`, H10080GB required. CPU scoring uses `debug`; acd_u rejects
CPU-only requests. Initial rejected scoring submission allocated no computation.
Job dependency failures cancel downstream jobs rather than leave them permanently
DependencyNeverSatisfied. Check exit codes and final acceptance before using results.

## Frozen work

| Work | Count | Job |
|---|---:|---|
| Historical reference and common-noise preflight | Shortest/longest A targets; four seeds |656868 COMPLETE0:0|
| PanelA: unchanged128, add C4S1 |512 predictions, reuse1024 accepted S2/S5 references|656899 array0–15,max8 concurrent|
| PanelB packet preparation |88 extra targets;14 overlap A|656900|
| PanelB native + controlled |1056 native +1224 controlled predictions|656901 array0–7|
| Native/controlled scoring, persistence, paired intervals |CPU-only|656910|
| PanelB FP32 controlled, C4S1/S2/S5 |1224 predictions|656911 array0–7,after B|
| Final precision comparison + scoring checks |CPU-only|656912,after FP32 and prior scoring|

PanelB contains all51 discovery groups with either metric dropping more than.05
against either reference, plus51 unique nearest-length neutral controls. Neutral
means all four discovery paired deltas have absolute value<=.01; deterministic
ordering and ties use group ID. The102 selected targets never enter PanelA's
prevalence denominator. B-overlap native predictions are reused from A/references.
All seeds103/107/109/113 are K1 runs, never best-of-four. Total new production
predictions4016, excluding bounded preflight/replay calls.

Inputs/selection/code/checkpoint/runtime and old score files are hash-bound.
The new lock is separate from historical Stage0 artifacts. Local copies live in
reports/c4_s1_attribution_2026-09-27/execution/. No frozen test targets accessed.

## Preflight passed

Exact historical S2/S5 coordinate replay at both length extremes, all four seeds.
C4S1 unhooked/hooked replay exact, actual4 trunk and1 denoiser call and sigma[2560,0].
Controlled S1/S2/S5 share identical actual initial noise, first denoiser input and
conditioning hashes; dropout is off. Repeated controlled S1 is exact.

Native extension preserves historical dropout. Controlled comparison retains the
native Euler sampler, gamma0=0/eta1, resets sampler RNG from target+replica, and
replaces random rigid augmentation with centering+identity rotation+zero translation.
Initial and first-noisy tensors are saved per prediction. This new control is not
claimed to reproduce the random-augmentation baseline; within the controlled block
only the step schedule changes. Cross-block improvements cannot uniquely identify
which removed random component caused them.

## FP32 control

Installed runner keeps model parameters FP32; configs.dtype selects outer autocast.
Precision workers verify all parameter dtypes and identical checkpoint/runtime.
FP32 workers replay actual BF16 raw initial noise AND first-denoiser coordinates
exactly; this also eliminates precision differences in initial centering.
They assert runtime Pairformer/diffusion input dtypes contain no BF16/FP16 and
that autocast is disabled at those module boundaries. First target S1 replays exactly.
The FP32 code is separately frozen in code_precision_v1. Previous code_v1 unchanged.

Retain original TF32 policy(matmulFalse,cuDNNTrue) to implement the requested CLI-only
precision change. This is `fp32_cli`, not a claim of all-operator IEEE FP32. BF16
can already execute some diffusion operations in FP32; any benefit can arise in
conditioning as well as coordinate generation. Do not attribute it solely to the
last decoder or promote FP32 by selected-panel mean alone.

Report FP32-minus-BF16 within each S, changes to S1-minus-S2/S5 persistence,
full quality distributions, and forward time/peak allocation. Precision failures/OOM
are retained, not silently dropped from denominators. No claim that FP32 is GT.

## Analysis and remaining boundary

Report target-wise four deltas, mean,k=0..4 for thresholds-.05/-.10, per-seed
P01/P05/worst5%, and joint failure counts. Target-cluster bootstrap retains whole
seed/config blocks; crossed common-seed-column bootstrap is a sensitivity analysis.
Selected B results are diagnostic. Old AA lDDT includes same-residue pairs; TM is
Kabsch TM-style. Independent scoring verifies prediction hashes and shared atom
coverage/feature hashes. Focused statistics tests passed2 cases, including exact
threshold equality and per-target persistence. GPU preflight is additional evidence.

This batch resolves forward persistence, randomness controls and numerical precision.
It does NOT yet implement full soft-sequence backward: changing amino-acid atom
inventories and cached ESM conditioning still require an explicit relaxation contract,
plus removal of upstream final-cycle-only gradient guards. Existing pair-leaf gradients
must not be mislabeled end-to-end q gradients. No training follows automatically.
