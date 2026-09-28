# Recycle 1 precision and original-logits derivative composition

Scope: original control, alpha=0.001, C4/S1, fixed graph and identity-keyed
noise211. No training, new targets or production changes. The protocol is
[mini_recycle1_composite_v1.md](mini_recycle1_composite_v1.md).

## Recycle 1: third local positive consistency result

Reuse the previous actual extended-state endpoints and output VJP, explicitly
selecting recycle1. No automatic reselection or ESM trajectory recapture.
The segment includes one MSA block and sixteen Pairformer blocks, with all
cross-cycle inputs retained.

Primary direction2, h=.003:

| Quantity | Value |
|---|---:|
| Native FP32 secant | +0.0103800025437 |
| Native FP32 AD | +0.00663001286293 |
| Reference FP64 secant | +0.00663001555053 |
| Reference FP64 AD | +0.00663003223623 |
| FP32−FP64 secant difference | +0.00374998699320 |
| FP64 finite-endpoint remainder | −1.66857e−8 |
| FP64−FP32 AD difference | +1.93733e−8 |

All fifteen rows have the forward secant difference as the largest of the three
terms. Maximum FP32/FP64 AD projection relative difference is 1.68174e−5
(0.001682%); maximum FP64 secant/AD relative difference is 4.11581e−5.
FP64 true JVP/VJP maximum relative difference is 5.20508e−15. Native/reference32
primal and AD are identical on tested points. Local chain reconstruction is
exact. The dtype audit records 5,610 double floating outputs and sixteen double
attention calls, with no non-double output observed.

This supports a forward-difference precision limitation at the tested scales,
not a recycle backward defect. It is a fixed-cotangent local result, not an
entire Pairformer Jacobian certificate. Do not reopen per-operator searches here.

## Complete fixed-cotangent VJP vectors

CPU-only comparison from saved baseline tensors:

| Segment | Relative L2 FP32 vs FP64 | After explicit dictionary passthrough subtraction |
|---|---:|---:|
| ESM25–36 | 5.68112e−6 | Not applicable |
| Initialization | 4.60697e−7 | 4.60699e−7 |
| Recycle1 | 2.44416e−6 | 2.44416e−6 |

Per-field norms/errors/cosines are retained in `full_vjp_comparison.json`.
The summary is not solely identity-path agreement. After recycle identity
subtraction, carried E/R/C fields are exactly zero, with undefined relative
error/cosine explicitly represented as null. The small `s_init` residual has
reference norm3.40e−8, relative error0.003249 and maximum absolute error7.24e−12;
this should not be confused with a large influential gradient discrepancy.
`z`, the largest field, has relative L2 error2.44416e−6. This remains one output
cotangent's full VJP, not the entire Jacobian.

## Original logits direction, native FP32 trajectory

The archived three logits directions are propagated using true forward AD.
No intermediate secant replaces a tangent. Native full coordinates and reverse
sequence gradient exactly replay the archives. All six intermediate boundaries
(early E/R/C, initialization, recycles1–4) have exact primal replay for all three
directions. All eighteen projected JVP/VJP comparisons satisfy the original
5%+1e−6 criterion; maximum relative discrepancy is0.00160323 (0.160323%), maximum
absolute discrepancy2.53595e−8. The directional responses are approximately
−1.02070e−4, +4.60714e−5, +1.57924e−5, not zero-signal passes.

Native diffusion's `_scaled_dot_product_efficient_attention` has no forward AD
implementation in this installed PyTorch build. Both full and staged native JVP
attempts retain this unsupported outcome; it is not classified as a backward
failure. The bounded math-SDPA suffix comparison is separately recorded below.

## Diffusion forward-AD coverage fallback and final composition

Only the saved diffusion interface and three true recycle4 tangents were reused.
The separate FP32 math-SDPA reference supports forward AD. Its primal is **not**
bitwise native: coordinate maximum absolute difference7.08103e−5Å, full-coordinate
relative L2 difference9.60172e−7. Complete input VJP relative L2 difference is
5.86744e−6 (per-field results retained). This backend difference is measured,
not attributed exclusively to dtype; both paths use FP32.

| Original logits direction | Native end-to-end VJP | Composed JVP, math-SDPA suffix | Relative difference |
|---|---:|---:|---:|
| 0 | −1.020700044e−4 | −1.020887439e−4 | 0.01836% |
| 1 | +4.607144478e−5 | +4.606924409e−5 | 0.004777% |
| 2 | +1.579244433e−5 | +1.581751805e−5 | 0.158519% |

All three satisfy the unchanged reported consistency criterion with nonzero
signals. The reference diffusion's own JVP/VJP maximum relative discrepancy is
1.91061e−6, and native/reference diffusion projected VJP discrepancy is at most
1.58931e−5. Reference JVP primals exactly replay their reference baseline.

This is **native-FP32 upstream true-tangent composition plus an explicitly audited
math-SDPA diffusion suffix**, compared against the native full reverse-mode
sequence gradient. It is neither a full FP64 trajectory nor a successful native
full forward-AD execution. Together with the three local precision interventions,
it gives positive consistency evidence for these original logits directions at
this fixed control point. No unexplained boundary discrepancy exceeds the locked
criterion; no further mechanical segment-by-segment FD scans are warranted.

## Evidence and limits

The recycle run took116.2s and41.25GiB; the original-q run took89.8s and14.77GiB
including setup. These are diagnostic job timings, not production latency.
CPU audit reconstructed fifteen reused coarse rows and fifteen new precision
rows, maximum absolute scalar discrepancy4.34e−18. Original-q CPU audit recomputed21 projections with maximum error9.49e−20;
the suffix audit recomputed3 rows with maximum error5.42e−20.
Focused local tests:15 passed.

GitNexus MCP context was checked for PairformerStages, but its cached index
reported nineteen commits behind; runtime source and archived replay checks,
not that graph, are the evidence for the execution path.

Compact reports: `reports/mini_recycle1_composite_2026-09-28/`.
Full hashed tensor evidence remains at DiamondHill:
`/media/PM982/onestepfold/mini_recycle1_composite_v1_20260928/`.
Original raw FD failures remain recorded. Soft-input distortion, graph switching,
absolute hard geometry and discrete-design utility are separate unresolved
issues; deployment remains rejected. No diffusion/LoRA training is justified
by these numerical findings.
