# Full diffusion scope preflight v2: execution equivalence

Frozen after the v1 preflight and the four-forward scope replay diagnostic;
before the new longest-input backward/update run. The v1 exact-scope condition
failed and remains failed. Token-dense already passed both original inputs.

On the first TRAIN input, full scope changes coordinates by max4.6492e-5Å
before any update. Full scope grad/no-grad/repeat outputs coincide; all288
selected gradients are present, finite and nonzero. The first captured mismatch
is at atom encoder outputs, not conditioning outputs. This locates a numerical
execution difference, not an identified faulty operator or backward error.
The first replay instrumentation failed because a hook mistook checkpoint
recomputation for a new probe; retain that attempt and its corrected rerun.

Run ONLY `diffusion_dense` on the SAME two TRAIN inputs (280/968 residues),
independently from public parameter values. No target/seed/quality selection.
Each input has six forwards:
1. All parameters frozen: exact original cached native coordinate replay.
2. Selected native parameters trainable: backward on the unchanged recipe.
3. One engineering AdamW step: forward retaining training parameter flags.
4. All parameters frozen: actual inference output of the same updated weights.
5. Public parameter values restored, frozen: exact original cache replay.
6. Partial checkpoint reloaded, frozen: exact step4 replay.

Require max-coordinate training/inference arithmetic difference ≤0.001Å both
before and after the step. This is an explicit engineering precision bound,
chosen after observing the first-input discrepancy; it is NOT a new quality,
chemical, FD or design acceptance threshold and NOT independent confirmation.
All exact frozen-native/reload tests, finite gradient coverage, RNG preservation,
excluded-parameter equality and native fixed Fourier flags remain required.
Report the actual differences rather than just pass/fail. Twelve S1 NFEs total.
No production backend/model change, no quality-based selection, no training reuse
of engineering checkpoints. The old v1 result must not be reclassified as passing.
