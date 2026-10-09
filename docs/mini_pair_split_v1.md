# Mini terminal pair intervention v1

Locked 2026-10-09 before new decoder outcomes. No training, new sequences,
teacher labels, ESM/MSA preparation, input-encoder calls or RCSB. Frozen Mini,
archived candidate s_inputs/features/chemistry, WT3+RNG, native last recycle,
frozen S1. Four fixed8208 single/dual x272001/272003 endpoints. Existing
48sites/24parents/912mutants,19AA/site. All panels remain development.

Let B be actual candidate's unadapted final conditioning, L its adapted final
conditioning. Delta=L_z-B_z in native FP32. For each endpoint/site, accumulate
all19 deltas on CPU in FP64 in locked candidate order, divide by19, cast once
to FP32 to obtain mean. No teacher conditioning participates in this mean.

Five conditions per endpoint:
- disabled: original B tuple (shared control across all endpoints).
- full: original L tuple, never reconstruct via subtraction/addition.
- pair: (B_inputs,B_s,L_z), original L_z, not B_z+delta.
- common: (B_inputs,B_s,B_z+mean).
- aa: (B_inputs,B_s,B_z+((L_z-B_z)-mean)).

Inputs B_inputs and L_inputs must be bitwise equal for actual candidate.
All conditions retain that candidate's own atom graph/chemistry and the same
two archived noises230201/230211. No scaling, permutation, rank, loss, seed,
checkpoint or noise search. No extra single-only arm. No target final s/z.
Mixtures can be off the trained joint-state distribution; causal interpretation
is limited to this interface intervention. Shared mean still requires19
predictions and is not a proposed cheap single-candidate deployment method.

Decode disabled and full from original tensors and require exact bitwise
agreement with corresponding archived coordinates for both noises. On first
site per shard also replay pair-only from CPU-restored identical tensors to
verify transfers preserve its decode. Cache CPU conditioning per site and
endpoint only; GPU decoding remains one candidate at a time. Mean and CPU
transfer/replay costs included in diagnostic wall time, not a speed claim.
Only HIP_VISIBLE_DEVICES0..5; first full site passes before remaining workers.
Fail closed on replay, hash, shape or finite checks; no retries selecting results.

Expected4560 native last-recycle calls,31008 S1 outputs plus6 transfer-audit
S1 calls, zero updates. Native C4 interface/input encoder counters zero.
No target3 reconstruction required. Hash original weights, banks and WT3
before/after. Coordinate NPZs and SHA manifests retained on DiamondHill.

Coordinate-only scorer: same prior exact teacher, parent-reference backbone
distance proxy (lower better), fixed CA mappings/masks, same geometry rules.
Report separately TRAIN27sites/15parents, same-parent new3sites, held18sites/
9parents. Equal-parent means for ranking/regret/response. Pooled structure
tails and geometry counts retain actual denominators, not independence.
Metrics: same-noise and two-noise mean-score Spearman/Top1, old230201 selection
evaluated on exact230211 regret, score MAE, centered AA distance-response RMSE,
all-atom fidelity, local P95/P99/max/>1A, pass→fail/fail→pass versus exact and
disabled, severe collision pairs and wrong chirality counts including outputs
already failing. Keep per-site/per-parent identities and continuous chirality.

Fixed contrasts for each endpoint: pair/common/aa minus disabled and full;
also aa minus common and pair minus full. Paired parent bootstrap10000 draws,
seed275001, descriptive95% intervals, no multiple-comparison significance or
independent-confirmation claim. Endpoint controls must reproduce prior site
scores and response metrics. Always report all four endpoints and all strata.

Only aa gains over BOTH disabled and full consistently in both seeds warrant
the hypothesis of masked useful AA pair corrections. Beating full alone can
merely remove adaptation harm. Common geometry/aa selection benefits can
differ; no automatic deletion of mean. If none help, close diagnostic without
new training. No promotion of a mixed condition based on this development panel.
