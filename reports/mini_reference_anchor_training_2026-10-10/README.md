# Reference-anchor training — completed paired comparison

Both original runs and all score/tensor-verification jobs have now completed.
See [terminal evidence](terminal/README.md) and the
[final report](../../docs/mini_reference_anchor_training_findings_2026-10-10.md).
The launch and interim records below are retained for provenance. TRAIN fitting
and weak decoded-response gains reproduced, but choice risk prevents promotion.

Two runs on HIP0/1, seeds272001/272003, fixed128 complete TRAIN gradient passes.
Protocol: `docs/mini_reference_anchor_training_v1.md`. Existing unanchored AdamW
controls are hash-bound in `training_lock.json`; their data, candidate exposure,
optimizer and initialization are matched. The extra reference branch means
compute and wall time are not matched.

Remote runtime:
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/reference_anchor_training_v1_20261010`.
Controller PID1015577, workers1015702/1015703. Training lock SHA256:
`13cda88bacb0bca93f93c59fad801428d120b37f124bcdc022d915127c4cdeff`.
Training deadline Unix1791630010.9576044. The controller scores completed runs
on CPU and verifies tensors serially on HIP4. No automatic restarts or extension.

Seventeen preflight tests passed both before installation and in the frozen
runtime. This directory originally recorded the launch. Its original process
IDs and deadlines are historical provenance, not active-job instructions.
The completed controller and independent checks are in `terminal/`.

The separately locked CPU follower waited for all six train/score/verify jobs,
checked hashes and arithmetic, compared every fixed node with its matched old
control, and exported results. It did not modify training code, parameters or
budget. Both held and training metrics remain required; nine repeatedly used
held proteins are development data.
