# Native Mini diffusion adapter: bounded engineering preflight

Locked before inference/updates, 2026-09-30, after51f2d387. This is preparation
for one-step denoising learning, not a training efficacy or generalization trial.
The geometry solver, its historical outcomes and production weights are unchanged.

Use1U07 (90 residues), the sole unused fully observed/native-compatible candidate
in fresh_contact_source_v1_20260930. Verify archived source hashes and sequence/
PDB/accession isolation to the fresh8 as well as inherited historical exclusions.
It becomes development/training infrastructure data, never independent validation.
Do not consume2B0A/2Z0J, reserved32 or oldY38 coordinates. One fixed new noise500009.

NativeFP32 ESM2-3B/Mini,4recycles,1student diffusion call; fixed identity noise,
augmentation/dropout/churn off, existing stableEuler sampler. Build conditioning
once with frozen pretrained weights. Generate the unmodifiedS1 andS2 reference
BEFORE installing trainable deltas. S2 is a synthetic reference, never experimental
GT or assumed clean chemistry. Record its GT accuracy and geometry separately.

Attach rank8 updates W+B@A to q/k/v/o and three transition matrices in each of
the8 token diffusion blocks (56matrices). A has local-seed Gaussian initialization,
B=0. All original weights, atom encoder/decoder, conditioning and Pairformer stay
frozen; optimizer may see only112new tensors. No input projection/ESM changes.
Parametrization preserves native module forward and direct weight access. It can
be merged into weights to remove adapter matrix products at deployment; verify
the actual merged prediction rather than assume equivalence.

Require bitwise nativeS1 parity at zero initialization. Make exactly ONE AdamW
update,lr1e-5,betas(.9,.999),eps1e-8,weight_decay0,global gradient clip1. No retries,
line search or checkpoint selection by quality. Engineering loss is equal-weight
proper-aligned observed all-heavy-atom MSE to fixedS2 and experimentalGT. Report
each gradient component, their cosine, finite/nonzero checks and before/after loss.
Alignment fits detached coordinates inFP64; no side-chain symmetry handling.
This smoke loss is NOT a final calibrated chemistry/design training recipe.

Verify all original model parameters remain bitwise unchanged; only declared
adapter tensors receive gradients. Save/reload the adapter and reproduce its
prediction exactly. ZeroingB restores nativeS1. Merge the adapter, restore native
state-dict keys, and require bitwise output parity. Check finite nonzero VJPs to
live continuous conditioning with merged frozen weights (not fullsequence proof).
No adapter gets promoted or deployed. Save all coordinate variants, initialization,
checkpoint, hashes, scores, gradient summaries, actual NFE/memory/time and failures.
Planned model counts:4Pairformer,10diffusion calls including2-callteacher.

One DiamondHill GCD, timeout1800s. Stop after this engineering preflight. A later
learning experiment requires its own train/validation split, GT and geometry
objective, fixed budgets and endpoint rules. No automatic longer training follows.

Implementation reference: [PyTorch parametrization semantics](https://github.com/pytorch/pytorch/blob/main/torch/nn/utils/parametrize.py),
including `leave_parametrized=True` when materializing weights. The runtime version
and module hashes, zero parity and merge parity are checked locally, not inferred
from documentation.
