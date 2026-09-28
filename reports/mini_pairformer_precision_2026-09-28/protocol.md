# Pairformer extended-state frozen-endpoint precision v1

Locked before execution,2026-09-28. Only existing control alpha.001/C4/S1,
original three directions and five h. Primary row:direction2,h=.003. No diffusion
execution, new targets/alphas, optimization, LoRA or production precision changes.

Stages:input encoding+initialization, recycle1,2,3,4. Boundary0 is complete early
interface ESM/restype/five chemistry fields. Later boundaries carry
(s,z,s_init,z_init,s_inputs,complete early interface). profile remains tied to
restype; raw chemistry derivatives are rebuilt. Fixed topology/masks are retained.
Read actual MSA/template configuration and feature reads; no assumption that a
shared per-forward quantity is constant across q±. All actual u0/u+/u− saved.

Compute each boundary cotangent by independently detached local pullbacks from
final complete diffusion-interface VJP. This avoids taking total derivatives
with respect to overlapping ancestor states and double-counting skip paths.
Compare resulting early cotangent to actual original full_recycle_pairformer
pullback and previous archived early VJP; require relativeL2<=1e-4+absolute1e-10.
Require exact staged/native/archived final baseline and archived final secants.
Do not interpret failures of these guards as scientific precision findings.

Choose stage with maximum absolute adjacent-boundary deviation on the locked
primary row, earliest tie. Initialization is eligible. On selected stage only,
reuse all3directions×5h and frozen actual endpoints, same FP32 weight values and
fixed features. NativeFP32,referenceFP32,referenceFP64. ReferenceFP32 compares
execution-path changes. Reference copies disable checkpoint wrappers for true
JVP while preserving eval arithmetic. Audit actual norm classes/epsilon/kernels.
Patch only independent reference attention to preserve FP64 instead of explicit
FP32 downcast, leaving native32 untouched. Cast fixed floating features exactly;
retain boolean/integer masks. Preserve math definitions and record overrides.
Reject hidden lower-precision floating outputs via dtype audit.

S32-A32=(S32-S64)+(S64-A64)+(A64-A32). Save signed terms and2h numerators,
midpoint shifts, endpoint radii, native/ref outputs and VJPs. v_h is the actual
extended-state secant, not original q direction. True torch.func.jvp/VJP on same
representable direction, unsupported operators explicitly recorded. No substitute
backward-of-backward. CPU independent projection replay. A raw FD failure, a
local precision explanation and the overall deployment verdict remain separate.
