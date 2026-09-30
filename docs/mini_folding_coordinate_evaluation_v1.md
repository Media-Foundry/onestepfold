# Coordinate-weight ablation: fixed-terminal execution v1

This execution supplement freezes the terminal comparison before the candidate
finishes training. The scientific contract remains
`mini_folding_coordinate_ablation_v1.md`; no training setting changes.

Only `coordinate_zero`, the audited update-2048 terminal from job 662470, is
newly predicted. Its checkpoint retains the internal arm name `expanded` but
must bind the new ablation lock. Reference `expanded` is the previously completed
coordinate-weight-0.01 control, not the new candidate. Both start from retained512.

Reuse all 3,640 hash-verified reference coordinates for native S1, native S2,
retained512 and expanded2048 from the completed scaling evaluation. Bind their
worker reports through its archived execution manifest. Experimental GT, atom
identities, masks, chemistry definitions and per-case metric code stay unchanged.
All 455 proteins retain both assigned noises; there is no best-of selection.

Eight length-squared-balanced inference shards each run four engineering NFEs:
one public baseline, one public-copy parity, one candidate load and one candidate
reload. Worker 0 must finish successfully before the other seven are released.
Total new calls: **910 prediction + 32 engineering = 942 NFEs**. Reused predictions
are copied and hash checked, not counted as new inference. All 4,550 outputs are
rescored against experimental GT with the existing independent distance check.

The three cohorts are original TRAIN128, added TRAIN295 and
**observed_validation32**. The last cohort has already been seen and is development
evidence; it is excluded from optimization but cannot establish fresh confirmation.
Primary contrast is coordinate_zero minus expanded; also report differences from
retained, native S1 and native S2, and the existing expanded-minus-retained and
native S2-minus-S1 contrasts. Preserve per-noise results, protein means, intervals,
tails, chemistry, RMSD, typed connections and newly introduced failures.

Pipeline: successful training audit → preparation/provenance checks → worker 0 →
seven parallel workers → independent CPU scoring → completed-score report.
No failed/timeout case may be dropped from denominators. No changes to the
candidate, noises, thresholds or membership during execution; no automatic model
promotion. Report inference timings as cached-conditioning diffusion only.
ESMC, output repair and design remain outside this matched comparison.
