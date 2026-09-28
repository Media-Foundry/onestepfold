# C4/S5 collision control — 2026-09-29

User requested an original C4/S5 comparison. Bounded parent-only diagnostic:
control sequence194, the same Mini-ESM checkpoint/ESM2 conditioner, no MSA/template,
FP32, K1, seeds211/200003/200009. No mutations, training or repaired inputs.

Compare (a) archived controlled C4/S1, with exact coordinate replay guard;
(b) controlled C4/S5: same identity-key initial noise, dropout off, identity
rotations, gamma0=0, lambda=1, eta=1, same stable Euler arithmetic, schedule only
changes to5steps; (c) original native C4/S5 prediction through runner.predict,
with its resolved sampler, stochastic augmentation and MC-dropout settings.
Report actual configuration, schedule and executed call counts. Native vs controlled
is a whole-inference-rule comparison, not an isolated step-count intervention;
identical seed labels do not mean matched native initial noise.

Three seeds × two new S5 arms =6 predictions, plus3 S1 replay checks. Common native
chemical topology/atom identities and old geometry thresholds, raw outputs only.
Record named severe pairs, backbone/sidechain category, graph distance and
max penetration; task score is descriptive, not a design success endpoint.
CPU recompute all9 outputs. No best-of-seed or threshold adjustment.

Stop after this batch. If implementation fails, preserve evidence and avoid
expanding numerical/method searches tonight. Main repair batch remains separate.
