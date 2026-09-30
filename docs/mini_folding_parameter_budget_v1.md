# Parameter-side budget v1, bounded TRAIN diagnosis

Reuse next_parameter_panel.json frozen in ec5330a8:8 existing TRAIN32 proteins,
lengths53–488,noise600001,retained512 andglobal_distance2048. No DEV, new data,
optimizer step, FD check, checkpoint selection or weight choice.16forwards,48VJPs.

Use unchanged runner, dense checkpoint loaders, train_folding_scale input loader,
C4 cachedconditioning/nativeFP32 diffusion_from_conditioning S1, actual TRAIN GT,
chemistry and S2 auxiliary targets. Replay every forward bitwise against its saved
TRAIN probe. Full288diffusiontensors/69,777,841parameters,not oldLoRA scope. Freeze
allothers. Compare weighted oldcoordinate(.01),global(.03290655679814053),and rest
(current noncoordinate/nonglobal sum). Obtain coordinate and parameter gradients
in each of3autograd calls. Preserve signed3x3Grams for each parameter tensor and
summed fullscope,raw component losses,timings,fullmodel state unchanged/RNG checks.

Grams accumulated in CPUFP64 chunks; no downsampledparameter projection or absolute
contributionfractions. Full large parameter arrays need not persist; retain per-
parameter Gram records, coordinate-side crosscheck with previous saved CPU arrays,
and hashes. Two focused algebra tests verify streaming/direct norms and cancellation.
No claim of Adam-preconditioned step attribution. Coordinate match alone is not
parameter-gradient matching. This panel omits>512chains and only one noise.

Four length-squared-balanced shards,worker0 gatesremaining3; all16 required, any
failure blocksinterpretation,no silentrestart. HPC3 acd_u,original frozen code copied
into isolated root; only newdriver/helper appended. No production modifications.
Run to completion once, then decide next bounded training intervention using TRAIN
evidence. Do not automatically expand another derivative matrix or read DEV to tune.

## Engineering retry record

Initialworker662636 stopped on strict3OND replay, no VJPs completed;662637–639
were dependency-cancelled. Three-forward diagnostic662640 hadmatchingparameter
fingerprints but coordinate differences(max .00216/.00813/.03138Å). Subsequent
four-forward662642,withinput noise/conditioning readback hashes andRNG checks,
replayed all four exactly,including grad-enabled and repeatedno_grad modes. Both
ran onACD1-12. This is not a proven operator/root cause or a relaxed tolerance.

Retry retains strict bitwise guards,adds inputreadback/synchronization/environment
logging,and uses originaltraining/evaluation nodeACD1-18. No scientificsettings,
inputs,weights,targets or gradientformula change. Isolatedretry directory preserves
firstfailedcode/lock/logs.16plannedforwards/48VJPs unchanged;thefailed1forward plus
7diagnosticforwards are additional engineeringcost,not hidden as free.
