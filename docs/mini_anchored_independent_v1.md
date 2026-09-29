# Independent-protein geometry validation v1

2026-09-29. Authorized next stage; geometry implementation frozen at `2aa87043`.
This protocol precedes selection and all new folding/solver outputs. No mutation
search, training, relaxation, K/weight/budget tuning, or production precision change.

## Selection and separation

Source: DiamondHill `scratch_structure_data_v1_20260927`, experimental construct
sequences and masked atom37 coordinates. Historical TRAIN is an asset label, not
permission to train on the new validation panel. Reserve selected groups and their
near-sequence exclusions from any future correction training. Do not change old
manifests. No frozen temporal-test structures are opened.

Exclude the entire historical 16k teacher input collection, TRAIN8192 and DEV128,
the old 1024-target Mini grid, confirmation targets, precision/gradient development
targets and known length preflight cases. Archive source lists and hashes. Resolve
their construct sequences from existing sequence catalog/metadata, failing on
unresolved IDs. Exclude matching PDB entries and any shared SIFTS accession (all
chains of an excluded PDB conservatively contribute); missing candidate SIFTS
mapping is excluded. This does not certify absence from Mini/ESM pretraining.

Use the existing Biopython global homology aligner: match2, mismatch-1, gap-open-8,
gap-extend-1. A near pair has >=30% identity among aligned residue columns and
>=70% coverage of the shorter sequence, with >=50 aligned residues. Every selected
candidate must have no near pair to any excluded sequence, and selected candidates
must also be pairwise non-near. This is an explicit greedy representative/separation
rule, not a claim of complete transitive clustering or remote-homology exclusion.

Scope: standard 20 amino acids, one continuous protein chain, no modified residues,
no recorded chain breaks, complete observed backbone, no disulfide/crosslink in the
supported graph. Missing side-chain GT atoms remain masked. Native atom inventory
must be rebuildable by the frozen chemistry constructor, including supported end
groups. Exclusions depend only on source data/representation, never prediction scores.

Four length strata: 50–127,128–255,256–511,512–1024; eight proteins each. In each
stratum hash-rank eligible groups using `anchored-independent-v1:20260929:` + group_id.
Audit at most the first64 eligible groups per stratum; choose the first8 passing
homology and pairwise selected-panel exclusion. Fewer than8 means selection stops
incomplete, not looser isolation or a change of length distribution. A pre-selection
screen is not part of the locked32 denominator; publish every screening exclusion.

## Frozen experiment

32 proteins x three noises `300007,300017,300023`:96 raw predictions. Native hard
ESM2-3B -> Mini-ESM C4/S1 FP32, fixed identity-key initial noise, identity augmentation,
no MC dropout, gamma0=0,lambda=1,eta=1; record actual schedule and runtime/checkpoint
hashes. ESMC caches are not substituted. GT never enters inference or repair.

Each raw output feeds both frozen mean JointObjective and TailObjective from the
same local initialization: 3 stages rho1/10/100,60 LBFGS iterations/stage, original
line search/max-eval, tail K16/1.9A/.1A. Final state only;900s ceiling per repair,
1800s per raw inference. At most8 DiamondHill GCD workers; no retry with altered
settings. Lock candidate IDs, sources, implementation hashes and support preflight
before GPU outputs. Failures/timeouts/nonfinite outputs after lock stay in denominators.

## Evaluation and stopping

Retain raw/mean/tail for every seed. Independently recompute original geometry gates,
all checked CA/ILE/THR chirality, connection residuals and raw-frame RMS preservation.
Publish penetration distributions/named worst pairs, newly introduced violations,
repair rate among raw failures, retention among raw passes, and all3-seed protein
pass counts. No post-hoc max-atom-displacement rejection; describe backbone/sidechain
extremes and residues with >2A/>5A displacement. These new descriptive cutoffs do
not retrospectively alter the six-case result.

Experimental precision: fixed observed heavy-atom identity/mask, inter-residue
all-atom lDDT (15A reference cutoff, thresholds .5/1/2/4A), CA-lDDT, aligned CA
RMSD/TM. Use one frozen scoring implementation for all three outputs; no teacher
coordinates as GT. Report all scores and paired changes, per-protein seed means,
worst tails and length strata. No best-of-three. Bootstrap proteins (seed triplets
together),10000 resamples,seed20260929; no independent-sample claim for96 structures.

Predeclared engineering continuation screen, not a deployment standard: Tail must
pass >=80/96 instances and all3 seeds for >=24/32 proteins; no raw joint-pass input
may become joint-fail. Mean protein all-atom lDDT change vs raw >=-.005, bootstrap
95% lower endpoint >=-.01, at most3/32 proteins with mean change<-.02. Any missing
quality result prevents a positive quality screen; report failures separately rather
than silently omitting them. Compare frozen mean solver descriptively and paired;
no requirement to win every protein or post-hoc select a solver per input.

Record closures, wall time, peak memory, initialization/forward/repair separately.
Iteration caps are matched, FLOPs are not. Stop after this batch; no validation-set
tuning or automatic distillation. Only then discuss offline labels, differentiable
finite-step solver, or short learned mapping. No solver-input derivative or design
utility claim follows from this validation.
