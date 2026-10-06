# Native C4 execution profile — 2026-10-06

The bounded profile is **complete**, with no optimization or model change.
All396 coordinate outputs from99 complete C4 workloads replayed the archived
reference bitwise, including instrumented runs. All four operator traces contain
GPU events. This provides execution-cost and dependency evidence, not a new
accelerator or speedup claim.

[Protocol](mini_execution_profile_v1.md) and
[dependency/invalidation audit](mini_execution_dependency_audit_2026-10-06.md).
Source freezes1,082 files, including1,074 unchanged prior native-batch files.
Controller started10:06:57UTC /18:06:57HKT, completed in228.109s (3.80min);
inner script including loading/audit took218.019s. No failed run or retry.

## Panel, timing and replay

Eight reused DEV parents plus2V66 stress, each WT plus the first archived mutant:
18 inputs. In this archive the nine mutants are A→C. Lengths88–164; this is not
a full19-AA screening benchmark or an independent accuracy panel. Four original
noises per workload. Exactly54 unprofiled steady repeats,18 synchronized-stage
runs,18 excluded warmups, one separately recorded first invocation, four
operator-profile passes and four CPU-profile passes. Actual counts:99 C4,
396 recycle iterations,396 S1,396 bitwise coordinate replays; zero updates.

Model and live ESM loading cost46.551s. The first complete workload took16.222s,
kept out of steady medians. Per-case steady workload medians span0.569–0.948s.
The sixteen DEV case medians average0.723426s; synchronized-stage workloads average
0.733619s. Parent GT/mask/inventory/reference lookup and archived-coordinate audit
are outside these sequence workloads, separately recorded. Confidence/CIF service
is absent. One worker removes this experiment's own multi-worker contention;
other host activity remains uncontrolled. Three repeats describe this small audit,
not a robust production throughput distribution.

| Synchronized DEV stage, per sequence/four noises | Mean ms | Fraction of synchronized wall |
|---|---:|---:|
| Full native C4 trunk | 400.765 | 54.63% |
| Four S1 ranges, including noise construction and cache preparation | 141.421 | 19.28% |
| Native feature construction + inventory check | 99.749 | 13.60% |
| Live ESM | 43.246 | 5.89% |
| Geometry-label setup | 31.335 | 4.27% |
| Task and geometry scoring | 9.582 | 1.31% |
| Host→device features | 2.625 | 0.36% |
| Four output host transfers | 0.714 | 0.10% |
| Relative/atom pair preparation | 1.079 | 0.15% |
| Coordinate NPZ writes | 2.746 | 0.37% |

Small unattributed overhead accounts for the remainder. S1-range time is **not**
denoiser-only GPU time: the range includes CPU identity-noise construction,
noise transfer, pair/atom cache construction and the actual denoiser. Unprofiled
per-stage entries are host elapsed times without stage synchronization; only the
explicit synchronized pass supplies this breakdown. Do not convert GPU enqueue
times into execution times.

For separate2V66 stress, WT/mutant steady medians are0.6077/0.6131s, with stage
breakdowns0.6053/0.6127s. Its values are not pooled into the DEV mean.
Measured steady peak allocation across DEV inputs is12.22–12.45GB, including
resident Mini/ESM weights. No candidate or noise batching was tested.

## Profiler overhead and operator evidence

| Fixed mutant | Steady median s | Torch profiler s | CPU profiler s | GPU events |
|---|---:|---:|---:|---:|
| 5OI7 A50C | .5708 | 2.0828 | .6571 | 19,464 |
| 2V66 A49C | .6131 | 2.0857 | .7347 | 19,564 |
| 1JKE A3C | .8083 | 2.1600 | .8766 | 19,582 |
| 4LR3 A26C | .9479 | 2.2139 | 1.0390 | 19,534 |

Torch profiling materially perturbs wall time (~2.3–3.6× these unprofiled medians).
Operator statistics locate work; they are not deployment latency. ATen device
self-time leaders include mm, native_layer_norm, copy_, bmm and addmm. Each trace
contains2,931 mm calls,1,011 native_layer_norm calls,635 bmm calls and511 addmm
calls over ESM+C4+four S1. Matrix operations, normalization and many small
operations deserve targeted investigation, but no kernel replacement or fusion
was evaluated here.

Do not sum user annotation ranges, ATen totals and raw GPU kernels together: they
represent overlapping levels. `aten::copy_` is not synonymous with host↔device
transfer; actual explicit transfers are a small fraction in the stage breakdown.
The trace does not by itself establish a GPU-utilization percentage or a causal
benefit from batching/fusion. Four full Chrome traces remain on DiamondHill;
operator summaries, CPU call records and trace hashes are archived in Git.

## Cache repetition is real but small

All18 fixed-candidate probes recomputed pair_z and p_lm/c_l four times. Every
repeat produced identical values and left RNG unchanged. Source dependencies
exclude sigma and noisy coordinates but include candidate final z and atom
chemistry. This supports considering **within-candidate, across-noise** reuse;
it gives no cross-mutant permission.

One pair+atom cache construction costs1.91–2.98ms in the isolated synchronized
probe. Removing three redundant constructions would nominally save5.7–8.9ms,
about1.00% of the DEV steady workload on average. That is only a first-order
estimate, not a measured optimized speedup: allocation, retained memory and
synchronization can change the result. Cache reuse alone is not a major answer
to this workload's latency.

## More useful host-side leads

**Identity-keyed noise.** Source inspection shows a per-atom SHA256 key, private
NumPy generator construction and three draws, repeated for every noise. cProfile
attributes34–65ms of self CPU time to identity_noise across four noises in these
four traces, with additional called work. Cumulative values61–288ms include
instrumentation and potential waiting at tensor creation, so cannot be copied
into an additive speedup estimate. Exact identity/seed lookup is a plausible
future optimization; changing random-number algorithms is not equivalent.

**Unused training labels in screening.** build_adapter_supervision constructs
smooth-lDDT labels and GT bond targets, but screen_native/response_geometry do
not consume those fields. In the four CPU profiles, smooth-label construction
has13–40ms cumulative time, versus19–51ms for the complete label builder.
The non-profiled synchronized geometry-label stage ranges roughly16–56ms across
all inputs. A screen-specific metadata builder is a concrete candidate for
removing unused work, while preserving identity/topology validation and exact
geometry outputs. Keep the original training helper intact.

**Native feature construction.** Its ~100ms DEV mean is meaningful, but rebuilding
mutant chemistry is required. The dependency audit distinguishes immutable CCD
assets and token-layout-relative features from the actual candidate atom graph.
No claim that the entire feature dictionary can be shared, and no cache was
installed. Observed WT/mutant comparison gives46 equal/57 changed leaves per
pair; all s_inputs/s/z differ, while relp matches in these equal-length monomers.

## Decision

Close this profile-only batch. It supports examining exact-output host-side
simplifications before another state approximation: avoid unused screening label
work, then investigate identity-keyed noise preparation with unchanged outputs.
The pair/atom cache repetition is verified but its isolated potential is small.
GPU operator work remains the largest component and can be studied separately
with pinned output/replay criteria. None of these proposed savings has yet been
implemented or promoted. No further batch was automatically launched.

Artifacts: [reports/mini_execution_profile_2026-10-06](../reports/mini_execution_profile_2026-10-06/)
contains protocol lock/report compressed JSON, timing summary, independent audit,
CPU profiles, source/trace hashes and local test log (four tests passed).
Runtime including raw traces/coordinates:
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/execution_profile_v1_20261006`.
Metadata mirror: `/home/husrcf/Code/onestepfold_runtime/execution_profile_v1_20261006`.
