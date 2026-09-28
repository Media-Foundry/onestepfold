# Complete-interface derivative decomposition, v1

Locked before execution, 2026-09-28. Only control_a1_s1 and 8bzn_a1_s1 from
09f0e82b: alpha .001, C4/S1, fixed native graph, noise211, FP32. Use archived
logits, all three original directions and h=.3/.1/.03/.01/.003. No new target,
alpha, training, source-combination experiment, smoothing or optimization.

Cut b comprises s_inputs/s/z and raw ref_pos/ref_charge/ref_mask/ref_element/
ref_atom_name_chars. Downstream rebuilds d_lm/v_lm/pad_info from raw fields and
fixed ref_space_uid. Fixed fields include relp and atom_to_token_idx. Inspect
actual diffusion reads; verify no remaining differentiable feature bypasses the
cut. ESM/restype/profile affect diffusion through conditioning only.

Use archived new-objective coordinate gradient w, held fixed. KL is separate:
report saved direct q derivative, excluded from coordinate-path decomposition.
First replay archived baseline, direct gradients and every saved perturbed X.
Require cut and original forward equivalence, and record max/norm error between
chain VJP and direct q gradient. Abort attribution if cut replay is not exact or
chain relative L2 error exceeds 1e-4 (plus 1e-10 absolute norm).

Report a=w J_F v, m=lambda dot(bplus-bminus)/(2h), d=w dot(Xplus-Xminus)/(2h),
with lambda=grad_b(w dot D(b)). Report all component m values, m-a, d-m, total
and algebraic residual. These are numerical/linearization deviations, not bugs.
Preserve original FD verdicts; this is localization, not a new pass gate.

Save b0/lambda and exact FP64 bplus-bminus tensors per row remotely, coordinate
pairs, source/input hashes and separate CPU FP64 projection replay. Full boundary
arrays may remain on DiamondHill; bind their hashes in the compact local audit.
No use of native geometry gate as a prerequisite. Keep prior absolute and
nonregression geometry records unchanged.

Only after the cut identifies a segment: use a small local precision/JVP
reference, not whole-model FP64. A cheap analytic p=softmax(q), E=pW reference
may then compare actual q/weights in FP32/FP64 plus true torch.func.jvp and
reverse VJP, with same directions/h. This is not a new folding run.
