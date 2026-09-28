# One-batch near-hard mutation utility protocol

Locked before execution, 2026-09-28. One previously audited control sequence,
archived logits at alpha=.001. Frozen native Mini-ESM FP32, C4/S1, native reverse
AD and native attention. No numerical modification, FD, training, soft trajectory,
relaxation or candidate-dependent settings.

One full ERC gradient of existing new objective: contact_objective + bond +
2*peptide + clash + .2*chirality + .01*KL(p||p0). The task is the existing monomer
contact objective including its CA guards, not binding fitness. Retrieve gp and
gq directly in the same graph; check softmax pullback with rtol1e-5,atol1e-8.
Never invert small probabilities. Candidate scores are gp[b]-gp[a], called local
substitution scores, never predicted finite hard-loss changes.

All194 positions ×19 standard amino-acid substitutions are allowed. Rank16
lowest scores using existing deterministic tie-breaking. Uniformly sample16
without replacement using proposal RNG6271, allowing overlap with ranked16.
Freeze candidate manifest, scores, source hashes and random/noise seeds before
any candidate evaluation. Proposal noise211. Confirmation noises200003,200009
are fixed now and never used for proposals, reranking or selection.

Evaluate parent and every unique candidate under all3 noises (maximum99 hard
forwards). Rebuild native features, graph, topology and live native ESM for each
unique sequence. Shared atoms use identity_noise; no parent conditioning cache.
Verify one-hot soft/native ESM parity on parent as an engineering replay guard.
Use identical native FP32 path and fixed graph per hard sequence; no autocast.
Parallelize unique sequences over4 idle MI250 GCDs; reuse a sequence's ESM and
conditioning across noises only because these are noise-independent. Preserve
arm membership if proposals overlap; no resampling to avoid overlap.

Save all coordinates, topology/reference, objective components, atom identities,
full geometry and timings. Hard task improvement threshold remains >1e-4.
Original GeometryRules and hard_accept are unchanged. Report separately:
1. task improvement + all geometry nonregression checks;
2. full hard_accept (also requires absolute geometry).
Both evaluated per noise, and counts requiring BOTH confirmation noises.
Keep all task deltas and min/P25/median/P75/max/mean; no best-of-noise or selected
candidate endpoint. Report total objective separately from task. One-parent
pilot is not prevalence evidence, protein-level replication or binder success.
Gradient cost is reported separately; equal candidate budget is not equal compute.

Stop after this batch, regardless of acceptance counts. No additional candidate,
seed, target, threshold tuning or iterative design is authorized by this protocol.

## Pre-candidate variable-check clarification

The original hand-written FP32 softmax check (rtol1e-5,atol1e-8) failed before
candidate generation; preserve this failure. Saved gp/gq agree exactly with an
independent native softmax pullback. The FP64 algebraic formula differs by max
3.01e-7 / relativeL2 4.33e-5, within a conservative gamma24 FP32 rounding bound
(max elementwise error/bound .0765). This is reduction/cancellation sensitivity
in the small native-probability logit response, not use of gq as gp.
The resume audit requires native pullback exactness plus the explicit FP64
formula rounding bound and archive coordinate replay before freezing candidates.
No geometry/task threshold, score, gradient, candidate count or seed changes.
One intervening ROCm launch failure occurred before the gradient and is archived;
execution moved to GCDs2,3,4,5. No candidate forward occurred before this addendum.
