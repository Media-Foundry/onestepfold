# C4 information-path swaps v1 — frozen before decoding

2026-10-02. Reuse functional_response_rank_v1's960 full native FP32 conditioning
packets and50 fixed sites in10 development TRAIN proteins. Zero C4 and ESM calls;
no training, Jacobian experiment, global SVD, new targets or adaptive selection.
No alteration to earlier experiment protocols/results.

## Six arms, always on the native hard TARGET atom inventory

|Arm|s_inputs|s,z|Reference chemistry / atom graph|
|---|---|---|---|
|exact|target|target|target|
|wt_trunk|target|WT|target|
|chem_only|WT|WT|target|
|target_trunk_only|WT|target|target|
|local_only|target|WT complement, exact target local|target|
|global_only|target|target complement, exact WT local|target|

Local = s[i] and union z[i,:]/z[:,i], including z[i,i] once. Equal-length token
correspondence is exact. No swapping atom arrays between chemical inventories.
Chem-only means WT neural context with the target chemical/graph route, not
unconditional chemical generation. The latter route includes identity, reference
geometry, element/charge/masks, atom-to-token mapping and native pair/padding
features. WT chemistry is never used for a mutant. These mixed interfaces may
be off-distribution; effects are conditional interventions, not additive mutual
information estimates or proof that a branch has no role in the native model.

Read full tensors from previously hashed13.005GB archive. Independently hash all
960 packets, all prior coordinate/inventory files and fixed weights. Rebuild
native features with seed101; require archived atom identities, order, bonds and
reference positions to match. No ESM loading/recomputation and a runtime hook
forbids Pairformer execution. Log actual direct decoder feature reads and source
hash. All conditioning uses the same packed layout; caches rebuilt per arm.

Same public Mini-ESM v0.5.0, FP32/eval, controlled stable-Euler S1 as prior.
Same identity-bound initial noise225001/225011, no added churn/rigid augmentation
or dropout. Exact must reproduce previous coordinates BITWISE for all960 unique
sequences. All six arms for each WT must also reproduce WT output bitwise.
A replay failure is an engineering stop, not an ablation result.

Counts: 960 native chemical feature rebuilds, zero ESM/C4/recycle calls,
11520 denoiser calls (950mutants*6arms*2noises +10WT*6arms*2noises).
11420 unique outputs;100 extra WT identity controls. Store all outputs, not only
successful geometry or beneficial objective changes.

## Locked analysis

Reuse the preceding fidelity metrics: all-atom/CA lDDT to SAME-NOISE EXACT MODEL
output (not experimental truth), global CA RMSD, fixed local CA RMSD in global
fit, CA distance RMSE, contact and distance-bin changes. Local region = parent
GT CA8A neighborhood plus sequence +/-2. Full native heavy-atom severe overlaps,
checked CA/ILE/THR chirality, max penetration, new failures and recovered passes
are reported separately; neither baseline nor ablation is chemically certified.
Keep6UFE-92 in the main panel as a fixed stress case; do not pursue its mechanism.

Ranking task remains the locked parent experimental CA-distance Huber objective
(delta1A, observed pairs separated >=3 residues). It is a backbone-preservation
proxy, not mutation experimental quality or binding. Report19 non-WT and20-AA
Spearman, top1 agreement, top1 regret in exact objective, normalized regret,
top3/top5 recall, actual task range and zero-signal diagnostics. Constant rankings
are undefined, not forced to success. Stable AA order breaks selection ties.
Also retain both-noise top1 consistency per site and distributions/tails.

Distance-response supplement: on common CA pair identities, compare each mutant
response to matched WT output, then compare ablation error to exact response;
also subtract the19-AA mean to measure AA-specific response error. Use FP64
coordinate differences. This is a descriptive response-scale diagnostic.

Aggregate within protein before10-protein means and bootstrap10000(seed226101).
These are development proteins with distinct accessions, not a new homology-held-
out or pretraining-unseen benchmark.1900non-WT outputs/arm and100site-noise
rankings are not1900/100 independent proteins.

Prespecified paired ranking contrasts: global_only - wt_trunk,
local_only - wt_trunk, exact - wt_trunk, wt_trunk - chem_only,
exact - target_trunk_only, target_trunk_only - chem_only. Differences describe
conditional added value, not percentage attribution. Global-only being good is
insufficient on its own: target s_inputs and target chemical features are retained
in both global-only and WT-trunk. Top1/regret must accompany Spearman.

## Costs and stopping

Cached target s_inputs already contains target-specific input encoding including
ESM. This test does NOT establish that generating it is cheap. No end-to-end
speedup claim; count native rebuilding, archive IO and actual decoder calls.
No numerical promotion threshold is chosen after results. Interpret evidence on
mean, tails, geometry and parent consistency together.
Eight bounded GPU workers then eight CPU scorers, maximum1h for each phase.
Runtime errors stay in the denominator; no silent drop or extra seeds. Freeze
code/input hashes before run. After these six arms are collected and audited,
stop and decide whether global rank is necessary. No automatic extra arms or
training. Independent Jacobian residual and20-query model remain deferred.
