# Mini post-recycle pair recovery

Source experiment: DiamondHill
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/pair_recovery_v1b_20261009`.
The predictor consumes each candidate's cached native last-recycle output and
WT3 mutation-anchored pair features. It changes only the final pair tensor.
Target C4 pair is a training label, never a predictor input. Native inputs,
single, S1, chemistry, and reference caches remain frozen.

`training_lock.json`, `protocol.md`, and `preflight.json` specify the fixed
experiment. `runs/{pretrained,random}/{272001,272003}` retains every training
step and both fixed checkpoints' evaluation records. Checkpoint weights and
coordinate NPZs remain at the source; the evaluation manifests hash each file.
`scores_*.json.gz` contains every candidate/noise's task, fidelity, geometry
transitions and continuous chirality measurements. These are development data.

The initial `pair_recovery_v1_20261009` launch is retained in `failed_launch`.
Random-arm initialization did not reproduce because native truncated-normal
initialization also reads NumPy through SciPy. Its two pretrained arms logged
15/22 updates before the controller stopped all workers; neither reached any
quality evaluation. Corrected runs seed/restore both streams and restart all
arms, preserving the original architecture, data, objective and budget.

`cache_build` records 912 native last-recycle cache generations and 1,824
bitwise baseline S1 replays. No new teacher generation or sequence preparation
was needed. Source files are copied verbatim and SHA256 checked by
`manifest.json`. `verify_results.py` independently recomputes ranking and
regret, compares exact/disabled/oracle controls with the previous audit, and
checks exposure, TRAIN-only scales, residual decompositions, geometry and tails.

The preliminary timing in `preflight.json` measures the recovery component,
one native last recycle and S1 separately on a short-chain case. It is not a
new complete-workload speed result. No model is promoted by these timings.
