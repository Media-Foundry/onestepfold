# Recipe × LR comparison: terminal TRAIN evaluation

2026-09-30. Registered while the three training arms are running, before their
terminal predictions. Implements the frozen `mini_diffusion_recipe_scale_v1.md`.
No checkpoint selection, additional targets, validation inference or gate changes.

Require all three training reports and independent history/optimizer audit complete:
512 updates, 2048 exposures, original 1613 base parameter tensors unchanged, zero
adapter initialization exactly equal to the archived old_low control. Check original
TRAIN128 identities/order/noises; no terminal checkpoint initializes another arm.

Evaluate all 128 TRAIN proteins at both original seeds600001/600011. Models:
native_s1, native_s2, old_low (archived gt_s2), old_high, calibrated_low,
calibrated_high. Reuse native and old_low coordinates only after checking their
archived hashes and provenance. Three new students give768 new predictions;
complete inventory1536. Eight GCD workers, target-level length-squared assignment.
Each worker checks native/zero-adapter parity plus loaded/merged parity for all
three new adapters:10 probe NFEs per worker,80 total. Actual student NFE=1.
No geometry repair, relaxation or altered inference precision/backend.

Use the unchanged shared observed-GT/full-inventory chemistry scorer. Bind mapping,
chemical packet and experimental atom37 source hashes; masks apply before GT
arithmetic. Independently recalculate AA/CA lDDT using dense blocked distances.
Report typed connection residuals, GT branch mismatches, worst atom pairs and
strict checked stereochemistry without introducing a new aggregate pass flag.
Errors stay in the128-protein denominator; incomplete scoring prevents a summary.

Average the two fixed noises within each protein before quality summaries or paired
contrasts. Report nativeS2−S1, each student−S1, and the four factorial contrasts:
old_high−old_low, calibrated_high−calibrated_low, calibrated_low−old_low,
calibrated_high−old_high. Interaction is
(calibrated_high−calibrated_low)−(old_high−old_low). Keep its sign.
Use10000 protein bootstrap draws, seed20260930, for descriptive95% intervals;
these condition on the fixed noises and are not multiplicity-adjusted. No formal
claim of generalization follows from TRAIN fitting.

Quality includes AA/CA means, paired tails and severe drops; CA RMSD worst-tail uses
the largest values. Chemistry includes new clashes on previously zero-clash inputs,
lost strict chirality, total severe pairs, observed-GT bonds, branch mismatch and
connection distributions. Retain per-protein and per-noise details, including length.
Report merged weight change, actual coordinate displacement, update clipping and
per-component learning curves. Different objectives' scalar losses are not directly
comparable. Cached-conditioning diffusion timings are not end-to-end latency.

No result can justify automatically escalating LR, extending epochs or reusing the
revealed validation32 for selection. Useful quality/chemistry progress would justify
preselecting a new isolated confirmation panel; absent that, reassess this bounded
comparison. Lower training clash weights never waive chemical evaluation.
