# Factor learnability and sparse-residual diagnostics — locked 2026-10-02

Follow-up to `946b4287`; prior 1024-update pilot and R24/R32 results remain closed.
No new teacher, ESM/C4, S1 during fitting, geometry training, Δs predictor, or AA-axis compression.
The user's new instruction authorizes this bounded diagnostic, not extending prior checkpoints.

## Memorization ladder

Use existing TRAIN teacher packets only, hashed and role-guarded. Parent selection is
ascending archived index, before these outcomes: first TRAIN is 1W53 (index 3),
site 37 (zero-based 36), then its two archived sites; then first four TRAIN parents
(1W53,1JHG,1A7G,4PT4), then all sixteen. Old 50-site panel and eight validation
parents do not enter fitting. These are memorization tests, not generalization.

At each stage initialize fresh unchanged FactorStudent R32/width128/two blocks,
seeds 231301/231303, AdamW lr3e-4, weight decay1e-4, eps1e-8, clipping1.
512 updates, one entire 19-AA site per update, cyclic sites, same exposure schedule
for both objectives/seeds. Record all candidates at 0/64/.../512, no best-checkpoint
selection. Objective comparison: (a) normalized dense Δz reconstruction; (b)
normalized balanced canonical factor regression. No decoder or geometry loss.

SVD is FP64 per candidate/channel, descending singular values, left-vector largest
absolute component positive with paired right sign; U=P√Σ,V=Q√Σ. Original student
expansion divides by √R, so supervised factors are multiplied by R^(1/4), without
changing the original network. Relative adjacent gap<1% groups use joint orthogonal
Procrustes alignment of stacked U,V in the loss; cutoff-crossing gaps are reported.
This addresses sign/near-degeneracy, but does not assert factors are a smooth target
across candidate/protein changes. Direct factor fit need not minimize matrix error.

Single-site additional control: independent learnable U,V for all 19 candidates,
initialized from the corresponding untrained network outputs; dense reconstruction
loss, AdamW lr0.01/decay0, same512 updates/two seeds. It has more independent
parameters and a different LR: optimization feasibility control, NOT architecture
or equal-parameter comparison and NOT deployable.

Advance only if at least one NETWORK objective reaches mean full-teacher Δz NMSE
≤0.1 in BOTH seeds. Free-table success alone does not advance. Stop at first failed
stage or after stage16. Report oracleR32 floor, full per-AA errors, normalized factor
errors, exposures, latency/memory and failure status. This diagnostic threshold is
not a geometry or deployment acceptance threshold. No automatic larger model run;
pair-content architecture changes require interpretation of this result first.

## R32 plus residual oracle

Reuse all eight previous validation parents, sixteen sites, 304 mutants, two original
noises230201/230211. This panel is now a reused representation-development panel,
NOT fresh independent confirmation. Existing exact/WT-s_inputs baseline/R32 decoded
coordinates must replay bitwise. Fixed native target atom graph/reference chemistry,
oracle target s, WT s_inputs; frozen native S1. No altered geometry thresholds.

Arms: Exact, baseline, R32, R32+mutation row/column, R32+contact-local,
R32+top residual magnitude at row/column budget, R32+top at contact-local budget.
Residual is exact hard Δz minus per-channel FP64 SVD R32. Masks store complete
128-channel directed pair entries. Contact-local is N(i)×N(i), where N(i) is WT
prediction noise230201 Cα distance≤8Å or sequence distance≤2; no GT or mutant
coordinate used to choose locality. Top masks sort residual squared channel norm,
stable tie-breaking; these use teacher information, not inference-available scores.
No union-mask tuning, per-example winner selection, or post-outcome budget changes.

Storage: FP32 factors2LCR×4 bytes plus each stored pair C×4+8 index bytes, divided
by dense Δz bytes. Include geometry transitions per identity (fixes AND newly broken
instances), 19-AA ranking/regret, local tails and per-protein metrics. A mask may
improve latent error while harming decoder geometry. No assumption of monotonicity.
Do not equate this oracle with a learned sparse-correction predictor.

Both batches stop and report at fixed endpoints. Old models, thresholds, and
teacher packets remain intact. Scope is protein hard-mutation response (explicitly
authorized), not the unrelated initial fixed-glycan scope retained in AGENTS.md.
