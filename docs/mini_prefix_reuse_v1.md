# Matched-depth WT prefix reuse v1 — 2026-10-06

Follow the closed native budget curve 7d9206cf. C4 remains default. Test exactly
WT2→Target2 and WT3→Target1, with fresh cold C2/C4 references. No training,
coefficient search, per-protein branch selection, soft inputs, or adapters.

Use the same archived eight DEV parents/four ADLT sites each and separate 2V66
stress stratum. 693 hard sequences, four noises 230201/230211/310003/310019,
public Mini FP32/live ESM2-3B/native features seed101. No new data/downloads.
All previously seen panels remain development; no independent confirmation.

Only recycle-carried token s/z are shared. Once per parent, build WT native
features and ESM, run WT C4, capture completed cycles2/3 with detached clones,
and decode/score its four WT noises. For each mutant and each arm, independently
rebuild its own features, ESM, atom graph and reference chemistry. Recompute the
complete target input initialization and inject it through every remaining native
recycle bridge. Diffusion uses that path's own s_inputs/s/z and newly prepared
candidate caches. Never keep oracle target s. Stored WT prefixes are read-only;
each continuation clones both tensors and verifies the source remained unchanged.

Implementation gate before screening: compare the new zero-state four-cycle
path against frozen full_recycle_pairformer; verify exact WT2+2/WT3+1 and true
target2+2/target3+1 recovery of native target C4. The target prefix is used ONLY
in this audit. Audit every parent's WT and first non-WT candidate before its
screen. Capture and restore exact CPU/CUDA torch RNG, Python and NumPy RNG at the
completed prefix boundary. Restore after recomputing target initialization,
before the first continuation cycle. Audit final RNG as well as all tensors
against unsplit native execution. Each candidate restores the source prefix RNG
independently; no candidate inherits another candidate's random state. Also validate all source snapshots after reuse.
All C4/WT coordinates replay previous archive bitwise; failures stop the batch.

Arm IDs in machine records: 2=cold C2, 4=cold C4, 22=WT2→Target2,
31=WT3→Target1. IDs22/31 are labels, NOT cycle counts. Rotate all24 arm execution
orders. Each mutant arm is independent, no cross-candidate state mutation.
Warm arms each charge the full measured once-per-parent WT C4 preparation,
capture and WT decode/screen/write cost, plus measured prefix cloning/read cost
in their target continuation time. Both use the same saved WT C4 output as WT
score baseline. Cold arms charge their own WT generation. Source model load,
source prefix bytes and device peak memory are recorded. Resident workload
includes native features, ESM, trunk, four-noise S1/host transfer, geometry/task,
NPZ writes and parent setup. Separate integrity-audit costs and additive first-use
model-load estimates; no confidence/CIF service or theoretical cycle speed claim.

Preserve the preceding protocol's score, masks,19-non-WT ranking, old-select/new-C4
regret, absolute geometry, pass→fail/fail→pass and local/global structure tails.
Main8parents and2V66 remain separate. C4 model coordinates are not mutant GT;
WT-only experimental accuracy remains separate. Reuse offline evaluator logic
with explicit arm enumeration. Both warm paths evaluated in full; no promotion
on an intermediate result. Report comparisons to both C2 and C4.

Bounded controller: prepare→integrity gate→screen→offline score→collect→audit→
summary. Four workers, per-worker screening bound3600s, no outcome retries.
No automatic WT1/WT4, mixing, blockwise or training follow-up. Outcomes distinguish
improvement over coldC2, preservation of C4, and actual workload saving.

## Pre-screen implementation amendment

Initial root prefix_reuse_v1_20261006 stopped in its gate after80.025s: the first
completed worker found native trunk RNG advancement despite eval/no dropout.
No screening or outcome evaluation ran. Frozen source/logs are preserved.
Protenix MSAModule calls random MSA sampling in eval; sample size generation can
advance RNG even for a single-row MSA. The corrected root
prefix_reuse_v1b_20261006 captures actual cycle-boundary RNG with s/z, restores
it on continuation and compares final state against native. This replaces the
incorrect assumption of RNG invariance, not any quality threshold. Native module
hooks record where RNG advances. No sampling kernel, model weight, loss,
scientific arm, or candidate set is changed. This is a pre-outcome implementation
correction, not a retry seeking better quality.
