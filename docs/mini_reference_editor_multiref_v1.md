# Mini reference editor: multi-reference structure-learning protocol v1

Prepared 2026-10-07 after review of `bef762d0`. **Data and experimental design
are specified; the direct control and multi-reference runner are not implemented
or trained.** The two-site pilot remains closed. This document does not report
new model quality, convergence, transfer, or acceleration.

The first question is whether one shared editor can learn complete candidate
structures across several references. The second is whether its iterative
workspace helps relative to a parameter-matched direct global writeout. A nested
3/15-reference comparison measures a small learning curve. These are teacher
fidelity experiments on reused development data, not experimental mutant
prediction or independent family confirmation.

## Fixed model and supervision

Retain public `protenix_mini_esm_v0.5.0`, checkpoint SHA-256
`1301bba9ad322518eace60fd244ded7904439f55317e90d402cc7a0c06026664`.
Reference Mini and S1 remain frozen. Use archived native FP32 C4 reference
`s_inputs/s/z`; predict all three candidate tensors and rebuild candidate S1
caches using that candidate's native atom inventory and reference chemistry.
Target C4, target input encoder and oracle target conditioning are forbidden
inside either model's inference/training forward. Target conditioning may be
loaded in a separate exact-replay preflight and must then be removed.

Use the existing pilot loss, without changes:

`aligned all-heavy coordinate MSE + 0.25 CA-distance MSE + 0.01 severe-clash penalty + 0.01 checked-chirality penalty`.

Use detached optimal proper rotation as before. Candidate losses are averaged;
no latent loss, ranking loss, candidate-difference loss, differential attention,
rank truncation, mutation-anchored pair injection, or decoder unfreezing. These
would be separate interventions. Teacher coordinates and geometry quality are
distinct targets: native teacher failures remain in the data and in reporting.
The parent experimental backbone is used only for the existing evaluation score,
never as a mutant coordinate label or as editor input.

## Verified archive and fixed split

[Preparation artifacts](../reports/mini_reference_editor_multiref_plan_2026-10-07/README.md)
contain all 48 site assignments and source hashes. On 2026-10-07, all **2,808
payload files / 9,721,483,922 bytes** passed fresh remote size and SHA-256 checks.
There are 24 references, 48 sites and 912 distinct non-WT candidates. This is a
file-integrity check, not a new tensor replay or a new chemical-data audit.

The historical archive was split 16/8. Preserve the later development boundary:
exclude **all of 4PT4** from training and keep 1W53 Y84, 1JHG N25 and 1A7G S34
out of updates. Do not quietly restore the original 16-reference training list.

| n15 role | References | Sites | Distinct non-WT candidates |
|---|---:|---:|---:|
| TRAIN | 15 | 27 | 513 |
| Same-reference new-site DEV | 3 already in TRAIN | 3 | 57 |
| Held-reference DEV | 9 | 18 | 342 |

The nine held references are 6AHP, 1X8D, 2EBE, 4PT4, 3SXZ, 4PQL, 6ZRW, 1YSB,
2FKZ. The archive's 24 references occupy 24 historical sequence/accession
components. This preserves that operational split; it does not prove absence of
distant homology or base-model pretraining exposure. Every panel has development
history. Neither new initialization nor a different noise creates an untouched
confirmation set.

The n3 subset selects the lowest eligible parent index in each original length
stratum: **1W53 T37; 2DP9 L49/Q52; 1DZR L13/A179**. It has five sites and 95
candidates. It is selected by this rule, not by teacher response or model results.
It is a strict subset of n15.

Evaluation labels follow actual update membership. Y84 is a same-reference
holdout at both sizes. N25/S34 change from unseen reference at n3 to seen reference
at n15; report that transition separately. The 22 sites added to TRAIN at n15 are
an expansion panel at n3, not part of the common held-reference transfer result.
The same nine held references / 18 sites form the cross-size transfer comparison.

TRAIN n15 covers 12 original AA types. A/D/E/G/I/L/T/V have instances on multiple
parents; N/P/Q/S each have only one. This improves coverage but does not provide
many environments for every directed substitution. Preserve these counts and
report seen/unseen original-AA strata descriptively; do not claim full coverage.

## Two architectures

**Workspace:** use the `bef762d0` ordinary-attention architecture unchanged:
width 256, 32 work tokens, four blocks, eight heads, late dense pair width 128,
pair chunk 16, 9,352,387 registered parameters. Reference memory uses single/input
projections and WT pair row/column means; full WT pair content enters late
writeout. This is not mutation-anchored `z[i,j]/z[j,i]` workspace input.

**Direct global:** retain the same reference projections, hard-edit encoder,
single/input heads, full-WT-pair late writeout and empty-edit anchoring. Remove
learned workspace tokens and all workspace attention blocks. For a candidate,
let `e_j` be the existing edit vector at edited positions and zero elsewhere;
let `q` be its mean over edits (zero for no edit). Initialize every node with
`h_j = memory_j + e_j + q`. Apply four shared, residue-wise residual blocks:

`h <- h + Linear(4096,256)(SiLU(Linear(256,4096)(LayerNorm(h))))`.

Use final node mean in the existing `pair_work` projection. Generate the three
conditioning responses against the identical no-edit branch, with the existing
explicit no-edit gate. This permits distant single and pair changes, multiple
lengths and positions. It is not the old fixed-length whole-field table, and it
is not simply setting the current model's block count to zero.

The specified modules imply **9,320,643 registered parameters**, 0.34% below the
workspace model. Verify actual counts and gradient-used parameter counts before
training; do not add inactive weights to match totals. Shared named modules must
receive identical initial tensors for a paired seed. Architecture-specific
modules use a separate deterministic initialization stream. Both data sizes start
from the same architecture/seed initialization. Cache ownership/version checks,
candidate isolation, serial kernel shapes and empty-edit anchoring are identical.

This is an architecture comparison at nearly equal parameter count, not equal
FLOPs or an isolated test of a single attention operation. Broadcast edit input
and feed-forward capacity are explicit differences. Record wall time, S1 counts,
peak allocation and output response statistics for both.

## Fixed exposure and checkpoints

Eight fresh runs: **2 architectures × 2 sizes × seeds 272001/272003**. No pilot
checkpoint continuation. AdamW lr 1e-4, weight decay 1e-4, eps 1e-8, global clip 1;
no scheduler, optimizer search or automatic extension.

Sort training sites by `(parent_index, position_zero_based)` and visit them round
robin. At that site's zero-based visit `t`, train the two non-WT AA at cyclic
indices `(2t mod 19, (2t+1) mod 19)` in `ACDEFGHIKLMNPQRSTVWY` order with WT
removed. Rebuild trainable reference projections for the current parameter
version and share their graph across the two candidates. Raw reference memory
is persistent. Use **230201 only** as the training-coordinate noise; evaluate
both 230201/230211, with their historical development status disclosed.

| Size | Updates/run | Candidate training decodes/run | Exposures per AA/site |
|---|---:|---:|---:|
| n3: 5 sites | 3,040 | 6,080 | 64 |
| n15: 27 sites | 16,416 | 32,832 | 64 |

Terminal budget is 608 updates per site. Save and evaluate at 0, 152, 304 and
608 visits/site, corresponding to 0/16/32/64 exposures per candidate. Terminal
is the primary endpoint; never select the best intermediate checkpoint.

Also save n15 at total update 3,040 for a secondary equal-update comparison with
n3 terminal. Sites then have 112 or 113 visits; report actual AA exposures.
Equal updates/decodes is not equal compute because lengths differ. Primary
terminal comparisons hold per-candidate exposure constant while adding contexts;
the secondary comparison holds update count constant while reducing per-site
exposure. Neither alone isolates every effect of data scale.

Total planned training is **77,824 optimizer updates / 155,648 candidate S1
decodes**, plus separately counted audits and evaluations. This budget has not
been executed. It is a bounded learning curve, not a promised convergence budget.

## Preflight and evaluation

Before fitting, freeze implementation and hashes. Independently verify the split,
exposure schedule, initialization pairing and registered/active parameter counts.
Require focused cache/no-edit/order/multiple-edit input tests, finite nonzero
gradients through all three predicted conditioning branches, frozen Mini
parameters, and exact archived teacher replay for all evaluated candidates/noises.
The inference packet must have no target conditioning. Log prohibited-call
counters throughout. Integrity failures stop the run and retain artifacts;
corrections receive a new frozen execution revision before fitting resumes.

At every fixed checkpoint decode all 48 sites, 19 non-WT AA and both noises;
report the split applicable to that run. No NMSE gate. Reference-only is all WT
conditioning plus candidate chemistry and S1, with no trainable editor; Exact
is native candidate C4/S1. Never import old oracle-target-s WT-z numbers.

Report per site and then equal-weight parent summaries, keeping TRAIN,
same-reference holdout, common held-reference and n3 expansion/transition panels
separate. Include:

- CA/all-atom lDDT to same-noise Exact; local/global RMSD and P95/P99/max, >1 Å.
- Mean and centered candidate distance-response errors on mapped CA atoms. This
  is evaluation only, not an added response loss; no alignment across different
  atom inventories without explicit mapping.
- Per-noise and two-noise-mean 19-AA Spearman, Top1, Top-k recall, score MAE;
  old-noise choice evaluated on new-noise Exact, its raw regret and Exact's own
  old-select/new-evaluate reference. Fix top-k to 3 and 5; do not choose k later.
- Absolute geometry pass, Exact pass→method fail and fail→pass separately;
  checked signed volumes, severe clashes, and failure identities. Never substitute
  net pass count for transitions or use teacher geometry as chemical truth.
- Per-site exposure, actual updates, raw loss components, preclip gradient norm,
  clipping fraction, response energy and failed/nonfinite seeds, including failures
  rather than rerunning until two good seeds appear.

Keep Y84's large structural tail and T37N/noise230211 (Thr25 Cβ check) as named
regressions. Retain 6ZRW P80L in the common held panel. **6UFE-92 is absent from
this archive:** it remains an uncovered historical stress case, not an implied
passed test. Do not silently merge a different teacher archive to include it.

Any uncertainty interval resamples parents, not mutant/noise outputs as independent
proteins; report both seeds individually. No validation-based early stopping,
per-protein method choice or selection of new checkpoints after viewing results.

## Cost boundary and implementation limitations

Keep model-only timing with prebuilt native candidate chemistry and raw reference
memory; ESM/MSA preparation is outside this cycle. Separate reference projection,
candidate edit/writeout, S1/cache generation and combined 19-candidate workload.
Cache once vs rebuild the same new-model projection is a cache correctness/cost
comparison, not a comparison against native mutant C4. A folding-model speedup
claim additionally needs matched reference-C4 plus 19-candidate timing against
19 native C4+S1 calls with equally prepared inputs. If not measured, say so.

The current serial forward **retains candidate outputs and concatenates them**;
chunked pair writeout also materializes dense z. It is not a streaming interface
with candidate-count-independent peak memory. Empty-edit pair writeout is still
recomputed per candidate. Preserve that behavior for this quality comparison;
future empty-write caching or parallel execution requires separate equivalence
and cost checks and must retain the shared training backward graph.

## Decision rules

Better multi-context training is evidence of learnability, not transfer. Better
held-reference ranking with worse raw regret or structural tails is a tradeoff,
not promotion. Similar direct/workspace quality gives no evidence that iterative
workspace is necessary. A workspace gain must be assessed against its measured
cost and across both seeds; no universal causal or sample-size claim follows.

Only consistent held-reference response and selection gains without concealed
geometry/tail regressions justify planning larger, independently split data.
Failure leads to closing this bounded comparison, not automatic longer runs,
Diff attention, rank changes, loss changes or Mini unfreezing. Even positive
teacher fidelity does not establish experimental mutation accuracy or a calibrated
20-AA distribution.
