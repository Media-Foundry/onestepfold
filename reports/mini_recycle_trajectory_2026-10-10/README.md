# Mini candidate-first WT trajectory audit — terminal report

**Complete; no training; no promotion; no speed claim.** This audit ran after all four
pair-placement fits, scoring and their independent checkpoint verification had completed.
It is separate from the two-seed placement learning comparison.

The [locked protocol](../../docs/mini_recycle_trajectory_v1.md) tests whether one real
candidate recycle followed by borrowed WT progression provides a better starting point
for the last candidate recycle than a cold two-recycle run. Mini, input protocol and
all native weights remain fixed. The learning variant has not been trained.

## Paths and integrity

For carried states `s/z`, write `W1,W3` for WT boundaries and `M1,M3` for true candidate
boundaries. The transported third-boundary state is evaluated as
`P3 = W3 + (M1 - W1)` in FP32, followed by one native update with the real candidate's
prepared inputs, MSA features and chemistry. This operation order preserves no-edit
identity; it is not claimed bytewise equivalent to every reassociation of the formula.

| Path | Candidate native recycles | Use |
|---|---:|---|
| Native C4 |4|Model quality reference|
| Cold C2 |2|Matched count of candidate updates|
| Mut1 + WT progression → final update |2|No learned correction|

WT C4 and its boundary extraction are shared reference work, not free. Native MSAModule
execution inside a recycle is included; upstream MSA/ESM preparation and input encoding
are outside this audit. Prepared candidate inputs remain candidate-specific. Target M3/M4
are saved separately as labels/audit targets and do not enter transport prediction.
The final single is recomputed, so this is not the fixed-final-single pair-only interface.

The frozen query-MSA protocol passed reference/candidate boundary-RNG equality checks;
continuation uses the saved reference RNG3, not an oracle candidate RNG. Native no-edit
and split replay, archive coordinate identity and one candidate isolation check per parent
passed before completion.24 parents,48 sites and912 mutants were audited on HIP6/7.
Both shards completed with456 target3+1 replays each and12 isolation checks each.

Recorded work is5,688 individual native recycle calls and5,568 S1 calls, zero input-encoder
calls and zero updates. The `c4` wrapper counter is zero because complete target trajectories
were reconstructed using individual recycle calls; it does not mean teacher reconstruction
was free. Audit reconstruction, native correctness checks and labels are charged in that
ledger. This concurrent audit is not a controlled inference timing experiment.

## Held development proteins

Nine repeatedly used proteins,18 sites,19 candidates and two noises yield684 outputs per
path. Spearman and Top1 compare two-noise mean candidate scores; regret selects on old noise
and evaluates the same candidate on new-noise Exact. Aggregation is equal parent. Native C4
is not experimental biological truth, and these data are not independent confirmation.

| Metric | Cold C2 | WT progression | Exact C4 |
|---|---:|---:|---:|
| Spearman |0.68616|0.74298|1|
| Mean-score Top1 |11/18|5/18|18/18|
| Raw cross-noise regret |0.024324|0.030820|0.008366|
| AA distance response RMSE, Å |0.43361|0.40680|0|
| All-atom lDDT fidelity |0.92332|0.93899|1|
| Geometry passes |296/684|405/684|438/684|
| Exact pass→method fail |170|50|0|
| Exact fail→method pass |28|17|0|
| Local RMSD P95, Å |2.2140|2.2627|0|
| Maximum local RMSD, Å |5.6724|5.9054|0|
| Local RMSD>1 Å |136|132|0|

WT progression improves average structure response and passing output count. It also
introduces33 failures relative to Cold C2 while repairing142; net pass count alone conceals
those transitions. P95 and maximum local deviation do not improve. Mean-score Top1 drops,
and raw regret increases by0.006496, despite the higher average Spearman.

The nine-parent descriptive95% interval for response RMSE difference is
[−0.04655,−0.00861] Å. Spearman's [+0.05682] interval crosses zero
[−0.00322,+0.11686], as does regret's [−0.00414,+0.02228]. The excess regret above
Exact remains0.022454 with a positive descriptive interval. These are development-panel
comparisons, not an independent claim of universal improvement or degradation.

2EBE A30 changes D→G, adding0.084197 raw site regret. E47 changes H→F, increasing
0.211440→0.255025. Benefits elsewhere are retained, including1YSB V5
(0.050158→0.014105) and4PQL L42 (0.024358→0.006306). All site changes are in
[selection_changes.json](terminal/selection_changes.json); severity and parent-level
geometry remain in [summary.json](terminal/summary.json) and [metrics.csv](terminal/metrics.csv).

## Other panels and what the last recycle does

The historical TRAIN panel is a role label; no parameters were updated here. Its average
Spearman improves0.69918→0.74743, response RMSE0.41631→0.38447 Å and regret
0.12830→0.07254. Geometry passes improve399→423/1026, while Exact passes412. Better
pass count than Exact does not establish experimentally better folding.

The three same-protein new sites are mixed: response RMSE0.50858→0.48977 Å and passing
outputs58→59/114 improve slightly, but Spearman falls0.73041→0.66725 and regret rises
0.07567→0.39670.1A7G S34 W→R changes site regret0.021067→0.888497. Local RMSD P95
increases3.7386→5.5896 Å even though the number above1 Å decreases60→17. This panel
must not be hidden in the larger averages.

For held proteins, centered `s` NMSE at transported boundary3 is0.10675 and after the
native final update0.06386. Centered `z` NMSE is1.11272 before and0.56579 after;
Cold C2 final `z` is0.76671. These before/after NMSEs have different teacher denominators
and cannot alone establish error contraction.

The separately recorded absolute latent errors provide the direct check: equal-parent
means of candidate RMSE fall1.28036→0.75363 for `s` and4.78936→3.68591 for `z`
(latent units, not Å). Yet errors increase after the update for45/342 candidates in `s`
and22/342 in `z`; maximum error-norm gains are1.596 and1.611. Thus the last recycle often
helps but is not a guaranteed corrective map. The joint fixed point, learned compensation
capacity and transfer of any future learner remain untested.

## Verification and archive

Local checks verified all19 archive file hashes, reproduced the full saved summary exactly,
independently recomputed432 Spearman values and144 old-select/new-evaluate regrets, and
checked5,472 per-output task/geometry-transition records. Native replay assertions occurred
on DiamondHill; local collection did not re-run coordinate scoring or those GPU operations.
[verification.json](terminal/verification.json) distinguishes these levels and records the
individual error amplification counts. The complete scores are retained in the15,673,641-byte
archive identified by [publication_receipt.json](terminal/publication_receipt.json), SHA256
`267c10bf864fb9f87b8dec0be387dd54cfa5be01d0f35b8ea03bfc185b38196f`.
The repository copy omits large per-output score files and model tensors; their source
locations and hashes remain available.

Deployment preflight records and two setup-only packaging failures are preserved in
`deployment/setup_attempts/`. They preceded GPU science; the final unchanged scientific
snapshot passed24 focused CPU tests. The original local-only `preflight.json` is historical,
while `status.json` and the terminal controller now record completion. No failed quality run
was silently replaced.

## Decision

The candidate-first transport interface is implementable and WT progression supplies useful
structure information at the same candidate-recycle count as Cold C2. It does not preserve
selection and structural tails well enough to replace C4. No learned correction or model
speedup has been demonstrated. Any subsequent learner must be separately locked, compare
with this fixed transport baseline, and distinguish pre-final state recovery from post-final
quality; this audit does not authorize a coefficient/prefix grid or automatic training expansion.
