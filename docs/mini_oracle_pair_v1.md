# Mini fixed-single / oracle-pair feasibility diagnostic v1

Locked 2026-10-09 before decoder results. Same48sites/24parents/912hardmutants,
19AA/site, Mini v0.5.0 FP32, cached actual candidate s_inputs/features/chemistry,
WT3+RNG, native candidate last recycle and frozen S1. No training, new sequence,
new teacher labels, ESM/MSA preparation, input encoder or target C4 recomputation.
Native MSA execution remains inside the one candidate recycle.

Three fixed conditions, no LoRA:
- disabled B: actual candidate's unadapted last-recycle conditioning, untouched.
- oracle_pair: (B_inputs,B_s,target_C4_z), original target_z, no residual algebra.
- exact: archived complete target conditioning, replay integrity reference only.

Actual candidate B_inputs must equal archived target_inputs bitwise. Oracle
construction uses only target_z, never target_s; exact reference is isolated.
All conditions use actual candidate chemistry/atom inventory and two archived
noises230201/230211. No additional scaled/mixed/centered/oracle-s arm. Every
exact and disabled coordinate must reproduce its archived counterpart bitwise.
Use existing pair_split_conditioning(...,mode='pair'), which returns original
B_inputs/B_s and the supplied pair tensor. No mutation of reference caches.

This is an oracle feasibility control, NOT deployable inference or evidence
of predicting target_z. Target_z costs are hidden only because already archived;
no speed claim. Nor is its decoder score a strict mathematical upper bound:
other z with fixed B_s could decode differently, and target_z may be mismatched
to B_s. Failure challenges simply restoring native z, not all possible pair-only
models or WT information sufficiency. Success does not prove residual learnability.

Six workers use only HIP_VISIBLE_DEVICES0..5 and deterministic siteindex%6.
First site's exact/disabled replay gates remaining workers. Expected912native
last recycles,5472S1 outputs,zero updates/C4 interface/input encoder. Frozen
model andWT3 hashes checked; candidate endpoint conditioning hashes retained.
Coordinates/manifest SHA stored.45minute bounded controller, fail closed.

Same coordinate-only scorer/geometry thresholds/parent-reference backbone
proxy as previous split audit. SplitTRAIN27sites/15parents, same-parent new3sites,
new-parent18sites/9parents. Report equal-parent same-noise and two-noise mean
Spearman,Top1,scoreMAE,old230201 selection evaluated against exact230211 regret,
exact self cross-noise regret, centered AA-distance responseRMSE, all-atom/CA
fidelity, localP95/P99/max/>1A, absolute geometry and pass→fail/fail→pass versus
exact and disabled, severe collisions/wrong chirality including already-failed
outputs. Preserve continuous chirality and failure identities.2EBEA30,E47 and
previous tail cases remain included, not a tuning target.

Fixed oracle_pair-minus-disabled and oracle_pair-minus-exact paired-parent
bootstrap10000draws seed275001, descriptive95% intervals. No result selection,
no numerical threshold invented after outcomes. A large recovery across response,
selection and tails supports testing pair recovery; persisting selection/geometry
failures limit that hypothesis even if average fidelity is high. All panels
already used for development. No independent confirmation or automatic training.
