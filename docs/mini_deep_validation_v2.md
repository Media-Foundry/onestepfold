# Deep Validation v2 — locked protocol, 2026-10-02

User authorizes longer bounded diagnosis after `0994b643`; this is a NEW experiment,
not revision of old stopping rules. C4/S1 and native chemical graphs remain unchanged.
No AA-axis PCA, no additional teacher collection except the explicitly gated blockwise
capture/timing checks, no BindCraft or sequence design, no Δs training.

**Resource constraint: HIP_VISIBLE_DEVICES only, physical devices 0–5.** Remove inherited
CUDA_VISIBLE_DEVICES; never set it to a duplicate selector. No work on devices 6/7.
Use at most six GPU workers, one per allowed device. Hash immutable runtime code,
teachers, jobs and checkpoints. Unexpected errors stop dependent stages and remain
reported; do not replace failed jobs with new settings.

## A. Continuous single-site optimization and factorial controls

1W53 T37 (zero-based36), all19nonWT. Fresh seeds231301/231303. Each update sees all19;
AdamW eps1e-8, weight decay1e-4, clip1, constant LR. One uninterrupted8192-update
trajectory, checkpoints512/1024/2048/4096/8192; initial and64-step diagnostics.
No selected intermediate endpoint or extra updates. Curves need not converge by8192;
report plateau evidence rather than calling the budget convergence.

Network configurations, each at LR1e-4/3e-4/1e-3 ×two seeds (30 runs):

| Architecture | Representation | Purpose |
|---|---|---|
| small bias, width128/two blocks | R32 factors | exact original architecture |
| large bias, width256/four blocks | R32 factors | capacity |
| small pair-content | R32 factors | edge-value messages, parameter matched |
| large pair-content | R32 factors | capacity×content |
| small bias, direct dense row head | unrestricted dense z, length84 | output diagnostic only |

Pair-content adds Σ_k α_jk W_z LN(z_jk) into attention values, gated by candidate-
dependent query; FF hidden width compensates added edge parameters. Actual parameter
counts are reported (not assumed10M). Quadratic pair operations, no triangle path.
Dense head maps each generated node to L×128 values without UV factorization. It has
a different output parameter count and fixed length; not a transferable candidate.

Free-factor controls: same initial factors as original small network, 8192updates,
lr0.01/decay0, two seeds, all19. This keeps the prior control optimizer; the three-LR
grid applies to neural generators. Free factors are NOT equal-capacity/equal-LR rivals.

Metrics: per-AA/full-mean NMSE, oracleR32 floor, centered AA-specific NMSE/energy,
prediction energy, gradient norm, update/weight norm, time/memory. No S1/geometry loss.
Norm-ratio diagnostics every64 updates; all five checkpoints retain optimizer/RNG.

Primary gates at final8192 only: free factors BOTH≤0.075; neural arm BOTH≤0.10.
≤0.12 is reported secondary only and does not advance. No gate based merely on decline.

## B. Oracle input decomposition (six matched additional runs)

Predeclared large pair-content at3e-4, same two seeds/8192 updates. Identical adapter
parameters, input modes: all WT s_inputs; only mutated row replaced by target s_inputs;
full target s_inputs. All modes also receive WT s/z and hard query. No target s/z is
given to the predictor. These six runs isolate input availability at one fixed LR;
the WT-adapter arm controls added parameters/common WT input. They are diagnostic,
not eligible for WT-only model selection. Strong gains do not prove WT-only information-
theoretic insufficiency, nor isolate ESM from all other components of s_inputs.

## C–E. Prespecified sequential transfer gates

Among WT-only FACTOR arms passing A, choose smallest final two-seed mean training NMSE;
ties within1e-6 prefer fewer parameters, then LR closest3e-4, then fixed name order.
No held-out score selects architecture/LR. Free/dense/oracle-input arms are ineligible.

C: reuse selected A8192 checkpoints, no further fitting; evaluate 1W53 site84 (zero83),
which NEVER entered A. Both seeds must have mean NMSE<0.80 AND centered NMSE<0.80:
a predeclared20% reduction relative to zero response, an engineering screen, not a
universal scientific boundary. Failure closes the ladder without broad training.

D: if C passes, fresh selected architecture/LR, first archived site of TRAIN parents
3/4/5 (1W53/1JHG/1A7G),8192 total updates, cyclic19-AA site batches. Hold out their
second sites, and BOTH sites of parent6 (4PT4). Training BOTH≤0.10; both seen-new-site
and unseen-protein categories BOTH satisfy<0.80 raw and centered NMSE. No holdout
selection. Existing sequence-group isolation applies; not all-history/pretraining unseen.

E: only after D passes, fresh selected architecture/LR, all16TRAIN×2sites,8192 total
updates, cyclicsite batches; evaluate all8 prior validation parents×2sites. Preserve
their repeated developmental use; not independent confirmation. Training≤0.10 and
validation<0.80 raw/centered in both seeds are separate reported conditions.

## F. Conditional functional refinement

Only if E training and validation BOTH≤0.15 (and full E gates passed), and each
seed's validation mean changes by at most5% between4096 and8192:1024 additional
updates, paired latent-only continuation vs latent+frozenS1 per initialization.
Same ordered candidate/noise draws (seed232501), no validation parameter updates.
Functional weights fixed from prior pilot: coordinate .25, CA-distance .25, clash .01,
checked chirality .1, plus unit latentNMSE. Final1024 only, no best-checkpoint selection.
No functional loss on poorly fitted bulk mappings. This retains exact target s: still
a factor-only diagnostic, not the complete WT-only output pipeline.

## G. Functional and timing audit

When a WT-factor arm passes A, decode both selected seeds at last reached stage on
seen site, held-out site, and fixed old6UFE-92 stress input. If E reached, additionally
evaluate its entire validation panel. Exact, WT-s_inputs baseline, WT-z, oracleR32,
and student arms share native target chemistry and noise. Rebuild every target graph.
Report19-AA Spearman, Top1/regret, per-protein and P95/P99 local RMSD,>1Å count,
geometry transitions, not merely pooled means. Stress/seen/unseen remain separate.
F arms, when eligible, are evaluated uniformly alongside their paired continuation.

Timing after training on an allowed GPU: warm repeated native C4 for WT and all19hard
mutants, source features/ESM separately, student20-query factors AND dense expansion,
and memory. Fixed10timing repeats after3warmups for student;3C4 repeats per sequence.
Desired response<0.25×oneC4; acceptable<oneC4. Also report first-source vs amortized
costs and Σ20C4. Oracle target s and chemistry/decoder costs are not hidden: this
cannot claim complete end-to-end acceleration or deployment even if z timing passes.

## H. Bounded fallback, not another fit sweep

If free-factor gate fails: stop architecture promotion, report optimization-ceiling
failure. If all neural arms including dense and oracle inputs fail primary single-site
fit despite a passing free gate: capture nativeWT+19hard mutant trajectories once,
four-block boundaries within each of four recycles plus stage inputs. Replay final
archived C4, record response energies, cross-boundary changes and spatial-R32 residuals.
Keep complete selected boundary tensors. No AA-axis compression, no automatic training
of a new blockwise student, and no claim a complicated final mapping is impossible.
If only dense/oracle-input succeeds, report that distinct outcome and stop WT-only ladder.

The controller records skipped phases with explicit gate evidence, as well as all
failures. The comparisons can identify useful interventions; they cannot uniquely
separate capacity, optimization, data diversity and information sufficiency in all cases.
