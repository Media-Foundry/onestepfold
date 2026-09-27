# Mini backward gate v1

2026-09-28. Preserve Mini-ESM v0.5.0, C4, K1. No training or recycle compression.

The first implemented probe differentiates coordinates with respect to cached ESM
feature values on a fixed chemical graph. It is explicitly a partial conditioning
derivative, not a soft-sequence or binder-design acceptance test.

`src/fastglycan/models/differentiable_mini.py` contains an explicit adaptation of
the archived upstream Pairformer method with only the recycle gradient guard
changed. Eval mode disables dropout, weights remain frozen, all four cycles retain
input derivatives. A deterministic S1/S2 Euler path takes an explicit initial
coordinate tensor, centers at each step, and uses native schedules with gamma0=0
and eta=1. It keeps native final-step arithmetic rather than replacing it with a
denoiser return. Cached diffusion conditioning is recomputed with gradients.

The shortest existing diagnostic target is used for implementation validation.
The runner must first reproduce original controlled FP32 S1 coordinates within
1e-3 Angstrom maximum component error. Failure stops the backward probe. Then a
rotation/translation invariant distance objective tests ESM feature gradients,
repeatability, central differences over four h values and S1/S2 gradient cosine.
This artificial objective is a graph diagnostic only; decrease is not evidence of
design utility. Finite-difference errors are reported, not silently called passes.

Two CPU tests pass: AST comparison against archived upstream (only gradient guard
changed), and a finite-difference test that detects a deliberately detached
recurrent path. GPU verification is separate and required.

DiamondHill run root:
`/media/PM982/onestepfold/mini_backward_gate_v1_20260928`
One GCD0 probe, PID1669820, bounded1200seconds, immutable code snapshot `code/`.
Check `probe.log` and `short_probe/report.json`; launch is not acceptance.

Next gates: validate residue/atom feature relaxation, differentiable ESM token
embeddings, hard-input equivalence and full-sequence directional derivatives.
Cached ESM and unchanged chemical identities cannot establish those gates.
Only after those pass run soft-logit optimization, hard sequence rebuilding and
independent-noise validation. Keep all existing diagnostic targets out of training.

Initial probe stopped before backward because the native runner removes feature
keys in place. V2 copies the prepared feature dictionary at entry; original failed
artifacts retained. Active snapshot code_v2, PID1670561, probe_v2.log and
short_probe_v2/report.json.
