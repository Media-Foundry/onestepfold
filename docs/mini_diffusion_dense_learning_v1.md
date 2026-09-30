# Native dense diffusion training scope comparison v1

2026-09-30, locked after scope engineering preflight, before training.
No new geometry gate, production precision change, width/LR grid, or validation
selection. The deployment contract remains pretrained Mini C4/S1/K1.

Compare public native weights with two update scopes, independently initialized:
`token_dense` updates the56 token matrices (47,185,920 elements) formerly targeted
by rank8 LoRA. `diffusion_dense` updates all288 natively trainable diffusion
tensors (69,777,841 elements). Native fixed Fourier parameters remain frozen;
ESM, input trunk, Pairformer and confidence remain frozen. No LoRA is installed.
The extra scope includes conditioning, atom encoding/decoding and other token
parameters; this comparison cannot assign any benefit to one specific module.

Reuse exactly the previously frozen TRAIN128, 16-epoch order, two training noises
600001/600011, 2048 protein exposures, accumulation4 and512 AdamW updates. Use
calibrated_high's weights with smooth-lDDT width0.1Å:
0.01A + D + 1.505408125612628B + C + 0.0006600251156855778R
+ 0.025476389066842815T. Read actual exact coefficients from its locked JSON.
GT is experimental observed structure; T is the explicitly synthetic frozen S2
auxiliary, not experimental truth. Atom/mask/chemical definitions do not change.

BOTH dense arms: LR peak1e-5, linear warmup32, cosine to1e-6 at512; Adam beta
(0.9,0.999), eps1e-8, weight decay0, clip gradient norm1. No early stopping,
checkpoint selection or extension based on observed quality. Two GCDs in parallel.
This is equal exposures/updates and identical optimizer settings BETWEEN dense
arms, not equal FLOPs, memory, update norm, or elapsed time. The archived LoRA
calibrated_high used peak1e-4 and is a practical reference, not a rank-only causal
comparison. Do not tune a dense LR based on this result.

Engineering evidence is retained separately: token scope passed exact replay;
full scope v1 failed bitwise cross-scope replay, and explicit v2 establishes exact
frozen native/checkpoint replay plus ≤0.001Å scope-dependent arithmetic bounds.
Observed full-scope differences were4.0–4.65e-5Å, with all selected gradients
finite/nonzero in two probes and longest-input allocated peak16.23GiB. Training
must not load any engineering-step checkpoint. Audit all excluded parameters,
native keys, random streams, selected gradient coverage, initial fingerprints,
data order and all optimizer state steps. Save a rolling checkpoint at128 updates
and terminal512; old intermediate optimizer states need not be retained.

After both arms finish and the training audit passes, evaluate terminals on ALL
TRAIN128 × both frozen noises. Primary comparison: diffusion_dense−token_dense.
Also report each versus native S1, frozen S2 and archived calibrated_high LoRA,
using the exact same cached conditioning and existing scoring definitions.
Report protein-level paired AA/Cα distributions and intervals, degradation tails,
new severe collisions/lost checked chirality, full geometry and connection
diagnostics, actual costs and parameter update size. All failures remain visible.
Do not revisit the already-revealed validation32 or protected historical panels.
No new acceptance boolean. Training-set benefit is NOT generalization or design
utility, and cached conditioning is NOT live soft-sequence gradient validation.

The test asks whether allowing native diffusion parameters to move can improve
the current quality/chemistry tradeoff at this fixed fitting budget. A negative
result does not prove one-step capacity insufficient; a positive result only
justifies a separately locked fresh confirmation after assessing damage tails.
