# ESM frozen-endpoint precision diagnosis v1

Locked 2026-09-28 before computation. Only existing control alpha.001, original
three logits directions and five h, unchanged downstream ESM-output VJP.
No folding/core inference, optimization, training, extra alpha or smaller h.

Read/hash actual imported ESM attention/rotary/modules and PyTorch versions.
Record LayerNorm classes, eps, normalized shape, actual attention path, matmul
flags. Native checkpoint FP32 runtime values are authoritative. Native remains
unchanged. Coarse boundaries: layer0 input, after floor(N/3), floor(2N/3), N,
and final emb_layer_norm_after. Preserve actual u0/uplus/uminus for every boundary,
not midpoint reconstructions. Compute boundary VJPs with fixed archived output
mu and remove hooks before backward. Require baseline/output-delta bitwise replay
against preceding archive and boundary-chain checks.

Predeclared selection: among the three Transformer segments and terminal norm,
choose maximum absolute adjacent-boundary secant difference for original
**direction0,h=.003**. Tie: earliest segment. Selection is diagnostic, not a new
validation sample. Report coarse signed deviations and 2h-scaled numerators.

For selected segment only, use nativeFP32, referenceFP32 and referenceFP64.
Reference copies same FP32 weights, same LayerNorm dimensions/epsilon. Freeze
actual native RoPE cosine/sine tables and lift their values; never regenerate
higher-precision positional constants. Context-scoped attention softmax computes
FP64 for double input and FP32 otherwise. Record actual normalization class;
if fused LayerNorm must be replaced, record and run its referenceFP32 control.
Trace floating operator output dtypes on referenceFP64, reject hidden FP32
computations. Check attention-softmax dtypes and parameter/cache equality.

Use identical frozen u0,uplus,uminus and mu for all precision modes.
v_h=(uplus-uminus)/(2h) is formed in double; native AD projection uses this exact
secant direction and native gradient. Forward-mode JVP takes its representable
input-dtype cast; report direction cast error and compare VJP on that same cast.
Compute S_r=mu dot(f_r(uplus)-f_r(uminus))/(2h), A_r=grad f_r(u0) dot v_h.
S32-A32=(S32-S64)+(S64-A64)+(A64-A32). Store signed terms and numerator forms.
Do not label the high-precision remainder pure curvature; record midpoint offset
and endpoint radii. ReferenceFP32 vs native separates execution-path changes.

Run true torch.func.jvp (no checkpoint wrapper) for each direction/step on both
reference precisions; unsupported operators are explicit results, no fallback
to backward-of-backward. Save gradients, projections and native/reference outputs
for CPU replay. Audit floating dtypes on a reference forward outside JVP so the
observer does not itself interfere with forward AD. No production math changes.
