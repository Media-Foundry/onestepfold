# Mini reference editor: candidate correspondence intervention v1

Locked follow-up to d2da9617. No training or promotion; previous study stays closed.
Question: does workspace mean regret improvement on the common held development
panel require correctly matched AA-specific predicted conditioning?

## Fixed panel and checkpoints

All four terminal workspace checkpoints: n3/n15 × seeds272001/272003, steps3040/
16416. No direct-control arm, intermediate selection, seed exclusion or tuning.
Use exactly the common9 held proteins/18 sites/342non-WT candidates from the
multiref plan; each has noises230201/230211. No added teacher or preprocessing.
No training sites mixed into the held metric. Both noises/panel are historical
development, not independent confirmation. 6ZRW included;6UFE92 unavailable.

## Three interventions

Let C_a=(s_inputs,s,z) be the original student output, C0 the archived WT memory,
mu=mean_19(C_a-C0), r_a=C_a-C0-mu. Use all three blocks together:

- Correct: C_a, original student. Do not numerically reconstruct mu+r_a.
- Common: C0+mu, identical token conditioning for all candidates at that site.
- Shuffled: C0+mu+r_pi(a)=C_pi(a), taken directly from original student tensors.

All arms decode with the actual receiver candidate's chemistry/atom inventory,
reference atom positions and identity-mapped noise. The donor supplies ONLY token
conditioning. No teacher target conditioning enters predictions or their mean.
Common is computed from CPU FP64 differences and reduced once, then cast to native
FP32; this is a conditioning intervention, not an execution optimization.

Exactly one derangement per site: sort the19 candidate AA identities by SHA256
of `mini-editor-intervention-v1|<site_key>|<AA>`, map each to the next in this
hash-ordered cycle. Same mapping across dataset sizes, seeds, noises and blocks.
Save mappings and hashes before any new S1 output. No resampling, scaling, best
permutation or held-label tuning. A single shuffle is a bounded sensitivity test,
not a population estimate over permutations or a proof of biological mechanism.

## Execution integrity

Mini checkpoint/reference encoder/S1 frozen; zero C4/input-encoder calls and zero
optimizer updates. Reuse archived actual-candidate packets. Copy the frozen
independent auditor source and add only this diagnostic. Source lock, plan, code,
checkpoints, old coordinate manifests and prepared packet hashes validated.
Keep the previous archive read-only; a new root owns logs and coordinates.
All684 correct outputs per checkpoint MUST match the old terminal coordinates
bitwise (2736 total); stop on any mismatch before interpreting interventions.
Mean/shuffle are never initialized from teacher conditioning. All outputs finite.
Verify source/checkpoint/Mini weight integrity again at finish. Test mean energy
identity, candidate-axis centering, derangement and all-block donor consistency.

Total:4 checkpoints×18sites×19AA×2noises×3arms=8208 S1; zero training.
One run per checkpoint; failed runs retained, no selection/replacement. A2-hour
infrastructure limit is a failure cap, not a scientific early stopping rule.

## Fixed evaluation

Reuse existing exact/reference_only coordinates; they require no new S1. An
independent CPU scorer recomputes every arm with the prior metric definitions.
Primary: equal-parent aggregate19AA Spearman, Top1, raw old-select/new-Exact regret.
Always select using230201 and evaluate that sameAA against230211 Exact. Exact's
own cross-noise regret is a reference, not assumedzero. Also score per-noise ranks,
score MAE, top3/5, centeredCA-distance responseRMSE, AA/CA lDDT, localRMSD P95/P99/
max/>1A, absolute geometry and pass/fail transitions. Retain continuous checked
volumes. Pair comparisons at the protein level, same10000-draw descriptive
bootstrap seed275001 as prior audit; nine proteins are the units, not AA×noise.

Report correct-common, correct-shuffled and each-reference contrasts separately
for both seeds and sizes. Decompose regret differences by protein AND site;
show selected AA and raw score gaps. Save student-only mean/centered conditioning
energy per block to document what is removed. Do not rank-checkpoint-shop.

Correct beating both interventions consistently would support usefulness of its
AA correspondence on this panel; it would not prove full response transfer.
Common retaining gains would support a site-shared component/chemistry interaction
explanation. Mixed results remain mixed. Shuffle deterioration may reflect an
out-of-distribution mismatch, not causal biology. Common requires all19 student
predictions and conveys no speedup. No new distribution calibration, experiment-
structure accuracy claim, fullfolding speedup, or automatic architecture changes.
