# Full-TRAIN optimization of the stage-aligned Mini pair suffix

This separate2026-10-10 experiment follows the closed update audit d1ed39a8.
Its purpose is to test whether a more fully optimized feature-forming process
can recover TRAIN AA residuals and whether any improvement survives decoding
and the existing development panel. Neither model capacity nor transfer is
assumed solved. No new readout, architecture, loss weighting or teacher data.

Use the unchanged StagePairRecovery: candidate block13 boundary, original
candidate B_inputs/B_s, two native-aligned trainable pair blocks, and the
existing edit injection. Final z is predicted directly; B_s is fixed by the
interface. Copy the same two seed initializations272001/272003, with exactly
the same initial parameters between optimization arms. Reference Mini and S1
remain frozen. No new ESM/MSA preparation, candidate C4/recycle, hint generation,
soft chemistry, or target state as a predictor input.

Use the original15 TRAIN proteins,27 sites and513 non-WT candidates, original
site scales q and Final objective. The objective averages nineteen full-field
candidate squared errors within each site, then averages sites. All model
arithmetic remains native FP32; diagnostic error moments and cross-site
gradient aggregation use FP64 as in the preceding audit. Target pair is only
a TRAIN label. No new centered weighting, structural or ranking loss.

Four fresh runs: two optimization recipes x two paired seeds:

* Full-batch AdamW: lr1e-4, weight_decay1e-4, eps1e-8, default betas, clip1,
  otherwise the previous recipe. One complete TRAIN gradient per update.
* Full-batch L-BFGS: installed PyTorch implementation, lr1, history20,
  max_iter1 per call, strong-Wolfe line search, max16 complete gradient
  evaluations per call, tolerance_grad1e-7 and tolerance_change1e-9. No gradient
  clipping or weight decay. Every line-search trial is charged, including
  rejected/repeated points. A hard callback cap restores both parameters and
  curvature history if the library requests one evaluation beyond the remaining
  allowance. A returned state must exactly match a measured parameter hash;
  a loss increase beyond1e-10 causes transactional rollback and is reported.

This compares complete optimization recipes. Curvature, step selection,
clipping, decay and update history differ; improvement cannot be uniquely
attributed to line search or any one of these. lr1 is the L-BFGS search-scale
convention, not a claim that an unsearched unit gradient step is suitable.
No diagnostic fraction from the preceding audit is selected as a learning rate.

Each run receives exactly128 complete TRAIN gradient evaluations:65,664
candidate forwards/backwards. Checkpoints are0/32/128 gradient evaluations.
The optimizer call may be interrupted at32/128; already evaluated trials remain
charged, the unfinished proposal and its history are rolled back, and the next
budget segment resumes the last completed state. One-evaluation remaining
segments are allowed to record a repeated state without accepting an update.
Unchanged/rejected steps still consume the declared work; all are reported.
Updates are not matched between recipes, only full-gradient work and label
coverage. This is not equal wall time or equal accepted-step count. Old stochastic
Adam results are historical context, not an equal-update comparison.

TRAIN inputs/boundaries/labels may reside on GPU, with a fixed32GiB tensor-byte
cap, to reduce repeated host transfers. This cache is not a new approximation:
all original FP32 tensors remain unchanged, labels remain separate, and cache
construction/time/bytes are counted. Native generation is not rerun. Four runs
use HIP0..3; HIP4 is available for bounded tests and independent verification,
HIP5's other workload remains untouched; HIP6/7 are unauthorized. Only
HIP_VISIBLE_DEVICES is set. No mixed precision or kernel replacement.

Before the first update, initial model hash and all-candidate baseline S1
replay must match the frozen source. The first full TRAIN objective/gradient is
compared with the saved update-audit result for that seed: objective tolerance
rtol2e-8/atol1e-10; gradient relative L2 tolerance5e-6. This first gradient counts
toward128. Native module guards prohibit trunk/input calls throughout and
diffusion calls during optimization. No native parameter may receive a gradient
or change value. Candidate order and repeated-call isolation are checked.

Record every full-gradient evaluation's full/common/AA error, parameter hash,
gradient norm, actual optimizer work, accepted updates, rollbacks and runtime.
Do not select or tune using development data. Line search sees TRAIN only.
Fixed checkpoints are evaluated regardless of latent NMSE: all original48
sites, original two noises, candidate chemistry and frozen S1. Terminal128 also
uses the one fixed cyclic AA mismatch, with receiver B_s/input/chemistry kept.
Keep raw score errors, old-select/new-evaluate regret, Exact's own selection
reference, AA distance response, geometry transitions and severity, and tails.
Nine repeatedly used new proteins remain development data, not confirmation.

Expected per run:65,664 training forwards/backwards;2,736 fixed-checkpoint
candidate prediction forwards;7,296 S1 calls, including terminal mismatch.
Six additional repeated/order-check prediction calls per run are separately
counted. Evaluation-only tensor verification has a separate ledger. No new
inference speed result is claimed by training throughput or GPU caching.

Freeze source/protocol/initialization/label manifest and installed LBFGS source
hash before launch. Existing raw files and failed runs remain immutable. Four
workers have a six-hour common wall cap; each scoring or independent verification
worker has a separate two-hour cap. Preserve incomplete or failed runs; do not restart for
quality, pick a seed, or extend the budget. Focused CPU and actual-runtime tests
cover budget rollback of parameters AND optimizer history, exception recovery,
site-equal gradients with variable lengths, and AA error decomposition.

Success is assessed in layers: full objective optimization; TRAIN AA recovery
and correct identity; development decoded response, regret and geometry; then
actual folding cost in a future qualified comparison. Better total J alone is
not success. If J improves but AA or transfer does not, retain that separation.
