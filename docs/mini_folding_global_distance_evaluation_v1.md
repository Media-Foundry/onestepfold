# Global-distance candidate: fixed-terminal execution v1

Locked execution supplement to mini_folding_global_distance_training_v1.md,
while training662548 is still running. No change to training/code/data/noises.
Release only after global_training_audit.json and job662549 complete successfully.
Candidate is update2048 from that audited lock, semantic name global_distance,
internal checkpoint arm expanded. Do not select intermediate checkpoints.

Reuse all4550 hash-bound outputs from the completed coordinate evaluation:
native_s1,native_s2,retained,expanded,coordinate_zero. Add910 candidate predictions
on the same455 proteins×2 assigned noises. Eight original length-squared-balanced
shards each perform4 engineering calls: public model, public-copy parity, candidate
load and exact reload. Total942 new calls, then5460 complete scores against the
same experimentalGT/masks/identities. Worker0 gates the other seven. Original
inference and per-case scoring code is unchanged; reuse is explicit for TRAIN/DEV.

Keep originalTRAIN128, addedTRAIN295 and observedDEV32 separate, protein means over
both noises, no best-of-noise. Central contrasts global_distance−coordinate_zero
AND global_distance−expanded. Also global_distance−retained/nativeS1/nativeS2;
retain coordinate_zero−expanded,expanded−retained,nativeS2−nativeS1 context.
Reuse same bootstrap seed/replicates. DEV32 is not new independent confirmation.

Report AA/CA-lDDT, paired low tails and drops below−0.05, proper GT-alignedCA RMSD
with upper paired tails, chemistry and newly damaged outputs, typed connections,
three-arm TRAIN32 curves, clipped updates, exposure counts and actual runtime.
Inference timings are cached-conditioning diffusion only, not whole-fold latency.

After scoring, run the same existing-coordinate extent analysis on all5460
outputs, without another model call. Bind full scored-output provenance. Its
primary per-protein diagnostic pair is now global_distance versus coordinate_zero;
all lock contrasts are still summarized. Preserve GT-based distance bands,
sequencegap>=24, missing-band nulls/support counts, fragment32 and remaining95%
fixed-alignment definitions. Append far-distance MAE/signed bias, radius ratio and
local/global extent to the final Markdown. These are descriptive diagnostics,
not new promotion thresholds or independent confirmation. Replay CA RMSD to1e-8Å.

Chain: audit→prepare→worker0→workers1–7→score/cohorts→extent→report.
HPC3 acd_u, no auto-requeue, invalid dependencies cancel. CPU stages hide GPU
although the partition may reserve one. Failures retain full denominators and
stop downstream release; no silent restart or subset reporting. No ESMC interface,
repair, design, optimizer/noise/data change or automatic incumbent replacement.
