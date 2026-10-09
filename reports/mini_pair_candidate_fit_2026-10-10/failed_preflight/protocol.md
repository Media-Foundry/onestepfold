# Single-site Mini pair-recovery fit diagnostic

Locked 2026-10-10 before training. User authorizes the proposed candidate-fit
test after closing the frozen-feature readout study. This is a fresh training
diagnostic, not another readout fit, a continuation, or a migration claim.

One preselected historical TRAIN site: 1W53 T37, p3_s37 (archive length84).
Selection follows the existing first TRAIN/preflight site, not a new ranking
of results. All19 non-WT candidates are used, with their own cached native
B_inputs/B_s/B_z, target_C4_z labels and fixed WT3 reference. No held sites
are fitted or evaluated. This single context cannot establish general capacity,
protein transfer, or independent confirmation.

Architecture unchanged: PairRecovery from4625c230, two pair-only Mini blocks,
1,331,972 trainable parameters, same128channels and zero final head. Four fresh
runs: pretrained/random x272001/272003. Reproduce the original initial hashes;
do not load an8208 model. Original Mini, S1, B and WT3 caches remain frozen.
No extra head, layer, nonlinear readout, intermediate supervision, LoRA, low
rank, precision change, structure/geometry/ranking loss or new teacher/input
preparation. The proposed process-supervision architecture is NOT this test.

Loss and optimizer unchanged: mean((B_z+R-target_z)^2)/q, original
q[p3_s37]=31.323820267027703; do not refit normalization on the one-site set.
AdamW lr1e-4, weight_decay1e-4, eps1e-8, global clip1, serial accumulation of
two candidates per update. Candidate indices(2*step+j)%19, j=0,1. All recovery
parameters train. Store separate common and AA-centered errors as metrics;
do not change the objective to centered loss.

8208 fixed updates/run. Evaluate/save0,304,1216,4104,8208; terminal8208 is
primary, no best-checkpoint selection or automatic extension. Candidate
exposures at these nodes are0,32,128,432,864. Step304 matches the per-candidate
exposure of the previous27-site8208 endpoint. Step8208 matches its total update
count but has27x as many exposures to this site. These are distinct comparisons:
optimizer history/interleaving differ, so neither alone identifies gradient
conflict, capacity, or an exposure-only causal effect. Historical training
endpoints, including failures, remain intact.

Every node evaluates all19 candidates: full/common/centered pair residual
NMSE, energy ratio and cosine, per-candidate errors, complete S1 decoding with
the two archived noises230201/230211. No latent threshold controls decoding.
Terminal also applies the pre-fixed next-AA donor residual to each actual
receiver's B_z while keeping its B_inputs/B_s/chemistry/noise. No permutation
search. Compare latent and functional correspondence to no correction, oracle
pair, and the old joint-training endpoint on THIS site. Do not bootstrap one
protein or count19AA x2noise as independent environments.

Functional metrics retain same-noise and mean-score Spearman/Top1/score error,
old-noise selection evaluated with new-noise Exact scores, centered CA-distance
response, lDDT, local tails, absolute geometry and pass/fail transitions. Exact
and oracle remain model references, not experimental mutant or chemical truth.
No oracle target state is passed to the predictor; targets are loss-only.

Before updates: source/code/protocol/cache hashes, original initial-state hash,
zero-edit and zero-head identity, all19 two-noise B coordinate replays. Save all
node checkpoints and predicted residual tensors for independent reconstruction.
Track early and periodic pre-clip gradient norms by parameter group, parameter
movement, losses and exact exposure counts. Check no native/input encoder call,
no gradients in Mini/S1, no change to resident inputs or reference state. Fixed
candidate-alone/order replay and checkpoint reconstruction at the terminal.

Four independent workers on currently free HIP0..3; HIP0..5 authorized only,
selected solely by HIP_VISIBLE_DEVICES. No DP batch change. Cache19 candidate
inputs/targets on the assigned GPU to avoid repeated transfer; this changes
storage placement only. CPU scoring separately bounded. Four runs total32832
updates,65664 training candidate forwards; expected912 S1 evaluations (228/run).
Evaluation forward/replay counts and memory/time are recorded separately.
Six-hour runtime cap, no automatic scientific restart, all failures retained.
This is diagnostic runtime, not a new folding speed benchmark.

Interpretation: strong single-site AA fit establishes representability for this
site under this budget, not universal sufficiency; compare the matched-exposure
node to joint training before interpreting benefits. Persistent poor single-site
fit leaves architecture AND nonlinear optimization unresolved, not a proof of
information insufficiency. Identity benefit must beat no correction as well as
wrong correspondence. Decoded quality, latent fit and selection remain distinct.
