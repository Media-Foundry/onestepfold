# Reference-anchored native pair suffix: fixed-budget training

Locked separately after the completed2026-10-10 reference-anchor audit. The
audit verified identical initial predictions and a change in TRAIN gradient
alignment; it performed no optimization or decoder evaluation. Its initial
gradient findings are not evidence of convergence or transfer.

Prediction is U_theta(candidate)-[U_theta(WT,site)-native_WT_C4_pair]. U is the
same stage-aligned native Mini pair suffix used by the preceding full-batch
AdamW controls:1,315,332 parameters, copied blocks14/15 and the same edit branch.
Candidate inputs/single stay exactly their own unadapted final-recycle values.
The reference branch uses only WT conditioning and its audited block13 cache.
Native Mini/S1 stay frozen. No target oracle inputs, ESM/MSA preparation, new
teacher states, extra native recycle, rank restriction, S1 training loss or
changed output head are introduced. All earlier quality conclusions stand.

At fixed parameters the subtraction cannot improve centered AA predictions in
real arithmetic. The AA-objective gradient is unchanged; the common-objective
gradient changes through the reference branch. This changes training dynamics,
not the centered-AA function class. Ordinary FP32 cancellation remains measured.

Two from-initialization runs, seeds272001/272003. Same15 TRAIN references,
27 sites and513 mutants, same TRAIN-only q_i and Final pair MSE. For each full
pass, average19 gradients within a site in native FP32, including one shared
WT pullback; average27 site gradients in CPU FP64. No candidate sampling or
randomized order. AdamW lr1e-4, weight_decay1e-4, eps1e-8, betas(.9,.999), global
clip1. No scheduler. Exactly128 full-gradient evaluations/updates:65,664
candidate forwards/backwards per seed. Additionally3,456 reference forwards
and backwards per seed. Reference graphs are rebuilt per site and parameter
version; the detached proxy receives an explicit once-per-site pullback.

Reuse the already closed full-batch AdamW272001/272003 controls. Their initial
hashes, objective, source/data locks, fixed-node predictions and source hashes
are bound before launch. The preceding audit reproduced the legacy full
gradient exactly. This is a matched objective/candidate-exposure/optimizer
comparison, not equal FLOPs or equal wall time. No L-BFGS or hyperparameter grid.

Preflight includes CPU FP64 streamed-vs-joint gradients and three AdamW updates,
all entry-point imports, reference-cache hashes and source hashes. First real
full gradient must match the completed audit's anchored vector within relative
L2 5e-5 and its initial objective within rtol2e-8/atol1e-10. Stop and retain any
failure; do not change tolerances or resume to obtain a favorable outcome.

Fixed checkpoints0/32/128. All48 sites x19 candidates x two archived noises
are decoded at every node without an NMSE gate. Node0 must exactly reproduce
archived unadapted coordinates. At128 also use the same pre-fixed cyclic
wrong-AA residual assignment, preserving the receiver's B_inputs/B_s/B_z,
chemistry and noise. Score all nodes; terminal128 is primary. No winner selected
from intermediate results. Total per seed:2,736 correct prediction forwards,
144 evaluation reference forwards,6 candidate isolation forwards plus2
reference isolation forwards,7,296 S1 calls. Independent checkpoint verifier
performs another2,736 candidate and144 reference forwards, without S1.

Keep raw/common/centered residual measures and predicted energy separate.
TRAIN full objective is site weighted; report protein-weighted residuals and
decoded metrics by TRAIN/same-protein-new-site/new-protein as before. Preserve
ranking, old-select/new-evaluate raw regret, median/worst risk, Top1, AA response,
geometry transitions, severe clashes/chirality and displacement tails. Compare
with unadapted, fixed-single/oracle-pair, matched old AdamW and wrong assignment.
The nine repeatedly used new-protein references remain development data.

Higher TRAIN AA recovery supports a learning benefit only. Held improvement
must exceed the unadapted baseline, not just wrong assignment; structure and
choice risks cannot be combined into a promotion on one better average. A
negative result closes this fixed-budget graph hypothesis, not all reference
architectures. There is no convergence/capacity claim, new speed claim or
independent confirmation in this trial.

Reuse the24 WT block13 caches built in the preceding audit (473,680,104 bytes
including saved block14). Native preparation there cost24 WT-only recycle calls;
not repeated or hidden as free. Learned anchors depend on site and parameter
version and cannot be reused across updates/sites. Candidate order does not
modify reference memory. Any future deployment timer must include construction
and application of the learned reference branch and the candidate native work.

HIP0/1 train the two seeds; CPU scorers have no visible HIP device; HIP4 performs
serial tensor verification. HIP5 is occupied by unrelated work and untouched;
6/7 unused. HIP_VISIBLE_DEVICES is the only visibility variable. Finite six-hour
training cap and two-hour score/verification caps, immutable code/data/protocol
lock before launch, no automatic restart, all logs/failures retained.
