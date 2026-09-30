# Next C4/S1 candidate: experimental global-distance supervision

Implementation plan, **not a locked training protocol or a launched experiment**.
The completed coordinate-zero ablation gains local lDDT/chemistry but loses global
GT accuracy. Existing-coordinate analysis shows persistent errors after worst5%
exclusion and increased long-distance underestimation. Preserve the retained512
reference; do not promote coordinate_zero or sweep its coordinate coefficient.

One candidate: retain the coordinate-zero recipe and add a robust experimental-GT
CA distance term. Use observed canonical CA identities only; no teacher coordinates
as GT, no invented missing atoms. Include sequence-separated CA pairs (gap>=24)
without an upper GT-distance cutoff. This covers the global span missing from the
15 Å local-distance neighborhood while leaving local chemical supervision intact.
Use per-protein pair averaging; do not let a longer chain automatically have a
larger scalar loss. A Huber-style error can limit the gradient dominance of large
individual residuals, while remaining responsive outside lDDT's neighborhood.
It does not guarantee correct topology or better lDDT.

Before a training protocol is locked:

1. Implement the label/loss path in a separate module; test mask isolation,
   rigid invariance, proper response to compressed/rotated fragments, finite
   derivatives and empty-pair handling. Reuse the current data contract.
2. On the original TRAIN32 at retained512, using saved coordinates and GT only,
   report loss magnitudes and coordinate-side gradient norms for the old global
   coordinate term and proposed distance term, including CA-specific versus
   all-atom budgets and the existing local/teacher terms. No network forward or
   backward is needed for this calibration. Choose one scale by a declared
   TRAIN-only rule BEFORE evaluating any trained candidate. Gradient-norm
   matching is calibration, not evidence of equally effective parameter updates.
3. Freeze one candidate and exact scale, same retained512 parent, TRAIN423,
   sample/noise order,2048updates/8192exposures and288diffusion tensors. Keep
   ESM2/C4 frozen, C4/S1/K1 deployment, existing GT local/chemical and S2 auxiliary
   terms. Do not chain from coordinate_zero terminal or change data/optimizer.
4. Verify untrained forward equivalence and new-loss finite selected gradients
   on the existing shortest/longest TRAIN engineering cases before release.
5. Evaluate the single fixed terminal with the same complete455 comparison,
   reusing archived reference predictions. DEV32 remains development; new
   independent confirmation is still required for promotion. Compare AA/CA,
   globalRMSD and paired tails, chemistry/new failures, and long-distance errors.

No automatic promotion from a positive lDDT mean; report remaining global and
chemical tradeoffs. No coefficient grid, new source admission, ESMC interface,
LoRA, repair, design task, or restart of numerical-backward diagnosis in this
candidate. ESMC remains a subsequent separate matched-condition experiment.

The current analysis supports testing this intervention, not its success. If it
merely trades the same errors differently, preserve the negative result and
reconsider the recipe rather than indefinitely extending the run.
