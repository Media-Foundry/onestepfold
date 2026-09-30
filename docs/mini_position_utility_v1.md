# Frozen learned S1: gradient-selected positions versus random positions

2026-09-30, after0d3d5e8b. Bounded development utility experiment, NOT a new
independent folding-quality validation. No training, relaxation, threshold tuning,
new FD sweep, Y38/control reuse, or fresh32 confirmation reuse.

## Lock before outputs

Select4 parents from the existing TRAIN128, lengths80–160 inclusive, by ascending
SHA256('position-utility-v1:20260930:'+group_id). No quality/chemistry filtering or
replacement after outputs. Source contract remains unchanged; selection is a
short-chain compute restriction for this pilot, not an architectural length claim.
Freeze full diffusion512 checkpointSHA
7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829.
Use native FP32 reverse-mode, live ESM2, complete ERC and all4 recycle paths,
one denoiser call, no dropout/churn/repair, identity-bound initial noise.

Near-hard alpha=.001: p_native=.999, others=.001/19, q=log(p), T=1.
Acquire probability gradient directly and verify the softmax chain relationship
to logits gradient. Do not divide logits gradients by small probabilities.
Use the unchanged old `run_hard_mutation_utility.objective`: monomer nonlocal CA
contact proxy with CA guards + bond +2peptide +clash +.2CAchirality. This is an
explicit diagnostic continuation of that objective, including its legacy native
reference bond definitions, NOT a claim of calibrated chemistry or binding utility.
No new loss weights, KL trajectory, or soft optimization is introduced.

Proposal noise800011. At position i define score=min_{b!=a}(g_p[i,b]-g_p[i,a]).
Choose one position with minimum score, break ties by residue index. Uniformly
choose one random position from the SAME complete position space, with RNG seed
900001+parent_index. Allow overlap; never redraw to make the groups disjoint.
At BOTH positions generate ALL19 non-native canonical replacements in fixed AA
order; no local-gradient replacement ranking or sign reversal. Archive full gp/gq,
all position scores, selected positions and candidate manifest BEFORE hard scoring.
No candidate substitution is accepted from a soft score.

## Hard evaluation and endpoints

Each candidate and parent rebuilds native chemical inventory, reference features,
ESM embedding and C4 conditioning. No parent conditioning/cache is reused for a
mutant. Shared atom identities share raw noise. Evaluate all candidates on800011
and prelocked confirmation800029/800053. Max4×39×3=468 hard outputs (fewer only
for overlap), plus4 input gradients and explicitly logged parity checks. Deduplicate
computation but preserve arm identity. Equal candidate budget, NOT equal total
compute: gradient setup/backward is an extra cost. Hard endpoints use ordinary
ESM token lookup and are checked against one-hot soft ESM for each parent.

Report per parent/arm, separately for each noise and jointly for both confirmation
noises: task delta distribution; task improvement >1e-4; task+legacy geometry
nonregression; task+zero severe overlaps(<1Å, covalent paths<=3 excluded)+strict
ALL checked CA and ILE/THR stereocentres. The last combination is limited evidence,
NOT full chemistry or deployment acceptance. Keep original full hard_accept as a
historical column only, never the sole method veto. No new connection hard window.
Report bond/peptide diagnostics, normalized severe counts, penetration, actual
worst atom identities and calibrated connection distributions. A candidate passing
only a subset must not be called chemically valid. Native parents can fail too.

Also preselect at most ONE candidate per arm by lowest hard total objective on
proposal noise, restricted to task improvement>1e-4+zero severe+strict checked
chirality on that noise; lexical sequence tie-break. If none qualify, select none.
Test that exact selection on BOTH confirmation noises without reselection. This
separates a deployable hard-search choice from retrospectively counting all successes.
Do not compare mutated sequences to parent experimental GT as if mutant GT existed.
All failures/timeouts remain in denominators; no parent replacement or candidate
expansion. Four parents are four development examples, not148 independent proteins.
Results do not estimate generalization or binding affinity. Preserve full failures,
then close this batch before deciding on the next method change.
