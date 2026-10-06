# Base model-only delta propagation — 2026-10-06

The bounded audit is **complete**. It finds a clear early low-energy-rank
window, followed by much higher spatial rank later in the native trunk. It does
not establish an exact multi-mutant accelerator or a useful speedup. Optimizing
only the earliest triangle update would affect a very small portion of C4.

[Locked protocol](base_delta_propagation_v1.md),
[artifacts](../reports/base_delta_propagation_2026-10-06/), and
[stage statistics](../reports/base_delta_propagation_2026-10-06/stage_summary.csv).

## Scope and integrity

User explicitly narrowed this cycle to the folding model, excluding MSA/ESM
preparation and pipeline costs. Official **protenix_base_default_v0.5.0**,
368,088,191 checkpoint tensor elements, FP32 native torch execution; four full
recycles with48 main Pairformer blocks per cycle. No ESM, template, MSA search,
diffusion, confidence, optimizer updates, kernel replacement, student or repair.
The internal native MSA modules remain active. Input packets have a single
dummy/query MSA row, with native candidate-specific chemistry and profile.
This C4/query-only diagnostic is **not** Base's default C10/200-step quality
configuration and does not establish behavior under rich homologous MSAs.

Three preselected development sites:5OI7 A50/L88,2V66 T75/L111,4LR3 T4/L164.
WT plus19 replacements per site:60 inputs,57 non-WT responses. Every input
has two plain C4 executions and one observed execution from matching RNG;
each WT also repeats observation and receives a separate event-timing pass.
One excluded warmup gives187 C4 calls/748 recycle updates/zero S1.
Final s_inputs/s/z whole-byte hashes match plain versus observed execution for
all60 inputs; repeated plain executions and final execution RNG also match.
WT internal observation points reproduce with exact numeric equality.

Worker436.571s (~7.28min); model loading44.136s and preparation13.114s separately
recorded. Device guard verified HIP0→PCI0000:32:00.0. Source freeze1,086 files,
60 input hashes, four installed model source hashes and checkpoint SHA verified.
Six focused tests passed. Independent CPU Gram-eigenvalue analysis reproduces
energy fractions for18,240 sampled spectra across all57 mutations. Independent
verification of full-tensor equality uses stored full-byte hashes; internal
whole-tensor equality fractions remain worker observations, not a second full
model execution by the independent audit.

## Strict equality and physical magnitude tell different stories

All57 first MSA TriMul A operands have some differences outside the mutation
row/column. Thus none qualifies as a literal bitwise row/column-only delta.
However, a post-hoc analysis of the already archived eight channels shows:

| Observation | Mean energy outside mutation row/column |
|---|---:|
| Additive z_init reconstruction | 3.04e-12 |
| First MSA TriMul gated A | 8.60e-12 |
| First MSA TriMul output | 0.00959 |
| Main block8 output, cycle1 | 0.08877 |
| Final z | 0.66791 |

Outside-row/column absolute differences reach4.29e-5 at initialization and
4.03e-5 in first gated A. Their tiny relative energy is consistent with an
almost row/column-local early response, but this audit does not causally
separate floating-point/layout effects from every feature dependency. They
cannot simply be called biological long-range response or rounded away under
a bitwise-exact claim. The additional nonlocal-energy analysis was performed
after the planned runs, uses no new forward passes, and is labeled post-hoc.

The average unchanged16x16 whole-channel tile fraction is15.27% before the
first MSA outgoing multiplication. It becomes zero at that multiplication's
output and stays zero at the later measured pair points. Zero unchanged tiles
does **not** imply an unstructured or high-energy-rank delta. Equally, a few
equal elements do not certify a reusable subexpression outside this panel.

## Early low rank survives more than the initialization

Spectra use eight fixed channels0,16,...,112, FP64 arithmetic on observed FP32
deltas. Statistics below average57 candidates ×8 channels; this is three
contexts, not456 independent proteins. R95/R99 are energy thresholds, not exact
algebraic ranks. No unmeasured channel guarantee is implied.

| Native point | Mean R95 | Mean R99 | Mean R32 energy |
|---|---:|---:|---:|
| z_init additive reconstruction | 1.74 | 1.89 | ~100% |
| First MSA TriMul, after input normalization | 1.96 | 2.00 | ~100% |
| First MSA TriMul gated A | 1.80 | 1.99 | ~100% |
| First MSA TriMul output | 2.00 | 2.82 | 99.976% |
| First-cycle MSA output | 2.01 | 2.83 | 99.980% |
| First main TriMul gated A | 2.04 | 3.25 | 99.971% |
| Main block1, cycle1 | 2.04 | 3.15 | 99.976% |
| Main block4, cycle1 | 2.37 | 5.34 | 99.956% |
| Main block8, cycle1 | 2.99 | 8.20 | 99.929% |
| Main block48, cycle1 | 40.87 | 67.01 | 91.643% |
| MSA input, cycle4 | 42.12 | 69.20 | 90.527% |
| Final z | 44.24 | 71.07 | 89.750% |

Initialization's observed rank2 energy is1−8.18e-13 on average, consistent with
the additive u_j+v_k construction up to floating-point residuals. First gated A
still has rank2 energy1−1.45e-11 on average. This positive observation is stronger
than merely finding a low-rank z_init: it reaches actual contraction operands.
It is empirical support, not a theorem that normalization/gating preserves rank.

By block8, R8 retains98.927% mean energy, but R2 only92.270%. Between the measured
block8 and block48, rank increases substantially. The audit does not locate an
exact transition block: intermediate blocks9–47 were not individually captured.
Cycle4 begins with a high-rank recycled response; the early cycle1 pattern
cannot be assumed to restart independently on every recycle.

Final-state variation across parents is substantial:

| Parent | Final mean R95 | Final mean R32 energy |
|---|---:|---:|
| 5OI7 | 26.96 | 96.07% |
| 2V66 | 44.50 | 89.37% |
| 4LR3 | 61.26 | 83.81% |

The lowest single sampled final-channel R32 energy is75.95%. There was no
decoder/geometry/ranking intervention here. These energies cannot be described
as functional fidelity or imported into earlier Mini R32 quality claims.

## Model-only cost, with an instrumentation caveat

Prepared device inputs are the timer boundary; input embedding and full native
trunk are included. External preprocessing, transfer, loading, snapshots and
offline decomposition are excluded. Two plain repeats per candidate are
descriptive, not a robust production throughput benchmark.

| Parent | Mean candidate C4 time | First MSA TriMul event time |
|---|---:|---:|
| 5OI7 | 0.9559s | 0.780ms |
| 2V66 | 0.9797s | 0.868ms |
| 4LR3 | 1.6438s | 1.516ms |

The first TriMul is only roughly0.08–0.09% of plain C4 time by these separate
measurements. CUDA-event hooks themselves perturb execution: inclusive module
sums can exceed plain wall time. Those percentages are scale comparisons, not
an exact additive speedup bound. The five measured pair operators in the first
eight main blocks of cycle1 total30.70/32.71/56.17ms in the separate event pass;
this excludes single updates and is not the cost of an implemented delta path.
Main-stack inclusive event totals dominate MSA-module totals. Do not add
inclusive parents and their nested operator times.

No factor generation, recompression, factor-to-dense materialization, fused
delta kernel, multi-candidate batching, HBM traffic or occupancy experiment was
performed. CPU SVD costs describe this diagnostic only; they are not a proposed
GPU execution cost. Maximum recorded model-pass allocation was1.924GB under
this serial short-chain protocol, not a20-way batch memory measurement.

## Decision

Close this audit without changing the native model. The result supports an
**early structured-delta window**, not persistent strict sparse reuse or a full
C4 low-rank engine. It also shows that optimizing only the first contraction
is unlikely to materially accelerate this measured workload.

If a further prototype is authorized, it should test real early gated operands,
include compression/materialization cost, retain a dense fallback and prove
numerical fidelity separately. The unmeasured block8→48 transition and later
recycles are material limitations. No kernel or additional batch is launched
automatically; no ESM/MSA-preparation optimization belongs to this result.

Full report/sampled snapshots/input packets remain at:
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/base_delta_propagation_v1_20261006`.
Local full metadata: `/home/husrcf/Code/onestepfold_runtime/base_delta_propagation_v1_20261006`.
Git contains the compact report (spectra summaries, full hashes), independent
checks and locked protocol; full singular spectra remain in the runtime report.
