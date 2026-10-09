# Mini recycle response correspondence audit v1

Locked before reading diagnostic metrics, 2026-10-09. No training or changes to
models/losses/thresholds/checkpoints. Same48sites/24parents/912hardmutants and
four8208 LoRA endpoints from lora_noise_v1_20261008, plus disabled continuation.

Inventory:24WT3 states+boundaryRNG saved;912candidate native s_inputs and native
C4 conditioning saved. target3 was computed and explicitly discarded in the
original compensation preflight. Therefore reconstruct target3 from cached
inputs with three native updates, then execute the fourth ONLY to verify
bitwise equality with archived target4 and both archived S1 outputs. This is
additional model computation for a diagnostic, NOT a new teacher-label dataset
or a speed method. NoESM/MSApreparation/inputencoder/newsequence/RCSB. Native
MSA execution remains part of recycle. Fail closed on any replay mismatch.

Before: carried candidate prefix is WT3 for disabled and ALL four LoRA models.
Thus predicted pre-recycle delta is exactlyzero, including after training.
Compare it with target3-WT3, retaining teacher raw/common/AA-centered energies;
NMSE=1 and undefined zero-vector cosine are expected algebraic controls.
Candidate-specific initialization/features also enter the recycle; the zero
carried-state delta does NOT mean all candidate inputs are identical.

After: compare predicted s4/z4-WT4 against target4-WT4 for disabled and all four
LoRA endpoints. Separate s/z metrics. For each site, uniformly average19AAs.
Report raw, AA-centered and common-mean target/predicted/error squared norms,
NMSE, energy ratio and cosine, FP64 streaming moments, no rank/scale fitting.
Do not infer AA-response direction from common structure fit. Undefined cosine
for zero prediction remains null, not a favorable or unfavorable numeric score.

Additional correspondence: LoRA increment=(adapted4-disabled4), target residual
=(target4-disabled4), with same raw/common/centered metrics. This asks whether
the learned update points toward the error remaining after native continuation.
Different-depth target3/target4 energies have distinct denominators; do not
interpret their raw difference as amount of missing prefix recovered.

Six workers select only HIP_VISIBLE_DEVICES0..5, deterministic site index%6,
eight sites/152mutants each. Every reconstructed target4 matches archived
conditioning bitwise, and target/disabled/fouradapted S1 coordinates match both
archived noises bitwise. Expected912target and4560disabled/adapted candidate
replays,10944S1 outputs,8208nativecycles acrosssixworkers; nooptimizerupdates.
Frozen weights, LoRA banks andWT3 cache hashes checked. Do not persist dense
full target3 archives; stream summary statistics to avoid duplicatingGBs.

UseTRAIN27sites/15parents, same-parent new-site3sites, new-parent18sites/9parents
separately. Equal-parent summaries; report paired endpoint-minus-disabled and
pairing byseed, no checkpoint selection. Link existing frozen structure/regret/
geometry results; no new decoder quality claims. All panels development.
Latent correspondence is an internal diagnostic, not a deployment gate or
proof of biological effects. Completion does not authorize new training.
