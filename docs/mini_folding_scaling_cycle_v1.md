# Folding-only data/optimization cycle: fixed terminal comparison

2026-09-30. Supersedes the tentative512 training-size target for this cycle ONLY,
with explicit actual source counts. The unchanged catalog/source/isolation rules
could not supply512 in the initial pool. The complete remainder has only66
HSP-eligible candidates for an88-source shortage, before native chemistry checks;
thus this extension cannot fill512. Do not weaken support rules or delay the
folding comparison solely to hit a nominal round number. Preserve every source
stage's incomplete512 result. This is a new size/split protocol, not a retroactive
claim that the original source objective succeeded. Larger-scale sourcing remains
future work; this cycle does not meet the earlier30k training ambition.

After the final source audit, freeze the actual source set. Keep original128
TRAIN unchanged. Among never-predicted additions reserve32 new validation proteins
before any cache/model call:16 in each50–255/256–1024 bin, SHA256 rank prefix
folding-scale-holdout-v1:20260930:. Reassign their source-only TRAIN labels to the
new holdout in a separate manifest; no prior training/prediction used these rows.
All final source pairs already satisfy mutual isolation. Old validation64 remain
excluded and are not reread for selecting this cycle. Report exact expanded TRAIN
count as source_count−32, never call it512. Record length/assembly composition.

Two arms: original TRAIN128 and expanded TRAIN, from the SAME retained full512
checkpoint SHA7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829.
Both update all originally trainable native diffusion parameters, ESM2/trunk/
confidence/fixed Fourier constants frozen; public Mini-ESM, C4/S1/K1. No scratch
initialization, LoRA, parameterization change, relaxation or design objective.

Both reset AdamW state (not an exact optimizer continuation), betas.9/.999,
eps1e−8,weight_decay0,clip1,accumulation4. Fixed2048 newupdates/8192 newexposures;
LR warmup64 to1e−5, cosine to1e−6 at2048. Use prior exact full-scope loss weights
from archived training_lock.json, smooth-lDDT width.1Å, experimental observed GT
and explicit frozen nativeS2 synthetic auxiliary. Same twoTRAIN noise identities
600001/600011. Complete hash-shuffled passes then truncate the final pass at8192;
order SHA prefix folding-scale-order-v1:{epoch}:{group_id}. Record partial-pass
exposure counts. Equalupdates/exposures, not equalepochs/FLOPs or wallclock.

Cache native ESM2/C4 conditions separately from model updates; GT never enters
conditioning. Native reference predictions are not experimental GT. Verify source
hashes, model-weight hashes, cache reload replay, label masks and loss labels
before training. Preserve failed engineering runs. Confirm public and learned
checkpoint loading on HPC3 before releasing the two training arms. No validation
predictions during training; fixed terminal only, no early stopping or best-of.

TRAIN curves at0/512/1024/2048 on a locked32-protein original-TRAIN probe; full
terminal training metrics on original128 and added training cohort separately.
New validation32×two locked seeds810013/810029: publicS1, publicS2, retained
checkpoint and both terminal arms, no best-of-seed. Freeze runtime and scoring
before evaluation. AA/Cα-lDDT versus experimental GT, paired protein-level tails,
severe collisions, strict checked chirality/new damage, typed connection residuals,
length/assembly strata, actual C4/S1 calls and total runtime are separate outputs.
Legacy narrow connection maxima are historical diagnostics, not the sole veto.

This remains a bounded folding experiment; no binding efficacy claim or BindCraft
integration. Cache and training release require their engineering audits. Failure
to improve does not automatically justify more updates or a new method grid.
