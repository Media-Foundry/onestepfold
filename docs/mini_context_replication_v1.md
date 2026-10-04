# Repeated-context learning curve v1 — execution lock, 2026-10-05

User approved continuation ofce91bb28. Keep its40parent candidate manifest exactly:
32TRAIN,8confirmation-candidate parents,oneA/D/L/Tsite each,nested8/16/32TRAIN.
No replacement or exclusion based on new labels, geometry or training results.
ExistingHSP/accession components isolate all40 and exclude34oldresponseparents.
HistoricalfoldingTRAIN/pretrainingindependence is NOT claimed.

## Inputs and teachers

CPU native-input preflight on all3080distincthardsequences before any new model
forward. Check fullnativeatomidentity,finite reference features,CA mapping1..L,
topology/reference chirality construction and observed reference mapping. Retain
all failures; any invalid sequence stops collection without shrinking the panel.

PublicMini-ESM FP32,eval,MCdropoutoff,liveESM2-3B,nativefeatures,fullC4/S1; no soft
input,warm-start,relaxation orstudent. Weight hashes inherited from frozen public
teacher archive and checked before execution. Shared atom-identity noise seeds:
TRAINlabels230201/230211; evaluation310003/310019. All four frozen before labels.
Exact-onlyoutputs; omit privilegedWT-z ablation in this new budget. OldWT-z numbers
from otherproteins are not imported as new-cohortcomparators.

40WT+3040mutants=3080distinctC4; repeatWTonce/parent for3120C4/12480recycles.
Four-noiseS1=12320calls; additionally replay the firstWTnoise once/parent =40S1,
total12360. AllWTconditioning replays must be bitwise equal; S1 replays likewise.
SaveWTconditioning,allnativeinventories,fullfour-noisecoordinates,taskandgeometry.
Do not save massive mutant conditioning solely for this scalar-readout task.

Task remains parent-experimentalCApairHuber(delta1A),observedpairsseqsep>=3.
Each label=Exactmutant task-ExactWTtask at matchingnoise. ParentreferenceGT and
observedmask are explicit legal context-head inputs; no mutantGT/oracletargets/z.
No probabilities,experimental mutation effect or structural acceleration claim.

## Models and budget

UnchangedContextTaskReadout3,780,994params andAATaskReadout21,377params fromf858c875.
Two fresh pairedseeds231301/231303 xthree data tiers xtwoheads =12runs.
AdamWlr.001,wd.0001,eps1e-8,gradientclip1,globalMSEscale.5759913630974075 reused
from oldTRAIN,not refitted. No ranking/geometry/latentloss,LRschedule orGELUchange.

1024all19AA exposures/context:32768/65536/131072updates. Cyclecontexts in nested
parentorder thenADLT order,all19candidatesperupdate. Snapshots at half-budget,
32768updates andterminal(deduplicated). TRAIN-only curves during fitting.
Primarymatched-exposure endpoint; secondarycommon32768-update endpoint. Both
are reported,not used to select a checkpoint. Distinguish moredata+morecompute
from fixedupdates+fewerexposures. Allseedresults retained.

Training reads its tier-specific OLD-label file only; eval labels stay separate.
WTtensorloader rejects parents outside the trainingjob. Evaluate neweight only
afterall12trainingjobs finish. Also separately report trainingcontexts and other
TRAIN-poolparents unused by smaller tiers; those are development transfer cells.
No update is permitted after viewing confirmation outputs.

## Evaluation and audit

For each fixed endpoint andsite:19AArho,Top1,top3/5overlap,regret,rawdeltaMAE/RMSE,
old-only choice evaluated onnewnoisemean. Equalprotein aggregation,sourceAAbreakdown,
proteinmedian/worstregret,pairedcontext-minusAA-only perseed. Allscores saved.
Exactold-choice/new-eval provides the noise-disagreementreference. Undefinedrho
staysnull. No minimum NMSE gate. IncludeAA-tableTRAINfloor andenergyconcentration.

RetrieveExactgeometry for selectedcandidate inallnoises:zero severedistance<1A
pairs andallcheckedCA/ILE/THRchiralitysigns. Recordabsolutefailures,not geometryrepair.
Scoresproduce no coordinates orRMSD; previousR32tailremainsunresolved.

Independent audit:source/manifest hashes,sequence/GT/nativeidentity,WTreplays,
CPU taskrecomputation,alllabeldifferences,initializationpairing,optimizersteps,
exposures,TRAIN-onlyloading,terminalselection/ranking/geometry retrieval.
Head-only timing excludesWT/preparation/hardvalidation; not20C4speedup.

## Execution and stopping

Separate immutable rootcontext_replication_v1_20261005; originalreports unchanged.
ExistingHIP-onlyphysicalguard,max4workers,safeHIP0..3; no otherselector set.
CPUpreflight/scoring,then4teacherworkers,collection,training,finaleval,audit.
Perworker bounds:preflight30min,teacher2h,scoring1h,training2h,eval30min.
Queue all authorized stages detached; persistatomicstatus/failures. Stage failure
halts dependent work, retains partialdenominators, and never retries an outcome.
Only infrastructure defects discovered before outputs may receive a separately
recorded correction. No automatic extension,modelpromotion or nextarchitecture.
