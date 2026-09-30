# Native dense terminal evaluation v1

Frozen during the already-locked two-arm training, before terminal predictions.
Training plan remains `mini_diffusion_dense_learning_v1.md`; no new configurations,
seeds, targets, acceptance thresholds or validation-set reuse.

After both workers and `audit_dense_diffusion.py` finish successfully, verify their
locks/checkpoint hashes. Read only the two fixed512-update terminals. Native partial
weights use a schema-specific loader that validates scope, shape, dtype and finiteness
BEFORE copying any value; frozen excluded parameters and native state keys must remain
unchanged. No adapters are installed for dense arms. On each evaluation worker,
check exact public frozen replay and exact loaded/reloaded output replay.

Eight GCDs evaluate all TRAIN128 × two old noises, with frozen cached C4 conditioning,
identity-bound atom noise and native FP32 C4/S1 inference. Models:
native_s1, native_s2, archived calibrated_high LoRA, token_dense, diffusion_dense.
The768 existing native/S2/LoRA predictions are hash-verified and copied;512 new
terminal predictions plus56 engineering replay NFEs are required. These are128
proteins, not1280 independent samples. Cache cost is not end-to-end inference cost.

Recompute all1280 predictions with the same observed-GT AA/Cα metric, atom identity
and mask mapping, typed connection diagnostics and full-inventory severe-overlap /
checked chirality measures. An independent bounded dense-distance implementation
cross-checks AA/Cα for every prediction. Verify all768 reused control coordinates
AND score records against their archived results. Keep failures in the denominator.

Primary: diffusion_dense−token_dense, protein means over both noises, followed by
10000 protein bootstrap replicates with fixed seed20260930. Report full mean/median,
P01/P05/worst5% paired tails, severe regressions and new damage to initially good
structures. Report both arms against nativeS1, nativeS2 and the old LoRA reference.
Those intervals are descriptive for this fixed TRAIN panel/noise pair, not evidence
of generalization or multiple-comparison-controlled discovery.

Also report parameter changes, common56-matrix changes, clipping, elapsed time,
memory and both unaligned and proper-aligned coordinate changes. There is no model
selection on intermediate checkpoints and no post-hoc budget extension. Old LoRA
used a different LR/parameterization, so it is not a pure low-rank capacity contrast.
No new aggregate chemical/design/deployment pass is introduced.
