# Global CA distance: TRAIN-only scale calibration v1

Locked before reading calibration results. No neural-model calls, parameter
updates, DEV coordinates/scores, source changes, or coefficient search.

Definition: observed same-chain CA pairs, sequence index gap>=24, no upper
GT-distance cutoff. Mean smooth-L1 of predicted minus experimental distances,
beta10 Å: e²/20 for |e|<10, otherwise |e|−5 (units Å). Average over pairs per
protein. Reference labels detached; no GT imputation or teacher-as-GT.
Native S2 auxiliary remains separately labeled and unchanged.

Use the32 original TRAIN probe IDs and two training noises600001/600011, exactly
at the retained512 common starting point saved in the original TRAIN423
`expanded/probe_0000`. All groups must belong to original TRAIN128 and TRAIN423.
Load native S2 coordinates from the existing training cache only. Preserve
same observed-mask/native-atom mapping and frozen original loss implementation.

Let a(g,s) be the L2 norm on OBSERVED CA coordinate rows of the gradient of
0.01*old_GT_aligned_MSE. Let b(g,s) be the corresponding norm of the unweighted
new global distance loss. Set

    lambda_global = median_g(mean_s a(g,s) / mean_s b(g,s)).

Require every b mean>1e-12, allfinite and all32 groups present. No clipping,
rounding, fallback value or after-the-fact exclusion; fail calibration if invalid.
Matching only the old CA-side budget avoids transferring the entire all-atom
coordinate budget to CA atoms. It does not match diffusion-parameter gradients,
optimizer updates or guarantees of convergence. The scalar will be frozen for
one later run; do not select by subsequent DEV scores.

For each case record unweighted losses, weighted old-term coordinate-gradient
norms both all-atom and CA, unweighted global norms, new-vs-coordinate/local/
teacher cosines (null for zero norms), pair counts and local/global term signs.
After computing the locked scalar, report weighted global gradient distributions
and ratios. FP32 prediction tensors match training; direction reductions use
FP64. Save finite vectors for independent norm recomputation. Three focused
unit tests establish masks, rigid invariance, tail response, derivative agreement
and chunk-reduction parity; they do not certify the whole folding model.

One HPC3 acd_u CPU-only job,8 singlethread workers, GPU hidden,20-minute cap.
Copied original objective code remains byte-identical. Hash-bind all code,
protocol, parent probe reports/coordinates, GT labels/mappings and teacher arrays.
Reuse existing cached GT supervision, check coordinates/masks against the original
experimental atom37 arrays. All64 cases must complete. No new training release
until calibration is complete and the candidate's GPU preflight passes.
