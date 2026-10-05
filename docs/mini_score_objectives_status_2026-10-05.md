# A/B/C score-objective comparison — launch status, 2026-10-05

**Started, not completed. No transfer or model-promotion conclusion yet.**
The preceding repeated-context batch and objective audit remain closed at175552c4.

[Locked protocol](mini_score_objectives_v1.md) changes only the objective:
A raw globally scaled MSE; B centered prediction/teacher MSE; C centered MSE times
TRAIN-only inverse floored variance weight (meanweight1). No new teacher data,
network, activation, optimizer, steps or sampling choice.

Same32TRAINproteins128sites,19nonWTAA/site; original8confirmationproteins nowDEV.
Three objectives ×context/AA-only ×seeds231301/231303 =12fresh runs.
Each131072updates,1024fullcandidate exposures/site; allA/B/C initialparameters
verified identical per head/seed and equal the historicaln32initialstate.

Weights locked: linearq25centeredTRAINenergy floor9.30978555588385e-05,
min/max4.1324015031841234e-06 /2.6394331522371637, mean1.
No DEV/newnoise labels used to determine the floor/weights. Outputscale unchanged.
Centering both vectors does not provide teacher means to inference. B/C cannot
alone calibrate absolute mutant-vs-WT scores or20AAprobabilities.

Controller started2026-10-05 11:19:21UTC (19:19:21HKT), PID1503425.
Startup snapshot: fourA/Bcontext runs2560updates each; twoCcontext queued.
After sixcontext jobs, sixAA-only jobs run onCPU, then terminalevaluation,
independent audit and descriptive summaries automatically. No result-selected
checkpoint/seed, restart, extension or default model change.

Per-site gradient instrumentation observes everyupdate: before weighting/clip,
after simulated unweighted and actualweighted clip, counts/ratios in32768update
windows. This is same-state scalar-gradient accounting, not an alternativeAdamW
trajectory. 17tests passed, including actualTorchclipping-vector equivalence;
1066frozen sourcefiles match local snapshot. No existing training/model code edited.

Estimate at startup70–85minutes remaining for alljobs/evaluation/audit, based on
initial throughput and historicaln32walltimes; not a completion guarantee.
Live state is runtime `status.json`, terminal `execution.json` and
`independent_audit.json`. This document remains a historical launch snapshot.

Remote root:
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/score_objectives_v1_20261005`

Local metadata mirror:
`/home/husrcf/Code/onestepfold_runtime/score_objectives_v1_20261005`

[Lock/weights/startup checks](../reports/mini_score_objectives_2026-10-05/).
Full terminal reporting must separate TRAIN/DEV, eachseed/sourceAA,
B−A,C−B,Ccontext−Acontext, within-arm context−AA-only, rawregret/tails,
2V66fixedcases and selectednativegeometry. No historicalWT-znumber is imported.
