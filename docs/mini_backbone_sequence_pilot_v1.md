# C4/S1 fixed-checkpoint sequence gradient and target-backbone utility pilot

2026-10-01. User fixes C4 permanently for this mainline; S1/K1 per structure
evaluation, sequence search may iterate in future. This batch has ONE proposal
round only. No training, recycle compression, repair, confidence objective, ESMC
bridge, binder task or repeat of closed Y38/position-utility candidate batches.

## Roles and prior evidence

Fixed2048 SHA3bee481ca3124b829eea476d1f2c9db18dd29965170524e4f4d5390dbb8cb509
is a development checkpoint, not a deployment model. Retained512 remains the
global-quality reference; diverse is archived. Existing local FP64 and original-q
composition evidence is positive at the OLD tested checkpoint/control, not an
automatic certificate for fixed2048. Old FP32 FD failure records remain, with
their demonstrated secant-precision limitation. Do not mechanically repeat FD.
Old position utility already yielded selected confirmation success0/4 under a
monomer contact objective. This experiment changes the task to target backbone.

## Task and selection locked before prediction

Use four TRAIN423 parents, length80–160, excluding PDB2FIP/1BFT/1QSM/5CPG,
8BZN/9QR4 and the old194-residue control by the length restriction. Sort eligible
group IDs by SHA256('backbone-sequence-v1:20261001:'+group_id), take first4.
No selection by model quality, chemistry or gradient. These are development
proteins, not held-out sequence generalization. Failures remain in denominators.

Observed experimental parent CA coordinates define a REQUESTED target backbone.
All observed pairs with residue separation>=3 enter mean Huber distance error
(delta1Angstrom). No contact/distance cutoff. This asks whether substitutions
better preserve this desired backbone under prediction; it does NOT assign mutant
experimental GT or prove mutant stability, foldability, binding or inverse-folding
generalization. Full target/mapping/masks and hashes are locked; mutant length
unchanged, residue indices map directly. No mutant all-atom GT scoring.

## Stage A: checkpoint-specific input audit (four parents)

Native FP32 weights all frozen; live ESM2, complete ERC, four full recycle paths,
one denoiser, no dropout/churn, identity-bound noise211001. Alpha=.001, T=1,
q=log(p), p_native=.999. No frozen sequence-dependent conditioning.
Directly obtain gp and gq; replay the softmax VJP to check variable routing.
Two complete native forward/backward calls must reproduce coordinates/gradients
exactly. Hook counts per forward: four Pairformer calls, one denoiser. Check
one-hot ESM/native-token parity and one-hot full path/native hard coordinates.
Report hard/near chemistry separately; near-hard must add no severe pair or
wrong checked stereocentre, bond/peptide RMSE/MAE increments<=.01Angstrom,
penetration increment<=.05Angstrom. Hard absolute failure does not block numerical
auditing; it remains a hard-candidate acceptance constraint.

Compare native full gq with FP32 math-SDPA full gq (relativeL2<=.01), record
coordinate max difference (<=.001Angstrom). Math SDPA is an audited reference,
not a production-backend change or FP64 model. Run true torch.func.jvp from
original q for three CPU-seeded Gaussian unit-L2 directions (seed212001+index).
Disable checkpoint wrappers ONLY in that reference. Compare native VJP projection
and reference JVP, and reference JVP/VJP, using historical5%+1e-6. Report all
values; at least one direction must have BOTH amplitudes>1e-6 and relative error
<=5%. Other near-zero absolute-tolerance passes are explicitly low-information.
Unsupported/OOM/nonfinite/audit failure stops candidate evaluation for this batch;
no change of thresholds/backend in production to force release.

Log complete native ESM+C4+S1 forward/backward wall time (GPU synchronized), peak
allocated/reserved VRAM, model loading/feature setup separately, repeat stability.
This80–160 pilot does not establish long-chain performance. Existing ESM checkpoint
wrapping is reused; no silent truncation. Broader length profiling is a later gate.

## Stage B: conditional one-round hard utility (only after all four audits pass)

Use task-only gp for proposals; hard chemistry is a separate acceptance constraint.
At each position score min_b(gp_b-gp_native), choose lowest, residue-index tie break.
Uniform random position from identical allowed positions, seed213001+index. Both
arms enumerate ALL19 replacements; allow overlap without redrawing. This separates
position proposals from the known-unreliable local replacement ranking.
Lock proposals before hard outputs. Max4x39x3=468 hard predictions. Same candidate
budget, extra gradient cost counted separately, not an equal-total-compute claim.

Every mutant rebuilds native tokens, ESM, atom inventory, reference chemistry and
C4 conditioning. Shared atoms retain identity-bound noise. Evaluate all candidates
and parents at211001 plus locked confirmation211013/211021. No best noise, no
relaxation, no additional candidates, no second mutation round.

Task gain>1e-4, original broad hard_accept absolute/nonregression safeguards,
ZERO severe pairs and ALL checked CA/ILE/THR centres correct are required jointly.
Do not reinstate legacy idealized connection max windows. Calibrated connection
distributions, worst pairs, bond/peptide errors and normalized clashes remain
reported. These operational checks are not complete chemistry validation.
Select at most ONE candidate per arm using proposal noise ONLY: among candidates
passing those joint requirements, lowest task loss, lexical sequence tie-break.
If none qualify select none. Confirm this exact candidate on BOTH confirmation
noises without reselection. Also report all candidates' paired changes and
rejection reasons; candidate/seed counts are not independent protein counts.

The main pilot outcome is number of parents with a preselected candidate passing
both confirmations, gradient vs random; four parents cannot prove general superiority.
If audit or utility fails, close with the reason. Do not reopen numerical bug
hunting without contradictory derivative evidence. Symmetry training remains a
separate unstarted candidate. No automatic binder or deployment promotion.
