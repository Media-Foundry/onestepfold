# Matched-depth WT prefix reuse — terminal findings, 2026-10-06

**Closed, no promotion.** WT2→Target2 improves average structural fidelity and
reduces new geometry failures compared with cold C2, but does not improve mean
candidate ranking or cross-noise selection risk. WT3→Target1 also fails to retain
C4 quality. Keep C4 default; stop these two fixed prefix-reuse configurations
without automatic WT1/WT4, mixing, adapter or further training searches.

Execution code/launch: `ffb2fec5`; [locked protocol](mini_prefix_reuse_v1.md),
[launch and initial integrity stop](mini_prefix_reuse_status_2026-10-06.md).
Corrected root `prefix_reuse_v1b_20261006` completed in785.189s (13.09 minutes),
starting08:51:11UTC and ending about09:04:16UTC /17:04:16HKT. Every stage exited
zero. This elapsed time excludes the previously preserved80.025s initial integrity
stop, which occurred before screening and prompted exact RNG restoration.

## Integrity and input boundary

All18 WT/target gate inputs passed unsplit-versus-wrapper C4 and36 split2/3
continuations bitwise, including final RNG state. Native MSAModule advances RNG
in eval; its state is captured and restored explicitly. No native kernel, model
weight or chemistry is changed. All2,772 cold C4 coordinate replays and36 source
WT replays match the earlier archive bitwise. Terminal audit counted2,763
conditioning calls,6,246 recycle iterations,11,052 S1 calls,11,088 logical output
checks (shared WT outputs appear in both warm ledgers),432 selection checks and
zero optimizer updates. Shared source tensors were checked for mutation.

Nine parents: eight previously observed DEV proteins (32 sites) plus2V66 stress
(four sites),19non-WT candidates per site, four fixed noises. Every target uses
fresh native features, live ESM and its own chemistry. Warm arms use only WT
cycle2/3 token s/z and saved execution RNG; their own remaining native bridge
updates produce complete s_inputs/s/z for diffusion. No oracle target s is used.
True target prefixes occur only in the integrity gate, never in method outputs.

These are development panels, not independent confirmation. The task is the
parent-reference Cα-distance proxy, not biological mutation utility. Structure
fidelity is to same-noise C4 model output, not experimental mutant ground truth.
Current geometry checks do not establish comprehensive chemical correctness.

## DEV selection and recorded cost

Spearman/Top1 use four-noise mean scores across19 non-WT candidates; aggregate
means are protein based. Cross-noise regret chooses once under the arm's two old
noises and evaluates that candidate using the two new C4 noises. C4's own
old-noise choice has nonzero regret. Timing ratios are paired per-parent geometric
means, **with the first-source timing limitation below**.

| Path | Spearman | Top1 /32 | Cross-noise regret | Excess over C4 old choice | Recorded time /C4 |
|---|---:|---:|---:|---:|---:|
| Cold C2 | 0.574671 | 12 | 0.165709 | 0.119871 | 0.736132 |
| Cold C4 | 1.000000 | 32 | 0.045838 | 0 | 1.000000 |
| WT2→Target2 | 0.559265 | 14 | 0.223963 | 0.178125 | 0.855783 |
| WT3→Target1 | 0.436623 | 8 | 0.267797 | 0.221959 | 0.724970 |

WT2 improves Top1 count over C2, but worsens mean Spearman and raw regret. Its
protein regret median is0.036157 versus C2's0.024228; WT3's is0.119450. The worst
protein is4LR3 for both warm paths (mean regret1.270991/1.215416). Both select
T4L there, producing new-noise regret3.859324; the teacher old/new choice is F.
Per-protein responses differ: WT2 notably improves3QR7 ranking (.584649 versus
C2 .067105), while1C5E drops (.179386 versus .691667). These favorable and
unfavorable observations are retained, without post-hoc method selection.

## DEV structures and geometry

Each path has2,432 mutant/noise outputs, clustered within eight proteins.

| Metric | Cold C2 | Cold C4 | WT2→Target2 | WT3→Target1 |
|---|---:|---:|---:|---:|
| AA-lDDT to C4, protein mean | .923195 | 1 | .958695 | .949840 |
| Cα-lDDT to C4, protein mean | .936743 | 1 | .964187 | .956437 |
| Aligned Cα RMSD, mean Å | 1.536677 | ~0 | 1.072726 | 1.274793 |
| Local RMSD in global frame, mean Å | 1.459478 | ~0 | 1.084961 | 1.224473 |
| Local RMSD P95 Å | 6.493751 | ~0 | 4.732969 | 4.538464 |
| Local RMSD P99 Å | 11.060055 | ~0 | 11.400103 | 14.381879 |
| Local RMSD max Å | 18.697358 | ~0 | 24.783986 | 24.845132 |
| Local >1Å count | 768 | 0 | 604 | 715 |
| Absolute geometry pass /2,432 | 988 | 1,028 | 1,001 | 970 |
| C4 pass→method fail | 337 | 0 | 167 | 206 |
| C4 fail→method pass | 297 | 0 | 140 | 148 |
| Selected candidate passes both new noises /32 | 12 | 8 | 8 | 9 |

Warm prefixes contain useful structural information: averages, P95 and new-failure
counts improve relative to C2. This is not uniform improvement: local P99 and
maximum displacement worsen. Both warm maxima involve4LR3 T4W/noise230201
(24.783986/24.845132Å). WT3 also has5OI7 T80R/noise230211 at24.673964Å.
Global aligned Cα maxima are33.723032/34.027406Å for WT2/WT3.

C4 passes only1,028/2,432 of these operational geometry checks. Neither restoring
C4 nor matching its choices would certify chemical validity. Transition counts,
absolute pass counts and structural displacement answer different questions.
The warm WT baselines are the bitwise C4 WT output, so their WT GT metrics equal
C4 by construction; this does not establish mutant experimental accuracy.

## Separate 2V66 stress result

| Path | Spearman | Top1 /4 | Cross-noise regret | Local >1Å /304 | Maximum local Å | Geometry pass /304 |
|---|---:|---:|---:|---:|---:|---:|
| Cold C2 | .842105 | 2 | .474544 | 227 | 12.989660 | 4 |
| Cold C4 | 1 | 4 | .092300 | 0 | ~0 | 10 |
| WT2→Target2 | .941228 | 3 | 1.208368 | 116 | 23.691727 | 3 |
| WT3→Target1 | .850000 | 3 | 1.208368 | 148 | 24.083043 | 2 |

The high WT2 Spearman and3/4 Top1 do not protect against expensive selection
errors. Both warm methods select T75A; new-noise regret at that site is4.833472,
versus C4 old-choice regret.369201. The other three warm old-noise choices have
zero new-noise regret. New geometry failures are8/9, repairs1/1, and all methods
have zero selected candidates passing both new-noise checks. Do not pool this
single stress protein into the eight-protein DEV mean.

## Timing accounting and important limitation

Each path's ledger covers77 sequences per parent (one WT and76 mutants), four
noises, native features, device preparation, live ESM, trunk, decoder/host
transfer, task/geometry screening and coordinate NPZ writes. Both warm ledgers
pay the complete once-per-parent source WT cost, including capture/read/clone
work; source cost is not omitted. Model loading and integrity/offline auditing
are separate. No confidence/CIF service runs. Four workers share CPU/storage.

| Mean seconds /DEV parent | Cold C2 | Cold C4 | WT2→Target2 | WT3→Target1 |
|---|---:|---:|---:|---:|
| Recorded resident workload | 42.389 | 57.670 | 51.005 | 43.468 |
| Native features | 7.645 | 7.641 | 11.168 | 11.193 |
| ESM | 3.350 | 3.349 | 4.039 | 4.039 |
| Trunk | 16.005 | 31.322 | 16.716 | 9.181 |
| Decode + host transfer | 11.611 | 11.601 | 15.122 | 15.128 |
| Screening | 3.208 | 3.187 | 3.208 | 3.174 |
| Add model-load estimate | 90.600 | 105.881 | 99.216 | 91.679 |

**The source WT always executes first in each worker.** Its first total is
17.499/18.109/18.056/17.265s; subsequent parent source totals are about.609–.661s.
The first-source native feature stage takes6.95–7.47s and decode takes7.11–7.24s.
Only warm ledgers inherit these first-call costs, while cold references run
afterward. Rotating the24 candidate arm orders does not balance this source-first
asymmetry. The precise causes of each first-call overhead were not isolated.

Accordingly, preserve these as **as-executed workload ledgers**, not a fully
balanced steady-state benchmark or a causal demonstration that warm2 intrinsically
costs more than cold2. Do not silently subtract the startup penalty or replace the
registered primary numbers with a favorable estimate. A controlled startup/warmup
benchmark would be necessary before any deployment speed claim; quality already
precludes promotion, so this batch does not launch that extra benchmark.
The previous batch's C2 ratio.797816 is not interchangeable with this batch's
.736132 despite identical quality: order/workload/system effects matter.

Stored cycle2+3 s/z totals are8.2–28.0MB per parent (two FP32 states). Worker peak
allocation is12.41–12.50GB and includes diagnostic guard copies. Exact RNG capture
and cache-integrity audit costs are visible; this is not a minimal-memory service
implementation. Detailed stages, WT source costs and per-parent paired timings
are retained in the machine records.

## Decision and retained evidence

This is evidence for structural benefit from WT prefix initialization, but not
for reliable hard-mutant selection or C4 substitution. It does not prove that all
compute reuse or learned corrections are impossible. Close the two tested paths;
no automatic additional prefixes, mixing or training. C4 remains the reference.

[Terminal artifacts](../reports/mini_prefix_reuse_2026-10-06/final/) contain full
compressed report/worker records, selections, timing and WT GT tables, summary,
terminal execution/status, independent audit and SHA256 inventory. Initial gate
stop and passed corrected gate remain in the parent directory. Runtime coordinates
remain at DiamondHill's `.../Folding/prefix_reuse_v1b_20261006`; local metadata is
`/home/husrcf/Code/onestepfold_runtime/prefix_reuse_v1b_20261006`. No execution or
scoring code changes were made during terminal collection.
