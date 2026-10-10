# Reference-anchor training — execution record, results pending

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
runtime. This directory is initially a launch record. It must not be read as
a completed result or promotion. Recheck the remote controller and actual PIDs
before reporting progress; launch success alone is not training success.

The separately locked CPU follower waits for all six train/score/verify jobs,
checks hashes and arithmetic, compares every fixed node with its matched old
control, and exports results. It never modifies training code, parameters or
budget. Both held and training metrics remain required; nine repeatedly used
held proteins are development data.
