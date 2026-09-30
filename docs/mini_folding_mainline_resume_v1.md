# C4/S1 folding first: mainline correction and bounded next cycle

2026-09-30. The user explicitly restored the order: first improve and validate the
C4/S1 folding model, then consider BindCraft integration. This supersedes the
interface-priority decision in commit56747495. No target/complex is required now.
No further monomer mutation search, binder setup, new repair architecture or
backward-debugging matrix is part of this cycle.

Current retained candidate: pretrained Mini-ESM, ESM2/Pairformer frozen, C4/S1/K1,
69,777,841 native diffusion parameters fine-tuned on128 proteins for512 updates
and2048 exposures. Its frozen fresh32 comparison found AA-lDDT0.801482 versus
nativeS1 0.798813 and S2 0.806460; chemistry improved overall but remains incomplete.
These are folding results. Mutation-proposal failures do not negate them, and
folding improvements do not certify design utility. Old fresh32 panels stay
excluded from training and further model selection.

## Released now: source expansion and independent audit

Resume the already frozen128→512 admission/order/isolation contract on HPC3.
DiamondHill new compute remains withheld after kernel-reported hardware memory
corruption; no new partial packets from the failed run are reused.

HPC3 rejected the proposed96CPUs/1GPU request before creating a job: acd_u permits
at most12 CPUs per requested GPU. Execution amendment: two shards,12 workers each,
all internal threads1, minimum1 unused reserved GPU each, visibility empty. No
source rule, ordering, partition index or qualifying function changes. Preserve
original migration lock and record a separate resume lock/script hash. This
supersedes its96-worker execution setting only, without mutating that artifact.

After both shards succeed, apply the original global-order selection, then
independently reparse HSPs and reconstruct exclusions/selection. Audit native atom
identity, experimental GT mapping/masks, hashes and provenance, inherited packet
parity, unsupported chemistry and length/assembly composition. Preserve failures.
If fewer than384 new entries qualify, report the shortfall and do not relabel the
set TRAIN512. Extending the raw catalog requires another bounded search manifest,
not relaxed isolation or geometry rules.

## Next training comparison: specification before model updates

Once the data count and audit are complete, lock a two-arm folding experiment:
original TRAIN128 versus expanded training set, both starting from the same
retained full512 checkpoint. Keep C4/S1, native parameter scope, experimental GT,
explicit synthetic S2 auxiliary, chemistry definitions and current loss weights.
Use the same optimizer initialization, schedule and exposure/update budget in
both arms; record samples seen, per-protein exposure, GPU time and length mix.
Do not conflate dataset composition changes with a pure effect of sample count.
Exact budget and schedule must be frozen in machine-readable form after runtime
and data preflight, before either arm trains. No unbounded continuation or grid.

Report nativeS1/nativeS2/retainedcheckpoint references, common TRAIN128 and new
training-cohort curves separately. Predeclare a new isolated folding validation
panel before predictions; do not select a new checkpoint using the old fresh32
confirmation results. Primary readouts: experimental AA/Cα-lDDT, paired tails,
new/residual severe clashes and checked chirality, typed connection diagnostics,
actual C4/S1 execution and end-to-end cost. Legacy ideal-connection windows remain
historical diagnostics, not a sole veto. No chemistry or accuracy failures are
waived. Deployment readiness and BindCraft integration remain subsequent gates.

This document releases source reconstruction/audit and implementation preparation.
It does not claim a new512 set, a started training run or recovered S2 quality.
