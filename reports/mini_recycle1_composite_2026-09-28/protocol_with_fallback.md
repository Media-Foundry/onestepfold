# Recycle1 reuse, full VJP comparison, original-logits composition v1

Locked 2026-09-28 before execution. Same control alpha.001/C4/S1, original three
q directions and original five h. No new target/alpha/optimization/training or
production precision changes. Preserve old initialization selection and results.

A. Recycle1 is explicitly selected (stage index1), no selection rerun and no
ESM/whole trajectory recapture. Reuse stored coarse_baseline states/adjoints and
15 actual positive/negative extended endpoints from mini_pairformer_precision.
MSA1block+PF16blocks+no template; carry all original reused inputs. Native32,
reference32,reference64; same frozen values, masks, precision audit, trueJVP and
three-term secant decomposition as previous stage. Unsupported ops remain visible.

B. Offline CPU comparison of complete stored native32/reference64 VJPs for ESM
25–36 and input initialization, then recycle1. Report total and per-field norms,
absolute L2/max error, relative L2 where reference nonzero, cosine where defined.
Reference norm<1e-10 is only a display annotation, not an acceptance rule. For
initialization subtract known direct dictionary passthrough mu on EARLY_NAMES;
for recycle subtract mu on all carried fields except updated s/z. ESM residual
architecture is not treated as an explicitly isolated dictionary identity path.
These are fixed-output-cotangent VJPs, not the entire Jacobian.

C. After A, original-q derivative composition: start with each archived v_q,
use true torch.func.jvp, never intermediate secants as tangents. Native full
q→liveESM/ERC→C4→S1→X JVP/VJP with archived coordinate projection w; report direct
KL term separately if used (coordinate diagnostic excludes it). Disable only
checkpoint wrappers for JVP and verify primal against native/archive. Fixed
chemical graph/noise211/layout; do not argmax-rebuild during probes.
Then propagate true tangents through complete early interface, initialization,
recycles1–4 and complete diffusion interface, checking each primal against native
FP32 archived states and projected tangent against its VJP. This is an FP32
native-trajectory composition, not a full FP64 model reference. Any later FP64
local-derivative composition at fixed native states must be labelled separately.
Retain per-boundary deviations/unsupported forward AD to localize unexplained
mismatch. Use original5%+1e-6 as a reported consistency criterion, not a new
finite-difference pass nor a global Jacobian/optimization/deployment certificate.

## Bounded operator-coverage fallback (locked after native attempt)

The native original-q attempt completed: all early/init/recycle primals replayed;
forward AD stopped at diffusion's efficient SDPA (unsupported). Preserve this run.
Reuse its three saved recycle4 true tangents and the archived complete diffusion
baseline. Only diffusion is replayed under torch.nn.attention.sdpa_kernel(MATH).
Compare native versus reference FP32 primal and complete input VJP (same w), then
true JVP/VJP and original-q projected response for three tangents. Record backend
changes explicitly; this is a mixed-backend composition, not native end-to-end
forward AD certification or FP64 reference. No new trajectory or q directions.
