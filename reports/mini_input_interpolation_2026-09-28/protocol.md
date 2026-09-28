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
