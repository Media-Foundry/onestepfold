# Native candidate compute-budget curve v1 — 2026-10-05

This follows closed score-head objectives7b7b763b. Pause small scoring-head
training/floor search. Test native cold C1/S1,C2/S1,C4/S1 with real candidate
features/ESM/atomgraph, no training, warm-start, student or targetC4latent injection.
C4 stays the reference/default; C1 is a diagnostic budget, not a new hard goal.

## Reuse audit

Stage0B archive contains1024parent nine-grid scores: C1S1/C2S1/C4S1 meanTM/lDDT
.8809/.8181,.8933/.8358,.9029/.8465. Stage0confirmation256parentsC2S2vsC4S2
warm-time ratio.585 with mean lDDT−.0072 and13/256TM-style degradation>.05.
Those are parent folding/legacy stochastic and scoring settings with cachedESM,
not this FP32 hard-mutant ranking workload or full preparation+screen timing.
ChordFold edit report2026-10-01 explicitly did not execute warm-start compression.
Reuse these as historical evidence, not interchangeable matched outputs.

## Fixed panel and input

Archive context_replication_v1_20261005: all8previous confirmation parents nowDEV,
all4ADLTsites each; add2V66's same4sites as separate stress stratum.9parents,
36sites,693unique native sequences (9WT+684nonWT). No new sampling/downloads.
All existing nativeinventory/GT/weight/sourcehashes locked. None of these are fresh
independent confirmation. No result-driven substitution; failures kept and fatal
execution errors halt downstream work, no replacement/retry.

PublicMini-ESM FP32 and liveESM2-3B, eval/MCdropoutoff, native_featureseed101,
original deterministic kernels and stableS1decoder. Fournoise230201/230211/
310003/310019 identity-coupled acrosscycle budgets. Everyarm rebuilds all native
features and ESM; full_recycle_pairformer starts from zeros for1/2/4cycles,
and supplies all its own s_inputs/s/z to S1. No WTstate or exacttargetstate cache.
Eachcandidate produces real full-heavy-atom coordinates. No geometry repair.

Rotate the six(1,2,4)order permutations by sequenceindex, countering fixed order
bias. Expected2079conditioning calls,4851recycles,8316S1calls. No best noise.
C4 coordinates replay all693archived sequences/fournoise bitwise before acceptance;
C4failures retained from archive. Exactnativeinventories verified for everyarm.

## Timing

GPU synchronized resident-model screening latency per sequence includes separate:
CPU native feature rebuild; device/relative/atom preparation; targetESM;
full cold conditioning; fourS1predictions and host transfers; geometry-label setup,
parent-reference task+geometry scoring; coordinate archive write. Also record total
wall around this chain, so unallocated overhead is visible. Shared parentreference
pair preparation/inventory lookup is measured perparent and charged equally.
Model/ESM load cost recorded separately and added for first-use estimates; no
claim that resident latency includes process startup or loading. Everyarm pays
its own full features/ESM costs. No confidence head is requested/used in this
screening workload; this is not full officialrunner/CIF/confidence service timing.

Retrospective C4comparison metrics, checksum/replay audit, reportJSON publication
and offline collection are separately timed audit overhead, not included in screen
latency. Saving coordinateNPZ is included; no CIF writer runs. ParallelGPU workers
shareCPU/storage, so report contention setting, perparent workload ratios and
stage costs; no theoretical4x claim. 1parentWT is reused across its4sites within
eachmethod's workload, identically acrossarms. No source-latent amortizationclaim.

## Quality and selection

Use same archived parentGTCAHuber task andmask/sequence separation≥3. For eacharm,
compute mutant−samearmWT task at matching noise. Rank19nonWTcandidates againstC4;
oldnoise selects once, newnoise evaluates **C4reference** regret. Also report the
selectedcandidate's actual reduced-budget geometry/task. C4old-select/new-eval
is the teacher-noise reference, not zero regret by definition.

All generatedcandidate coordinates: sameinventory C4-output CA/allatomlDDT,
alignedCA/global-frame localRMSD, contact/bin/pairdistance differences using prior
functional_response_rank definitions. Local region=referenceC4CAwithin10Å ofsite,
including site; WTusesallCA. C4 is model output, not mutant experimentalGT.
WT-only experimentalGT metrics use fixedidentity/mask; no mutantGTclaim.

Geometry absolutecounts and transitions computed from generatedstructures:
severe nonbonded distances<1Å with graphdistance≤3exclusion, checkedCA/ILE/THR
chirality, maxpenetration; descriptivebond/peptide residuals. Old narrow connection
jointpass is not reinstated. No pass-count wording implying fullchemicalvalidity.
Reportmean/P95/P99/max and>1Å localtail, identities, absolute failures, pass→fail,
fail→pass. DEV8protein aggregate separatefrom2V66stress; allnoise instances belong
to theirprotein. Primary ranking, rawregret tails and complete timing jointly
inform direction, no posthocpromotions/gates. No furthertraining automatically.
