# Fixed-WT Jacobian plus residual functional-rank v1

Locked 2026-10-02 before full-batch tangent collection or residual functional scores.
Last bounded AA-axis linear-structure diagnostic requested after global PCA v1.
No student training, new sites, model-weight change, adaptive rank or design search.

## Tangent definition and scope

Same10 TRAIN proteins/50sites/19nonWT AA; the exact hard endpoints from prior
full-global-rank archive stay unchanged. p0 is exactly one-hot WT, not near-hard
logits. d_a has -1 at WT and +1 at the candidate at the single mutation position.
T_a=J_C(p0)d_a by **torch.func.jvp**, complete ESM2+R+C+four native recycles.
No finite difference, backward-of-backward JVP or division by small probabilities.
This is the derivative along p(t)=p0+t*d_a at0+, on the fixed WT native inventory.
ESM and all current probability-dependent reference fields are live. The chart's
homopolymer reference bank, missing-atom zeros and seeded WT override remain as
implemented previously; do not silently introduce another soft representation.
We do not evaluate this chart across argmax, assert hard-graph continuity, or
claim this tangent equals the finite native-graph mutation. Residual includes
nonlinearity, chart-extension choices and graph reconstruction differences.

One WT chart forward per parent must exactly reproduce archived s/z. EVERY JVP
primal must match this native base bitwise, all tangent entries finite.
For the first locked site's first nonWT direction per protein, use2 random fixed
output projections (seed228101+parent index, each block scaled by1/sqrt(numel))
and compare trueJVP with reverseVJP; error <=1e-6+.005*max(abs(projections)).
Record amplitudes and low signal; no failed check silently discarded.
JVP disables checkpoint wrappers. Reverse validation uses non-reentrant ESM-layer
and native block checkpoints to bound memory; its primal must still match.
Retain the uncheckpointed longest-chain preflight OOM separately; it occurred in
reverse validation after successful native JVP, not in the main functional batch.

## Oracle residual and decoding

Compute FP64 Delta_a=C_hard,a-C_WT and R_a=Delta_a-T_a; mean over19nonWT only.
Use raw joint Gram(Rs)+Gram(Rz) as primary. Block-balanced joint Gram/Es+Gram/Ez
is predeclared secondary, where Es/Ez are total residual energies BEFORE centering.
A zero-energy block contributes zero. No separate-block sweep in this final diagnostic.
C_hat=C_WT+T_a+mean(R)+project_K(R_a-mean(R)), final cast once toFP32.
K=0,1,2,3,5,8,10,12,15,18, same as direct PCA controls; also decode tangent-only
C_WT+T_a (without oracle residual mean). K0 is NOT tangent-only.

Use WT s_inputs and native TARGET chemistry/atom graph for every approximation;
rebuild decoder reference caches. Same layout, public MiniESM, FP32 controlledS1,
identity-noise225001/225011. Exact(target inputs,target trunk) and Baseline(WT inputs,
target trunk) freshly decode and bitwise replay prior global experiment.
All K18 actually reconstruct/decode with existing input1e-5/coordinate1e-3A guards;
no bypass to exact state. Verify raw/balanced K0 identical before sharing decode.
All other queries retained, even if poor. WT kept unchanged, not a20th PCA sample.

The means/bases/coefficients use ALL19 target teachers: oracle reconstruction,
not a learned correction, cross-AA generalization or cheap inference algorithm.
950JVPs are real computations, not free analytical features. Archive every full
s/z tangent, direction order, source hash, runtime and projection check.

## Budget, outputs and interpretation

8GPU workers,32CPU scorers with prior fixed assignments;7200s maximum for each
phase. Expected950JVP,10WT primal+10reverse-validation forwards,3880recycle module
calls (checkpoint block recomputation recorded via timing, not counted as fullC4).
Expected41820decoderNFE,1900duplicateK0NFE avoided,960native hard rebuilds.
Preflights and chemical template construction are separately reported setup work.

Exactly reuse prior full-rank functional scores, local regions, parent-GT CA-distance
Huber ranking proxy and all geometry definitions. Report both Exact/Baseline refs,
19AA and20AA ranking,Top1/regret/top3/top5,local RMSD tails,new geometry failures,
6UFE92 stress case,non-finite/runtime failures. This is model-response fidelity,
not true experimental mutant effects or binder/design utility.

Compare residual vs direct PCA at matched K/metric, including protein-averaged
paired Spearman/Top1/regret and10-protein bootstrap10000(seed228101). Keep complete
curves and downside transitions, not a post-hoc winner. Also report tangent fit,
residual energy and spectra, without substituting energy for functional evidence.
No new acceptance threshold making 0.95 correlation a pass. If K5/K8 does not
improve selection and tails meaningfully, close this linear compression path;
a weak mean improvement alone does not justify a model or further K tuning.
Any later nonlinear20query propagator requires a separate data/training protocol;
this batch does not authorize automatic training or independent-validation claims.

## Pre-functional launch corrections

Initial preparation missed the onestepfold package in its source bundle; no workers
started. After packaging repair, all8 workers stopped at the first WT replay guard:
the comparator incorrectly treated WT's noise axis as an arm axis (WT packets are
[2,N,3], mutant packets [arms,2,N,3]). No JVP/residual functional panel was collected.
Preserve those logs; fix the file contract with a focused regression test and use
new run directory jacobian_residual_rank_v1_20261002_retry1. Same frozen proteins,
noises, weights, derivative definition, metrics and budgets; no result-driven change.
