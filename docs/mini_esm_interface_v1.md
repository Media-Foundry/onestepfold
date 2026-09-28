# ESM-output interface localization v1

Frozen 2026-09-28 before execution. Only control_a1_s1, alpha .001, original
three logits directions and h=.3/.1/.03/.01/.003, fixed native chemical graph,
C4/S1/noise211/FP32. No optimization/training/new alpha/target or geometry gate.

Reuse the archived diffusion-interface VJP lambda_b, fixed coordinate projection
w, q/directions and all 15 previous late-interface secants. Add early interface
c=(esm_token_embedding,restype, five raw reference chemistry fields). profile
is tied to restype in the actual chart and must be reconstructed as the same
tensor, not an extra independently counted path. Rebuild d_lm/v_lm/pad_info.
Keep the ordinary full four-cycle Pairformer and packed late conditioning.

Compute mu=J_H(c0)^T lambda_b, where H maps the complete early interface to
complete diffusion interface b. Check exact cut forward equality and exact
archived b0, and chain q gradient relative L2 error <=1e-4 plus absolute1e-10.
Record any deviation from previous end-to-end AD, do not replace old FD results.
Check every q-dependent feature read belongs to the cut or its rebuilt aliases.

For each original q±hv, recompute live ESM, chemistry and H. Require late delta
bitwise equal to previous stored FP64 bplus-bminus. Then report:
a=AD; n=mu dot(cplus-cminus)/2h; m=lambda_b dot(bplus-bminus)/2h; d=old w dot ΔX/2h.
Decompose d-a=(n-a)+(m-n)+(d-m). These are numerical/linearization deviations.
Report ESM and R/C contributions individually without calling them independent
causal mechanisms. Save c0/mu and exact early delta tensors; independently replay
CPU FP64 projections and the telescoping identity. No whole-model FP64 this round.

If the main gap lies in H, a future bounded cut can examine input encoding and
recycles, retaining all skip paths. If it lies before c, future localization can
examine ESM input/Transformer. Do not claim an operator bug from this split.
