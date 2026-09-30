# TRAIN-only gradient-budget diagnostic v1

Lock before execution. Reuse existing original TRAIN32 × noises600001/600011.
Six states: retained512 shared initial; global-distance continuation at512,1024,
2048; coordinate-zero2048; expanded coordinate0.01 control2048. 384 saved outputs.
No folding calls, parameter updates, new predictions, DEV/validation targets,
coefficient selection or checkpoint selection. No change to production losses.

Use hash-bound original GT mapping/masks, full chemical supervision and nativeS2
auxiliary targets, exactly as the original calibration. NativeS2 is synthetic,
not experimental ground truth. Recompute original loss components in CPU FP32
at stored FP32 coordinates; reduce gradient inner products in FP64. Keep full
unweighted coordinate-gradient arrays for audit, including coordinate loss even
when inactive. All observed CA and all-atom spaces reported separately.

At every fixed state calculate three actual recipe sums: expanded (.01 coordinate,
no global); coordinate_zero (zero both); global_distance (zero coordinate,
.03290655679814053 global). Other weights stay locked. Save all raw Gram matrices,
term norms, total norm, norm-of-sum/sum-of-norms, signed projection on total and
cosine with the remaining terms. Zero gradients/undefined cosines stay null;
do not interpret norm fractions as additive percentages or parameter influence.
For summaries average the two noises per protein, retain individual results and
report medians/tails, signed cancellations and zero counts. Not an FD experiment.

Separately summarize existing global-training history using matched complete
first/last epochs (same group and seed) rather than unpaired run prefixes. Loss
magnitudes alone do not establish gradient dominance. Report actual CPU walltime,
eight worker processes with internal thread limits1, original input/source hashes,
all384 cases in denominator. Any failure stops summary release. Frozen raw outputs
must not be overwritten. HPC3 acd_u, CUDA hidden, no automatic retries.

Question: was coordinate-side supervision weak/conflicting along the archived
trajectory, and does matching CA norms hide a different all-atom budget? This
cannot by itself answer how gradients transform through diffusion or Adam; if
needed, next use a bounded parameter-space diagnostic, not an automatic weight
sweep. DEV quality from the prior experiment is not a weight-selection objective.
