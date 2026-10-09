# Mini single-context pair fitting evidence

Fixed TRAIN1W53 T37 /19candidates, pretrained/random x272001/272003. This is a
fresh feature-training diagnostic with the unchanged recovery model, not a new
readout fit or independent protein evaluation. See
[protocol](../../docs/mini_pair_candidate_fit_v1.md).

`manifest.json` hashes unmodified exported source artifacts. `training_lock.json`
binds the protocol, code, original input cache, scales and initial-state hashes.
`runs/` contains every fixed node's latent diagnostics, exact candidate exposures,
gradient traces and compressed per-output functional/geometry metrics. Full
checkpoints, residual tensors and coordinates remain in the source runtime root
recorded in the manifest. They are not omitted from evaluation.

`tensor_verification.json` records a separate FP64 stacked-tensor reconstruction
of every node's raw/common/AA residual statistics. `verify_results.py` verifies
source hashes, schedules, all historical controls and score arithmetic.
`analyze_results.py` creates `analysis.json` and the learning-curve figure without
choosing a winning checkpoint. Step304 matches old per-candidate exposure;
step8208 matches old total updates but has27times the local exposure.

Only one protein/site: no protein bootstrap, transfer claim, independent
confirmation or deployment speed claim. Nineteen AA and two noises are not
independent proteins. Preserve original failed v1 preflight evidence; no model
or label fit occurred before the missing-test packaging correction in v1b.
