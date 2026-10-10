# TRAIN-only update audit of the closed stage-aligned pair experiment

Locked design2026-10-10 under the active model-performance goal. The eight-run
experiment4cd73afb remains closed. This diagnostic does not train a replacement,
extend any trajectory, tune a hyperparameter, decode structures, or inspect
development labels. It asks why updates do not consistently lower the declared
full TRAIN objective. Capacity and insufficient supervision are not assumed.

Use all four accepted n15 runs: Final/Hint x272001/272003, at0/4104/8208. The one
operational retry supplies Final272003, exactly as in the verified source map.
Each saved checkpoint includes native-suffix parameters and AdamW history.
Use its original27 TRAIN sites, all19 AA, q, FP32 function, inputs and labels.
No new ESM/MSA preparation, C4, recycle, S1, target intermediate generation or
test-panel scores. Candidate B_inputs/B_s and native reference remain frozen.

At each of these12 fixed states:

1. Compute each site's full19-AA objective and parameter gradient. Average
   site gradients in CPU FP64 to obtain G for the original site-equal objective.
   Record per-site norms, cosines, pairwise gradient Gram matrix and module
   contributions. Recover final and hint error means and AA-centered components
   using full-field FP64 error moments, verifying the algebraic decomposition.
   Baseline objectives must reproduce the saved frozen-checkpoint analysis.
2. Consider the next27 scheduled two-candidate batches, one per TRAIN site.
   At8208 this is a hypothetical next schedule cycle, not authorized continuation.
   Each calculation starts from the SAME checkpoint and AdamW state; no sequence
   of updates is chained. Record raw and clip1 gradients, and compute AdamW
   displacements with clip1 versus no clip for this one step only. The no-clip
   branch retains the original clipped-history moments; it is not a no-clip
   training trajectory. Both use originallr1e-4/wd1e-4/eps1e-8.
3. Compare G with every batch gradient and displacement. Average the27 raw
   gradients, clipped gradients and displacements separately. The two candidates
   per site are the predeclared schedule phase, not all19; record this sampling
   limitation and compare their average gradient with the full19-AA G.
4. Form four diagnostic directions: mean clipped AdamW displacement; mean
   unclipped AdamW displacement; one AdamW step using full G with clip1 and the
   same history; and -G scaled to the norm of mean clipped AdamW displacement.
   The mean displacements are counterfactual averages, not a proposed optimizer.
   Evaluate the complete513-candidate TRAIN objective at fixed fractions0.1 and1
   of EACH direction from the same original parameters. Record raw/common/AA
   errors, directional derivatives and actual rounded FP32 displacements.
   These fractions are finite-step diagnostics, never selected as a learning rate.

Positive G dot displacement is ascent to first order; negative is descent.
Compare first-order predictions with finite objective changes. A worse full step
and a better tenth step can support local step-size/curvature concerns for that
direction, not establish a global learning-rate solution. Compare raw/clipped
gradients and saved-history AdamW separately; high clip frequency alone cannot
prove causality. Good local descent does not establish multi-step improvement,
capacity sufficiency, transfer, geometry, selection quality or a speed result.

No predictor input can read target labels. All label requests must belong to
the27 TRAIN keys. Runtime can load historical metadata/reference memories but
no held target conditioning enters this audit. Native input/trunk/S1 calls
are prohibited. Validate original source and checkpoint hashes, identical
initial native function, unmodified native weights and reset predictor state.
Independent AdamW states must not alias; repeated probes must return identical
displacements. Save vectors and full per-site metrics at the audit runtime root,
not dense pair tensors or trainable model checkpoints in Git.

Budget:12 states x(513 full-gradient forwards/backwards +54 scheduled-batch
forwards/backwards +8x513 finite-evaluation forwards) =56052 candidate forwards,
6804 backwards. There are660 independent in-memory AdamW step calculations
(54 batch counterfactuals +1 full-gradient counterfactual per state), no accepted
training updates. Scalar/vector checks add no folding calls. Failed integrity
attempts are retained and separately counted. Do not restart for a bad outcome.

Four independent workers on HIP0..3 only; HIP4 available for a bounded preflight,
HIP5 is occupied and untouched, HIP6/7 unauthorized. Use HIP_VISIBLE_DEVICES
only, fixed native torch kernels and no precision change. Six-hour audit cap;
immutable code/protocol/source manifest before execution. Preserve every state
and both objectives; no favorable subset. Candidate cost and all extra work are
recorded. No claim that this is a zero-compute or zero-optimizer-step inspection.

Focused tests validate isolated AdamW-state probes against direct PyTorch steps,
FP32 parameter replay, gradient weighting and descent/ascent diagnostics on a
known quadratic. Full scientific TRAIN objectives and hashes are independently
checked against the closed experiment before interpreting results. A subsequent
training intervention requires a separate fixed protocol based on these results.
