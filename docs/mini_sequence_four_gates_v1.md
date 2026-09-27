# Four sequence gates — 2026-09-28

The user confirmed these four gates: native hard-input replay; sequence-gradient
numerics; matched S1/S2 optimization; hard-sequence rebuilding with independent
noise. Retain pretrained Mini-ESM v0.5.0, C4, K1. No adapter training.

## Implemented input contract

Frozen native ESM2-3B now accepts L×20 amino-acid probabilities through expected
input embeddings, native token-dropout scaling and all36 transformer layers.
Activation checkpointing preserves input gradients. MI250 preflight: one-hot final
representations exactly match native token inference; logit gradient finite.

A native-inventory chart is built from the current argmax sequence. Both restype
and no-MSA profile depend on probabilities. Reference positions, charges, masks,
element and atom-name encodings are interpolated from native amino-acid templates
on the current atom-name inventory. The current native conformer's row is retained
exactly at its one-hot endpoint. Atom-pair reference preparation is differentiable;
upstream performs this inside no_grad. ESM is recomputed for every changed q.

This is a piecewise relaxation: an argmax change rebuilds the native chemical graph.
Missing candidate atom names contribute zero reference features within a chart.
It is NOT a globally smooth relaxation of variable atom count, and mixed reference
features are not asserted to be physical conformers. Exact hard endpoints and local
finite differences do not prove continuity at chart boundaries. Deployment remains
unaccepted until boundary effects and actual task performance are assessed.

## Gates and outputs

1. Rebuild native sequence features and compare native ESM inference and original
   runner S1 against soft one-hot C4/S1. Require embedding/feature error≤1e-5 and
   coordinate max error≤0.002A. Stable Euler algebra avoids high-noise cancellation;
   this is numerically, not bitwise, equivalent to the native update.
2. Both S1/S2: finite/nonzero logit gradients, exact repeatability, three centered
   logit directions, central differences h=.3,.1,.03,.01,.003. Require two adjacent
   h values within5% relative plus1e-6 absolute tolerance in every direction. No
   best-of-seed, no cached ESM shortcut. This gate is local to an unchanged argmax.
3. From identical logits (4×native one-hot), separately optimize with S1 or S2 for
   50 Adam updates, LR.2, grad clip1. Cross-score the same q under both samplers at
   initial/final/every10steps. Log sequence, mutation count and topology changes.
4. Harden final sequence, rebuild all native input features, replay native runner,
   then evaluate baseline/final sequences under S1/S2 and noise seeds103/107.
   Atom-name-keyed initial noise preserves common atom noise across graph changes.
   Save full coordinates, atom names, residue indices and sequences.

The current objective is nonlocal Cα contacts with Cα clash and chain penalties.
It is an implementation diagnostic, NOT interface quality, affinity or validated
binder design. Reports retain individual gate results and set deployment_accepted
false; experiment completion must never be mistaken for acceptance.

## Execution

DiamondHill root `/media/PM982/onestepfold/mini_sequence_gates_v1_20260928`.
First target is the previously used shortest diagnostic protein100residues.
Immutable snapshot code_gates_v1 and source hashes gate_source_v1.json.
Two parallel GCD0/1 workers: PID1674776/S1 optimization, PID1674777/S2 optimization.
Each bounded3600s. Each independently executes all four gates and writes an atomic
report throughout. No larger panel launch before the first hard-replay gate works.
Failure traces and incomplete reports are preserved. Check process handles and
report stage rather than inferring success from launch.

Local tests6pass: native Pairformer body preservation, detached-recurrence detection,
ESM hard-input formula, checkpointed gradient equality, chemical probability path
and chart guard, and finite-difference acceptance rejecting a deliberately detached
term. GPU scientific results remain separate evidence.

## First completed execution

Both50-update arms completed on the100-residue target. Hard endpoint feature and
ESM errors0; native coordinate replay max≈0.00074A. Three-direction local gradient
gates passed for both S1 and S2, repeated gradients identical. Logit-gradient cosine
was−0.702 at the shared soft start for this specific contact objective, not a
universal S1/S2 gradient relationship. Soft objectives decreased for both arms.

Hardening produced1 mutation for S1 optimization and6 for S2. Both mutated
sequences passed rebuilt-native replay. However neither arm passed own-sampler
improvement under both noises. S1 optimization hard-loss delta was−0.000856 at
seed103 but+0.003703 at107. S2 optimization was+0.008609/+0.001496 under S2.
Thus stage4 practical performance failed in this first probe despite correct input
and gradient plumbing. Reports and full hard coordinates copied to
reports/mini_sequence_gates_2026-09-28. No deployment acceptance claim.

CPU geometry audit includes native bond-length error, peptide C–N error, chirality
and nonbonded heavy-atom pairs below1A. These are reported separately from the
coarse Cα objective. They can reveal proxy optimization that worsens chemistry.

## Bounded diagnostic continuation

V2 adds chart-boundary measurements: at an argmax change, evaluate the identical
soft q under old/new chemical inventories and report aligned Cα RMSD/loss jumps.
Six GCD0–5 workers compare S1/S2 optimization for8BZN(125),9QR4(362), and an original
neutral control nearest200residues. This is a diagnostic subset, not a prevalence
estimate. Source code_gates_v2; targets locked in gate_cases_v2.json. PIDs1677382,
1677383,1677384,1677386,1677388,1677391. Each bounded5400seconds. Scope is unchanged;
no training, no test-set access and no sampler/architecture tuning on the panel.

## Independent artifact acceptance

The final scorer now calls sequence_gate_audit.validate_run. It rejects missing
updates/cross-scores, malformed logits, sequence mismatches, fewer than3gradient
directions, overwritten numerical acceptance, missing/duplicate hard-noise records,
missing coordinates and disagreement between coordinate-recomputed and reported
loss. It hashes all10required artifacts. Initial100-residue outputs independently
reproduce the reported hard losses on CPU within1.5e-8. Eleven focused tests pass,
including tampered artifact/loss/finite-difference acceptance rejection.

A CPU-only finalizer PID1679383 waits on the actual remaining V2 worker PIDs;
it does not infer completion from stale state files and never restarts workers.
It writes final_audit_v2 only after all eight optimization arms are terminal and
report completion. Numerical/scientific failures are valid experiment outcomes
and remain false in the final report. See mini_sequence_gate_completion_audit.md.
