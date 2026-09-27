# Matched H100 / MI250 precision replication

User requested DiamondHill replication alongside HPC3. Same Mini-ESM checkpoint,
102 diagnostic targets, seeds103/107/109/113, C4, S1/S2/S5, K1, dropoutoff. Both
BF16 and FP32 are run on DiamondHill,2448 predictions. This is a selected diagnostic
panel, not an unbiased prevalence study. No training or ESM feature re-extraction.

## Corrected HPC3 FP32 audit

Original FP32 array656911 failed all8 workers before accepting predictions; final
score656912 cancelled by dependency. The assertion that CUDA autocast must report
`enabled=False` in FP32 was incorrect for PyTorch2.7.1. A diagnostic job656983
captured FP32 Pairformer inputs under enabled autocast, with FP32 diffusion inputs
and disabled autocast. Its exit is an intentional stop after trace capture.

The corrected check records autocast target dtype and actual module input/output
dtypes: enabled autocast is accepted only when its target isfloat32, and outputs
must remainfloat32. No BF16/FP16 module input is permitted in the FP32 arm.
This changes the auditor, not precision settings, weights, data or predictions.
Corrected code frozen as code_precision_v2. Preflight656987 completed successfully;
array656988 and final CPU scoring656989 replace the failed precision run.
Preserve all v1 failure artifacts. The FP32 CLI arm retains matmulTF32False,
cuDNNTF32True as previously locked; do not call it all-operator IEEEFP32.

## DiamondHill execution

Root: `/media/PM982/onestepfold/c4_s1_precision_crosshost_v1_20260927`.
Controller PID1664120, script run_diamondhill.py. Data bundle~33GiB,1453 hashed files;
all original packets and BF16 random-input arrays copied from HPC3, verified before
GPU execution. Model weights are already present on DiamondHill and hash-checked.
All seven pinned upstream Python module hashes must match HPC3; Torch/HIP versions
are recorded separately. Local source snapshot code_cross_v1 is immutable.

Preflight uses shortest/longest B targets at both precisions and S1/S2/S5, checking
exact same-host replay and common conditioning across schedules. Both raw initial
noise and the first actual denoiser input are replayed from HPC3 saved arrays.
No assumption that CUDA/ROCm RNGs with the same seed generate identical tensors.
Same-host replay must be exact; cross-host coordinate equality is not required.

After preflight success, launch8 processes with ROCR_VISIBLE_DEVICES0..7,one GCD
each,PyTorch/numeric CPU threads1. Per-worker90minute hard timeout; preflight30min.
Expanded allocator enabled on MI250; no RAM offload or cross-GCD memory pooling.
Each worker runs both precisions over its fixed target/seed shard. Model parameters
are frozen. First S1 target repeats within each precision before further predictions.

The controller then performs CPU-only experimental-GT scoring and pulls accepted
HPC3 FP32 per-target scores (wait<=1hour). Final output final/report.json,
final/per_target.csv and final/acceptance.json. All4896 target/seed/S/host/precision
entries are required before cross-host report acceptance. All required GT tar files
were checked present before GPU launch. No inference receives GT coordinates.

Report separately:
- Within H100: FP32 minus BF16.
- Within MI250: FP32 minus BF16.
- MI250 minus H100, at each fixed precision.
- S1-minus-S2/S5 persistence per host/precision, plus time and memory.

Cross-host differences mix Torch2.7.1/CUDA12.8 and Torch2.12dev/HIP7.14, their kernels,
and hardware. They are stack differences, not a pure hardware causal effect. Timing
is diagnostic with fixed cached inputs and dtype instrumentation; not a matched
end-to-end folding or ESM extraction benchmark. Fixed conditioning features mean
this experiment excludes language-model extraction precision differences.
