# Mini candidate final-recycle internal adaptation v1

Locked before outcomes, 2026-10-08. User authorizes continuation after closure
of external compensation study 3cdc78d5. No external prefix compensator here.

## Question and computation

Does adapting pretrained candidate computation improve WT3→Target1 continuation,
relative to the SAME unadapted continuation, on held reference environments?
Original Mini protenix_mini_esm_v0.5.0 reference encoder, initialization, MSA,
attention, and S1 remain frozen. Cached WT cycle3 s/z and boundary RNG are read-only.
Actual candidate archived s_inputs, raw MSA features and chemical graph are legal
inputs. No candidate final s/z input, no input encoder, no ESM/MSA preparation,
no RCSB, no new teachers. Native MSA execution remains part of folding.

Only 32 output projections (pair/single transition in each of 16 main Pairformer
blocks) receive weight residual B A, rank16, alpha16, no bias/dropout. A uses
Kaiming-uniform, B is zero. Dimensions 512→128 and1536→384;655360 parameters.
This is weight-update rank, not AA-response rank or spatial-response rank.
No rank/LR/placement sweep. This placement tests transition-output adaptation;
failure does not test all possible native adaptation.

Adapters are external parameter banks, attached through temporary forward hooks
ONLY around one candidate final recycle. They are not registered on Mini, never
merged, absent from reference C4 and S1. This runtime explicitly sets native
Pairformer activation checkpointing to None, because backward recomputation
outside the hook scope would be incorrect. No-grad native inference already uses
None; memory impact is reported. The first bundle stopped on this guard before
any cycle, gradient or quality output; the corrected bundle preserves that failure.
A second bundle stopped on the old runtime work-directory collision before model
load; each new bundle now owns its absolute work directory. Neither failure
produced a trained outcome or changed any experimental setting.
v1c completed the first seed's full912candidate zero replay, then stopped at the
overstrict all-projections-nonzero-gradient gate. A fixed TRAIN T37A probe found
native block12/13 single-transition output weights AND inputs exactly zero;
their output gradients were nonzero(.0021113), so the backward path was connected.
Those two locations remain in the unchanged bank; the gate now records activation
and output gradients, permitting zero weight gradients ONLY at those two locations
when their measured inputs are exactly zero. All active projections must pass.
All original parameter hashes, requires_grad flags and empty gradients are checked.
No-edit dispatch bypasses adaptation and returns original WT continuation. This is
an explicit inference rule, not evidence that learned updates vanish on WT inputs.

## Fixed data, optimization and arms

Same archived source as compensated_recycle_v1d_20261007, source manifest hashed.
15 training parents/27 sites/513 nonWT variants;3 same-parent new sites;
9 whole held parents/18 sites. All development, not independent confirmation.
No protected site or whole held parent enters training. Full48site evaluation.
Fresh seeds272001/272003;8208 updates each;two candidates/update following original
multiref schedule;32 exposures/AA/site. Four dry updates(2/seed) discarded.
Checkpoint0/4104/8208;terminal primary, no intermediate selection or seed exclusion.
AdamW lr1e-4,wd1e-4,eps1e-8,clip1, no schedule. Original coordinate objective:
aligned heavy-atom MSE+.25 CA-distance MSE+.01 severe-clash+.01 checked-chirality.
Train noise230201;eval230201/230211. No latent/ranking objective or decoder unfreezing.

Arms: Exact native C4, reference-only historical baseline, unadapted WT3→Target1,
and adapted terminal(and fixed diagnostic checkpoints). LoRA has no separate AA
query; no wrong-query control is fabricated. Correctness of full candidate inputs
is held fixed. Adapted-versus-disabled is the primary intervention. Prior external
compensation results are historical context, not parameter-matched causal controls.

## Integrity gate

Existing24WT/912target split replay audit is reused via source hashes. Before any
formal training: both zero-init banks must reproduce all912candidates×2noise
unadapted coordinates bitwise. All weight gradients must be finite and present;
every projection output must receive nonzero gradient. Active up gradients must
be nonzero;after one discarded update, active down gradients too. The two proven
dormant-input locations follow the explicit check above. Disabled native replay after a
nonzero update, candidate order, WT24 continuation, immutable caches and native
weights must pass. Local tests cover exception-safe hooks and no native gradients.
No changed numeric tolerance following results. If preflight fails, stop and retain
failure; fix only diagnosed implementation issues before outcomes with new bundle.

## Evaluation and timing

Independent coordinate-only audit: per-noise and mean-noise Spearman/Top1;old-noise
selection evaluated on new Exact noise raw regret;Exact self-noise reference;
parent-equal means/medians/worst;centered-AA CA-distance response RMSE;all-atom
lDDT;local RMSD P95/P99/max/>1A;absolute geometry and both pass/fail transitions;
continuous signed chirality volumes. TRAIN/same-parent-new-site/held-parent separate.
Protein-paired descriptive bootstrap contrasts adapted-disabled. No target-dependent
calibration. Teacher output fidelity and backbone proxy score are not experimental
mutation truth. Nine held proteins reused for development;6UFE92 absent.

Fixed checkpoints replay on T37A/two noises. Terminal disabled restoration across
48sites, fixed candidate order and no-edit bypass checks. Serial isolated timing
on1W53L84/19mutants/oneS1,6 rotated repetitions, discardfirst and medianremaining5.
Include cached initialization, WT C4 once for continuation arms, hooks/LoRA, native
remaining cycle and S1 cache+decode. Cold baseline executes19C4+S1. Exclude input
preparation, load, disk and scoring. No pipeline speed claim. No speed promotion
without quality. Model size/peak memory/actual native cycle and S1 counts reported.

## Controller and decision

Preflight→two fixed runs→independent CPU scoring→serial replay/timing. No automatic
extension, checkpoint replacement, additional seed or architecture.6h/run timeout,
failed runs retained. Runs use guarded HIP0/1 only, preserving reserved hardware.
Main judgement: net held response/selection improvement beyond unadapted;both seeds
and geometry/high-cost tails disclosed. Training fit alone is not migration success.
Any future confirmation requires unseen families. Current protocol does not promise
success or claim that updating native transitions is the unique remedy.
