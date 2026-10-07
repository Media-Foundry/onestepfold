# Mini cached-reference editor engineering pilot v1

Locked2026-10-07 before fitting. User approves Mini architecture prototype;
Base is excluded. Public protenix_mini_esm_v0.5.0 and archived exact C4/S1
teachers from factor_student_pilot_v1_20261002, fixed hashes. This is a new
engineering/teacher-fidelity experiment, not experimental mutant prediction.
No downloads, no new ESM/C4 teacher, no diffusion fine-tuning or rank truncation.
Raw WT conditioning was previously produced by native ESM+C4. Reference Mini and
S1 weights remain frozen; gradients must traverse S1 into all three predicted
conditioning tensors. No oracle target s/z/s_inputs enters student inference.

Architecture: width256,32workspace tokens,4blocks,8heads,pair_width128,chunk16.
Reference memory projects WT inputs/s and pair means; per-block reference K/V
is shared. Workspace reads reference, reads evolving candidate nodes, interacts
internally, writes all residues. Late pair writeout reads full WT pair content,
left/right candidate nodes and workspace mean through a nonlinear128-wide head.
Dense single/input responses; dense pair response, no AA/spatial rank bound.
Ordinary attention only; no Diff attention sweep. Small nonzero output weights
std1e-3; SiLU residual branches, LayerNorm. Empty-edit branch anchors response;
explicit no-edit gate removes numerical batch differences. Cache bound to model
parameter versions and reference tensor versions. Raw reference caches persistent;
trainable projections rebuilt after every update. Candidate axes never attend
other candidates. Same-reference batch2 shares projection and empty branch.

Panel, positions1-based:
TRAIN:1W53 T37(parent3),1JHG A2(parent4),all19nonWT each.
DEV same-protein unseen-site:1W53 Y84,1JHG N25.
DEV different-protein:4PT4 L10(parent6).
All are reused development contexts; no independent confirmation claim.
Structural labels: exact native hard-mutant S1 coordinates, old noise230201 only
for training.230211 used for evaluation only in THIS experiment, but is historical
development noise. No experimental mutant label. Parent experimental backbone
used ONLY for legacy score evaluation, never passed as editor input.

Two seeds271001/271003 from scratch, reset after Mini loading. AdamW lr1e-4,
wd1e-4,eps1e-8,clip1,512updates perseed. Alternate train sites; each update two
nonWT candidates with a deterministic balanced cyclic order (512AA exposures/site,
26–27 exposures/AA). Average candidate losses, one optimizer update. No adaptive
extension. Main terminal512; intermediate128 and initial0 fully evaluated.
Loss = aligned all-heavy coordinate MSE +.25 CA-pair-distance MSE
       +.01 existing severe-clash penalty +.01 checked-chirality penalty.
Alignment uses detached optimal proper rotation for the coordinate objective;
no latent NMSE loss. Record raw components, gradient norms/branches, response
energy. Loss coefficients are pilot choices, not tuned on validation.

Preflight: all95mutant exact S1 replay on both noises;3WT replay; reference-only
conditioning+target chemistry baseline. Cache/fresh, candidate order/subset,
edit-list order, cross-site reuse and no-edit invariants. CPU focused tests plus
actual Mini/S1 gradient audit. Fail on nonfinite, replay/integrity/cache failures;
no silent retries or alternate model selection. Fixed run cap45minutes.

At0/128/512 decode all5sites×19AA×2noises,regardless of latent fit. Report bysite
and train/same-protein/new-protein: AA/CA lDDT,local/global RMSD,P95/P99/max,>1A,
severe collision and checked chirality transitions,raw task MAE,19AA Spearman,
Top1/regret,old-select/new-evaluate regret. This is reference-only baseline,
not historical WT-z with oracle target s. Do not combine their numbers.
Training coordinates never become structure-quality ground truth claims.

Timing: prepared raw WT memory + prepared candidate chemistry, model only.
Measure projected-cache construction, candidate edit/writeout,S1 and combined;
compare cached projection vs rebuilding identical projection percandidate. Report
ordinary fresh Mini C4 cost as NOT MEASURED; preexisting cache generation is not
free for full deployment. No end-to-end or20×speedup claim. Serial/limited batch
and full batch candidate readout distinction retained; no20densez memory promise.
Reference decoder and raw memory hashes unchanged; checkpoints/output manifests,
sourcefreeze, independent score recomputation and checkpoint replay before closure.
Pilot may demonstrate learnability without transfer;512updates insufficient to
prove an architecture cannot fit. No automatic data expansion or decoder unfreeze.

## Pre-training execution revision v1a

Initial host reboot preserved as interrupted root. Retry1 passed all95 exact
mutant/two-noise replays, then failed the absolute1e-4 candidate-permutation
check before any update. Standalone MI250 diagnostic: fixed-order repeat exact;
block differences~1e-6; largest s difference1.220703125e-4 (one FP32ULP at
reference s magnitudes up to1768). Candidate-independent algebra but batch
position changes floating reduction. Preserve original threshold; forward now
uses identical single-candidate kernel shapes, sharing reference projections
and empty workspace. Same architecture/loss/seeds/budget. Parallel candidate
speedup is explicitly deferred. New frozen v1a root; original failure retained.
