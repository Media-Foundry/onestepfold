# Global s/z functional-rank v1 — locked before decoding

2026-10-02. Same10 development parents,50 sites and19 non-WT hard endpoints from
hard_response_rank /functional_response_rank /conditioning_swaps. Reuse the960
full native FP32 state packets. No C4/ESM recomputation, new sites, Jacobian or
training. Chemistry/inventory remains native TARGET for each AA and arm.

## Projection and decoder inputs

For each block b=s,z, compute in FP64, before any subtraction:
Delta_b[a]=C_b[a]-C_b[WT]; mu_b=mean over19non-WT; R_b=Delta_b-mu_b.
WT is NOT a twentieth PCA sample and always keeps its original state/output.
Replace ENTIRE s and z in the joint arms, including all nonlocal tokens/pairs.
All truncated arms use WT s_inputs, never hidden target s_inputs.

Two separately labeled references are mandatory:
- Exact: archived target s_inputs,s,z +target chemistry.
- Baseline: WT s_inputs +FULL target s,z +target chemistry (previous target-trunk-only).
Recompute both and require bitwise coordinates vs the previous swap archive.
Evaluate total error to Exact and isolated compression error to Baseline, including
rankings and new geometry failures. Baseline's small s_inputs effect is not a
compression failure, and is not evidence that upstream targetESM was unnecessary.

K=0,1,2,3,5,8,10,12,15,18, all retained. Five variants:

|Variant|Gram/basis|s|z|
|---|---|---|---|
|raw|Gs+Gz, shared AA coefficients|rankK|rankK|
|balanced|Gs/Es+Gz/Ez, shared AA coefficients|rankK|rankK|
|s_only|Gs|rankKs=K|exact target|
|z_only|Gz|exact target|rankKz=K|
|separate_both|independent Gs and Gz|rankKs=K|rankKz=K|

Gs=Rs Rs^T, Gz=Rz Rz^T, both19x19. Es=sum_a||Delta_s[a]||² and
Ez=sum_a||Delta_z[a]||² are fixed PRE-CENTER total response energies for the site.
A zero-energy block contributes zero to balanced Gram and is explicitly reported.
No per-AA adaptive normalization or post-hoc metric choice. Separate_both may use
up to2K distinct AA response directions; it is NOT the same capacity as sharedK.

Use descending FP64 eigenspaces. Left sample projector Q_K reconstructs the full
raw-coordinate block as WT+mu+Q_K R, cast once to native FP32. Balanced scaling
changes the shared projector, not the physical scale of reconstructed states.
Record spectra, per-block energies/shapes, Gram matrices and sample projectors.
These are in-sample oracle means/bases/coefficients using ALL hard endpoints,
not a head that predicts them from WT or a held-out-AA generalization test.

K0 raw/balanced/separate_both is one shared mutant-mean state across AA; chemistry
still differs. Verify their full s/z tensors bitwise equal before reusing identical
K0 decoded outputs. No other deduplication: all five K18 reconstructions are
actually decoded, never bypassed with the original target. Full-rank input
max error<=1e-5 and coordinate max error<=1e-3A to Baseline are engineering checks;
record actual errors and retain any nonzero values. Production weights untouched.

## Native replay and execution

Public Mini-ESM v0.5.0, FP32/eval, controlled stable-Euler S1, identity noise225001
and225011, no added churn, rigid augmentation or MC dropout. Native chemistry
regenerated withseed101 and checked against identity/order/bonds/ref_pos archive.
Same contiguous packing and caches rebuilt for EVERY changed conditioning.
No ESM loading; hook forbids Pairformer calls. Record decoder feature reads.

Expected95020NFE =950mutants*(2reference+48distinctprojection arms)*2noises
+10WT*2noises. The50projection slots include two analytically identical K0 slots,
whose equality is verified before reuse (3800 calls avoided). Both Exact and
Baseline references for960unique sequences must match previous archive bitwise.
Logical projected output slots are not independent proteins or a speedup claim.

Eight GPU workers;32 CPU scorers with site assignments frozen by L² balancing.
Maximum7200seconds for each phase. Failures remain part of the fixed denominator;
no cherry-picking K, noise, sites, runtime retries or additional training.
Store raw coordinates/inventories, source hashes, basis evidence, counters and
all per-case scores. Full13GB source state archive stays immutable.

## Functional endpoints and inference limits

Use the same metrics as the previous experiments: exact-model-referenced AA/CA
lDDT, global CA RMSD, fixed local-region CA RMSD in global fit, contact/bin and
nonlocal distance differences. Also compute these against Baseline. Local region
remains parent observedGT CA within8A plus sequence +/-2; no local refitting.

The locked ranking proxy is parent experimental CA-distance Huber loss, delta1A,
all observed pairs separated>=3 sequence positions. It is not mutant experimental
truth, binding or biological activity. For19non-WT and20-AA, report Spearman,
top1 agreement, top1 regret, normalized regret, top3/top5 recall and low-range
flags, to BOTH Exact and Baseline. Stable AA order breaks exact selection ties;
constant Spearman is undefined. Include both-noise agreement per site.

Keep full-inventory severe nonbonded overlaps (<1A, graphdistance<=3 excluded),
all currently checkedCA/ILE/THR chirality, maximum penetration, new failures vs
both references and existing failures. No claim of comprehensive chemistry.
Keep6UFE-92 as a frozen stress case without mechanism pursuit or exclusion.
Mean scores cannot replace local tails or geometry transitions.

Aggregate within protein then across10proteins, bootstrap10000(seed227101).
The same developer-used TRAIN/accession-separated panel is not new independent
homology-held-out evidence. Latent energy is diagnostic, never the success gate.
Raw-vs-balanced and the one-block controls guide interpretation, not selection
of a favorable metric after results. Do not treat keeping one block exact as a
fully compressed model. No arbitrary "95% ranking preserved" scalar threshold.

Collect and audit the full curve, then stop. No automatic adaptive-rank gate,
Jacobian residual, response propagator training or deployment promotion.
