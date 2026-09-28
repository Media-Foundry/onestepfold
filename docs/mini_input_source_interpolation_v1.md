# Hard-neighborhood × upstream input-source forward diagnosis

Locked before outcomes. Two development cases:8BZN and control9XVW from the
previous fixed-chart diagnostics. No training, optimization, objective smoothing,
acceptance-threshold changes or frozen-test use. Frozen MiniESM, C4/S1/K1, FP32,
fixed native atom inventory, identity-keyed noise211, no dropout or augmentation.
Conditioning is packed identically for all forwards.

Alpha:0,1e-4,1e-3,.01,.05,.10,.20,19/(exp(4)+19). The last value is the mathematical
old initialization; additionally replay the actual FP32 softmax(4*onehot) as a
separate full-soft row to quantify probability-rounding differences.

Stage1: native HHH baseline, E-only, R-only,C-only,ERC. HHH is constant in alpha
and is evaluated in every worker as an endpoint/replay control. R modifies only
restype/profile (as actual existing implementation); deletion_mean/MSA unchanged.
C modifies ref_pos/ref_charge/ref_mask/ref_element/ref_atom_name_chars using the
existing zero-filled reference bank. No renormalization, alignment or identity fix.
E uses newly computed live ESM2-3B embeddings per probability tensor. The frozen
embeddings are shared only for bit-identical prepared inputs, with packet hashes.

Check alpha0 fields against native and soft-ESM onehot against native ESM forward.
Require alpha0 coordinates bitwise equal to same-layout baseline. Recompute
reference d_lm/v_lm/padding, full4cycle conditioning, diffusion pair and atom caches.
Instrument input and diffusion atom cache builders to verify both consume every
current reference field and d_lm/v_lm. Graph tensors must remain equal to native.

Report full geometry, nonbonded minimum, tracked pair, aligned AA/CA displacement,
input/conditioning deltas, reference mask and intraresidue bond contraction.
Export residue42/43 reference-bank contributions for8BZN (37/194forcontrol),
including absence and unaligned/aligned backbone frame comparisons. Do not modify
templates based on these diagnostics. Supplement prior saved clash coordinates
with rho(h); retain original FD criterion and signed contribution interpretation.

Only if single sources fail to account for full-soft failure, add ER/EC/RC on the
same fixed alpha grid as a labelled interaction follow-up. Do not select a new
model or estimate prevalence from these two cases. Each worker bounded30minutes;
ESM preparation shared per target to avoid redundant extraction. Up to8GCD.

## Execution amendments (original protocol preserved remotely)

The initial forward jobs stopped before model execution at source hash checks:
local soft_sequence_chart.py includes an unused boundary helper absent from the
frozen runtime. Verified the sole difference and corrected manifest binding,
retaining lock.v1.json/failed logs and prepared packet parent hashes. No field
formula, data, alpha, model or acceptance threshold changed.

Interaction trigger was recorded before inspecting scan outcomes: at the last
alpha ERC tracked-pair distance<.1A and all singles>=.1A. This is an attribution
pattern, not a design threshold. It fired, so ER/EC/RC were run on the same grid.

After combinations, bounded location follow-up used8BZN only: exactly positions
42/43 versus their complement, alpha0/.20/.2581587, E/R/C/ERC. This implements the
user-proposed local-versus-other check, with no new chemistry interpolation. The
number of softened sites differs; no per-site importance comparison is claimed.

Final:138 coordinate records audited, all jobs exited0 after the manifest repair.
See docs/mini_input_source_findings_2026-09-28.md for conclusions and limitations.
