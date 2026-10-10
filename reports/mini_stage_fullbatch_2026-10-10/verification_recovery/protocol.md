# Verification-only recovery of the full-batch experiment

The original four training and four scoring jobs completed. All four tensor
verifiers failed on import of `verify_stage_pair_recovery.NumpyMoments`, before
model construction or any verification forward. The original controller remains
`closed_with_failures`; the result follower's failure is retained. This is a
deployment omission, not evidence that a numerical comparison passed or failed.

Supply the committed, unchanged `scripts/verify_stage_pair_recovery.py` in a
separate, SHA-locked dependency directory. Its SHA256 is
`1671f75acb7ec3b190ec61aa34d326eb45fbde7a85663ab2f8dd1b8395081e2e`.
Run the unchanged, already locked `verify_stage_fullbatch.py` four times, once
per original arm/seed, serially on HIP4. Keep all numerical tolerances, all
48 sites and checkpoints 0/32/128, mismatch construction and hash checks.
There are 2,736 evaluation-only recovery forwards per run, 10,944 total if all
four complete. No backward, parameter update, S1, C4, recycle or ESM/MSA prep.

The new controller has a separate two-hour cap for each verifier, an import
preflight, exclusive new logs and a separate status file. It neither restarts
training/scoring nor changes any original controller, source, lock, checkpoint,
history, coordinate or score. Hash-protect the original evidence before and after
the recovery, including all checkpoint files. A failure is retained and cannot
be converted to success by suppressing a check or selecting another checkpoint.

Export can accept recovery only with four successful new verifications plus
the original eight successful training/scoring jobs and the four preserved
import-failure logs. Publish both controllers and the separately hashed
dependency, controller, recovery lock and result evidence. Label the export
`operational_recovery=true`; never rewrite the original controller as successful.
The scientific protocol, results and interpretation remain unchanged by this
operational repair. Completion of verification is not model promotion.
