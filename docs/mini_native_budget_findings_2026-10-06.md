# Native hard-mutant C1/C2/C4 budget curve — terminal findings

The batch is **complete and closed**. C1/C2 reduce measured resident screening
cost, but neither preserves C4 candidate selection and structure sufficiently to
replace it on this development panel. C4 remains the default. No training,
warm-start, student promotion, or automatic continuation follows this batch.

Protocol: [locked native budget v1](mini_native_budget_v1.md). Execution source
commit: `d6534e4a`. Started 2026-10-05 15:57:04 UTC; completed after 580.121 seconds
(9.67 minutes, just after midnight October 6 in Hong Kong). Every controller stage
exited zero; terminal status is `complete=true, phase=closed, active=[]`.

## Integrity and scope

The audit counted 2,079 conditioning calls, 4,851 recycle iterations, 8,316 S1
predictions, 8,316 task checks, and 324 selection checks. **All 2,772 C4 coordinate
replays matched the prior archive bitwise.** Optimizer updates: zero. The startup
snapshot remains a historical partial result; it is superseded by these terminal
artifacts, not rewritten.

The main panel contains 8 previously observed development proteins, 32 sites,
19 non-WT candidates per site and four fixed noises. 2V66 contributes a separate
four-site stress stratum. Including parent WT sequences, there are 693 unique
hard sequences. Each C1/C2/C4 arm rebuilds native features and live ESM2-3B and
starts its own trunk from zero. Each supplies its own complete s_inputs/s/z and
native chemistry to S1. No exact target C4 latent or WT latent supports a reduced
arm. The model is the locked public Mini-ESM FP32 checkpoint, not a new student.

All panels are development data, not independent confirmation. Sequence lengths
are 88–164 for DEV and 111 for stress. The task is the parent experimental backbone
Cα-distance proxy, not experimental mutation utility. Structural fidelity below
uses same-noise C4 model coordinates as reference; only WT has experimental GT
accuracy measurements.

## Main development result

Spearman and Top1 compare four-noise mean scores across 19 non-WT candidates.
Cross-noise regret selects once using the two old noises in the corresponding arm,
then evaluates that fixed candidate with the two new **C4** noises. Protein means
are the aggregation unit. C4's own old-selected candidate has nonzero new-noise
regret; reduced-arm excess regret is reported separately.

| Arm | 19-AA Spearman | Top1 / 32 sites | Cross-noise regret | Excess over C4 old choice | Resident time / C4 |
|---|---:|---:|---:|---:|---:|
| C1/S1 | 0.327961 | 7 | 0.199890 | 0.154053 | 0.592246 |
| C2/S1 | 0.574671 | 12 | 0.165709 | 0.119871 | 0.797816 |
| C4/S1 | 1.000000 | 32 | 0.045838 | 0 | 1.000000 |

C1/C2 save approximately 40.8%/20.2% of resident workload time, corresponding to
1.69×/1.25× speedup. This cost reduction comes with substantial choice degradation.
C1's worst protein mean regret is 0.657089 (3QR7); C2's is 0.740294 (4LR3).
Protein regret medians are 0.030939/0.024229/0.018156 for C1/C2/C4. Individual
proteins can improve over C4 old-noise selection, including 5OI7, but this does
not establish an overall replacement advantage. Full per-protein values and
candidate selections are archived, including these favorable exceptions.

## Structural fidelity and actual generated geometry

Each arm has 2,432 mutant/noise outputs in DEV; these are repeated measurements
within eight proteins, not 2,432 independent proteins.

| Metric | C1/S1 | C2/S1 | C4/S1 |
|---|---:|---:|---:|
| AA-lDDT to same-noise C4, protein mean | 0.848943 | 0.923195 | 1 |
| Cα-lDDT to same-noise C4, protein mean | 0.868692 | 0.936743 | 1 |
| Aligned Cα RMSD to C4, mean Å | 2.691184 | 1.536677 | ~0 |
| Aligned Cα RMSD, P95 / max Å | 10.2048 / 33.6047 | 6.5558 / 20.9490 | ~0 |
| Local Cα RMSD in global frame, mean Å | 2.805357 | 1.459478 | ~0 |
| Local RMSD, P95 / max Å | 12.3782 / 27.5205 | 6.4938 / 18.6974 | ~0 |
| Local RMSD > 1 Å | 1,035 | 768 | 0 |
| Absolute checked geometry pass / 2,432 | 527 | 988 | 1,028 |
| C4 pass → arm fail | 690 | 337 | 0 |
| C4 fail → arm pass | 189 | 297 | 0 |
| Selected candidate passes both new noises / 32 | 3 | 12 | 8 |

The C2 net geometry difference of −40 conceals 337 new failures and 297 repairs.
Its selected-candidate pass count exceeds C4's, but its ranking and regret are
worse. Neither net counts nor selection fidelity substitute for absolute geometry.
C4 itself passes only 1,028/2,432, so it is not a universally chemically valid
reference. These checks cover severe nonbonded overlap and specified chirality
centers; they do not certify all chemistry. Bond/reference and peptide residuals
remain descriptive in the full records; the old narrow connection gate is not
reinstated.

Largest local tails include C1 5OI7 T80R/noise230211 (27.5205 Å) and 4LR3
T4P/noise230211 (26.1645 Å); C2 4LR3 T4I/noise230201 (18.6974 Å) and
T4V/noise230211 (18.0397 Å). These are disagreements with C4, not measured errors
against experimental mutant structures.

WT-only experimental GT AA/Cα lDDT means are C1 0.746250/0.818320,
C2 0.775179/0.853725, C4 0.787976/0.864250 under the same identity/mask protocol.
This provides a separate parent-folding accuracy comparison; it cannot establish
real mutation-effect accuracy.

## 2V66 stress stratum, kept separate

| Arm | Spearman | Top1 / 4 | Cross-noise regret | Local > 1 Å / 304 | Maximum local Å | Absolute geometry pass / 304 |
|---|---:|---:|---:|---:|---:|---:|
| C1 | 0.700877 | 2 | 1.344956 | 304 | 28.8783 | 0 |
| C2 | 0.842105 | 2 | 0.474544 | 227 | 12.9897 | 4 |
| C4 | 1 | 4 | 0.092300 | 0 | ~0 | 10 |

C1 introduces 10 pass→fail transitions; C2 introduces 7 and repairs 1. All three
arms have zero selected candidates passing both new-noise geometry checks.
The relatively high C2 ranking correlation does not protect structure or geometry.
Stress resident ratios are 0.630645/0.752210/1; they are not pooled into DEV.

## Timing interpretation

Resident ratios in the primary table are geometric means of matched per-parent
ratios. Each parent workload contains its WT once plus 76 mutants, four noises
per sequence. Each arm pays for native feature generation, device preparation,
live ESM, trunk, S1 plus host transfer, task/geometry screening and NPZ writing.
Parent setup is charged equally. Six execution-order permutations rotate across
sequences. Four workers share CPU/storage; non-trunk stage variation is visible.

| Mean seconds per DEV parent workload | C1 | C2 | C4 |
|---|---:|---:|---:|
| Resident screen total | 36.465 | 50.671 | 62.035 |
| Native feature build | 8.142 | 10.863 | 9.108 |
| ESM | 3.365 | 3.899 | 3.556 |
| Trunk | 8.594 | 16.765 | 32.114 |
| Decode + host transfer | 12.315 | 15.025 | 13.231 |
| Task/geometry screen | 3.492 | 3.423 | 3.419 |
| First-use additive estimate | 86.404 | 100.610 | 111.974 |

First-use estimates add measured model/ESM loading (~49.939 seconds on average)
to resident work; they are not separate fresh-process measurements for every
parent. Totals also include device preparation, NPZ writing and residual overhead.
Ratios of table means need not equal geometric means of paired ratios. Offline
C4 fidelity evaluation, audit and report publication are separately recorded in
execution.json. Confidence/CIF service work is absent in all arms. These are
matched screening measurements, not an official full-service throughput claim.

## Decision and artifacts

Close the batch without promotion. The experiment demonstrates a measurable
native compute/quality tradeoff, and rejects direct C1/C2 substitution in this
configuration. It does not test WT warm-start, blockwise reuse, learned early
exits, or the impossibility of those methods. Any next compute-reuse experiment
needs its own bounded protocol; none was started during collection.

Terminal [artifact directory](../reports/mini_native_budget_2026-10-05/final/)
contains summary.json, selection.csv, timings.csv, wt_gt.csv, compressed full
report and worker reports, execution/status, independent_audit.json and SHA256
inventory. No large coordinate arrays are committed. Coordinates remain at
DiamondHill `/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/native_budget_v1_20261005`;
metadata mirror is `/home/husrcf/Code/onestepfold_runtime/native_budget_v1_20261005`.
Startup tests and source checks remain in the parent artifact directory. This
closure changes only reports and research memory, with no model or evaluator edit.
