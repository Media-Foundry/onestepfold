# Repeated-context learning curve — running, not a result report

Snapshot2026-10-05 00:58HKT (2026-10-04 16:58UTC). User approved continuation of
the prospectivece91bb28 cohort. The bounded controller is running on DiamondHill.
This document records startup, not terminal training or transfer conclusions.

## Completed

- Locked the original40parents and A/D/L/T sites, nested8/16/32TRAINparents and
  eight separate confirmation candidates. No sample or site substitution.
- Native-input preflight passed **3080/3080distinct hard sequences**, zero failures.
  Full WT atom identity/order matches each archived reference mapping; all native
  variants have valid CA correspondence, finite reference coordinates, bounded
  bond indices and nondegenerate checked reference centres. This does not assert
  predicted geometry quality; no coordinates were predicted in the preflight.
- Four CPUpreflightworkers completed in about105seconds each. Eleven focused
  tests passed; run snapshot source/protocol hashes match local files.
- Four teacherworkers reached real hard forward/decode. Their firstWT C4 and S1
  repeat checks passed bitwise. All40WT replays remain required by the final audit.

## Running and queued

Teacher: publicMini-ESM FP32, liveESM2/C4/S1, native hard rebuild, no repair orsoft
mixture. Planned3120C4calls,12360S1calls including replays. Fournoise values are
230201/230211 forlabels and310003/310019 for evaluation. Counts are measured by
module hooks; do not infer completion from expected counts.

After collection and scoring, queue12fresh runs: two unchanged score heads,
two seeds, three data tiers.1024exposures/site gives32768/65536/131072updates;
also compare the common32768-updatecheckpoint. Scale0.5759913630974075 and
optimizer remain fixed. Training files contain OLD labels only and model inputs
never include mutant s/z/s_inputs. Alltraining mustfinish beforeconfirmationeval.

The heads still address reference-conditioned scalar screening, not structure
generation. The AA-only control and per-source/protein analysis are primary;
newWT-z decoder ablations are not in this budget. Selected-candidate geometry is
retrieved from native teacher outputs, not repaired by a scoring head.

The detached controller handles preflight→teacher→score→labels→train→eval→audit,
with finite timeouts and persistent status. Failure halts dependent stages and
retains partial records; there is no outcome-based retry, seed replacement,
checkpoint selection, automatic extension or promotion.

## Where to check the actual terminal state

Remote root:
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/context_replication_v1_20261005`

Local metadata mirror:
`/home/husrcf/Code/onestepfold_runtime/context_replication_v1_20261005`

Read remote`status.json`and`execution.json`, then`report.json`and
`independent_audit.json`. This frozen startup snapshot must not be treated as the
latest remote state. Do not duplicate-launch the controller after an SSH timeout.
Training and final selection results do not yet exist at this snapshot.

[Execution protocol](mini_context_replication_v1.md),
[startup artifacts](../reports/mini_context_replication_2026-10-05/),
[prospective data-design rationale](mini_context_replication_design_v1.md).
