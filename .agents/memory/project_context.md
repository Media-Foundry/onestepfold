# Project context

## 2026-09-27 — TRAIN4 scratch results accepted; mean benefit with mixed minimum/chemistry

User asks to inspect the first scratch overfit result. Jobs655575/655576/655577
all COMPLETED0:0; both arms pass predeclared jointgate, exact bestGPUreplay and
independentCPU acceptance (24saved predictions each). Archived204metadata/GT/
coordinate files onX570 andcurrentworkspace; allSHA matchHPC3. Review:
reports/esmc_scratch_overfit_v1_20260927/review.md. ManifestSHA
6a2a9793146e60273aaf7285b6838acc764cc2b12587037d803169d6891f395e.

Baseline firstjointpass500exposures/2000updates: meanAA .92660098,
minprotein/noise .91475449, worstnoise pooledRMSD .599833A.
Smooth firstjointpass550/2200: mean .97369208, min .96150663, RMSD .404129A.
Do not compare differentstoppingpoints as equalbudget. SAME500exposures:
smoothmean .93887055 (+.01226957), min .91110703 (-.00364745), RMSD .525493A;
only3/4targetmeans improve;1YRI drops .93783 -> .91304. All10common nonzero
checkpointmeans favor smooth, but not uniform tail/chemistry improvement.
Smooth450failed onlypooledCN .301742>.30;500failed onlypooledCO
.152456/.150858>.15. No thresholds relaxed. Baseline500 pooledchemistrypasses,
but4B9P individuallyCN .311061/.307771; avoidclaim allindividualchemistry passes.

This supports TRAIN4 memorization andnewloss fitting benefit, notgeneralization,
newarchitecture, fasterjointpass orP1>=.7. One trainingseed;twoinference noises.
Recommend nextcontrolledTRAIN32 with fixedcandidateandmatchedbaseline for
causal efficiencyclaims; explicitlylock itsgeometrygate (historical32pooled<=1A,
29/32<=2A differsfrom4all<1A), qualitygate,budget,andper-targetchemistryreporting.
Thisturn onlyreviewed/archived; no newtraining orDEV/test access, no ESMC
extractionresume/merge. Existingextractionhandoff remains a separate scope.

## 2026-09-27 — Extraction running; user-requested handoff

All3 extraction workers passed startup and processed real training sequences.
At final handoff: localR9700 PID850552 processed7606/9887; PrecisionW7900 GPU0
PID802988 processed71/9957; GPU1 PID802989 processed69/9925. These are startup
snapshots, not current or final counts. Precision root /media/990Pro/onestepfold/
esmc_29769_20260927; local root /home/husrcf/Code/onestepfold_runtime/esmc_29769.
BothPrecision processes detached, source/modelhash checks passed. Startup evidence
archived reports/esmc_29769_extraction_2026-09-27/startup. No subsequent monitoring,
merge, structure preparation or training under this turn. User explicitly asked
stop after extraction starts; wait for user to resume. ExistingHPC3 jobs untouched.
Future continuation: verify completion manifests/checksums andcross-host probes
beforeacceptance; do not launchduplicatewriters intoexistingpart directories.


## 2026-09-27 — 29,769 structure sequences; stop after ESMC extraction starts

User accepts29.7k, explicitly requests structure-derived sequence inputs and says
stop after extraction starts. Precision additionally authorized: two idle W7900
48GB, working directory /media/990Pro/onestepfold/esmc_29769_20260927. X570 local
R9700 32GB root /home/husrcf/Code/onestepfold_runtime/esmc_29769. DiamondHill remains
authorized for subsequent data preparation/training, but do not start that work
under this limited extraction handoff.

Selection29769 TRAIN unique exact-sequence groups,20–1024 residues,8830652 total
residues; all1600 historicalDEV excluded, fixedDEV128 unchanged, old8192 structure
representatives retained, pre2021-09-30 validTRAIN quality andcanonicalsequence
rule retained. No frozen-test coordinates/manifests read. Sequence is the accepted
structure construct, not UniProt full length; retain unobserved sequence positions
with label masks rather than concatenating observed fragments. Hash of groups.gz
4fd740e5fda9f709c973065a4cb6f7a620d36c8e1101ad818a96862785af4ecb.

All selected final-layer features already cached onHPC3. Current new extraction
therefore adds fixed12/24/36 layers for the user-authorizedMLC candidate; no changes
to ongoingfinal-only training. Three disjoint hash-mod3 partitions:0=9887groups/
2941726residues localR9700,1=9957/2952403 PrecisionGPU0,2=9925/2936523 PrecisionGPU1.
Codebf343ba264b650dff7a073643725f9aaa1fdbe8d andHF28aed46fcaf217dfa59f78a589bb449aa3ae5d98.
Modelblob SHA526573c304b7718f9cfd2a8adf79638feb6752eb38056968bf21d9036b7882ce.
LocalFold torch2.9.1/ROCm7.2; PrecisionBIO torch2.13/ROCm7.15. ModelFP32, storageBF16.
Per-card batchtokens2048, sharded16384residues. Source/inputlockchecks plusfinite
20/271/1024 TRAINstartup probes before extraction; common probe tensors saved.
Four cachecontract tests passed. Cross-device/oldcache numericalcompatibility,
full shardacceptance/merge andlongchainstructurepacketQA remain pending.

LocalPID850552 started andwriting safetensors. Precisionlaunch records will be
archived under reports/esmc_29769_extraction_2026-09-27; checklaunch/progress records
for currentPIDs, never blindly restart/overwrite. Currentcachedfeatures not yet
accepted for training. No automatic merge, training or monitoring afterhandoff.
See docs/esmc_29769_extraction_2026-09-27.md and frozen source/lock.


## 2026-09-27 — Scratch-first plan and bounded TRAIN4 supervision diagnostic

User asks for an overall plan and explicitly says to start step by step with
an overfitting test from the beginning. New plan: docs/scratch_model_plan_v1.md.
Retain frozen ESMC600M; no folding checkpoint or coordinate-teacher training.
This updates the priority of the prior pretrained-tail recovery plan, while
leaving running locked continuation655518/655519 and their dependencies unchanged.

Old scratch already used a random ESMC projection and passed TRAIN32; do not
claim simply reinitializing creates a new architecture or repeat the old grid.
First new variable: add10*smooth-all-atom-lDDT to A+.1F+R+10D, compared with a
matched baseline. Both use the same random seed101/raw existing16+8 topology,
TRAIN indices[0,7,15,31], exact initial hash/old-coordinate replay, batch1,
AdamW1e-4/wd1e-4/clip10, c1/s1/K1, final-only ESMC. One H100 per arm, acd_u.
Same atom-neighborhood mask/reduction as true lDDT, sigmoid temperature0.1A;
fixedweight10 is one engineering candidate, not a selected optimum.

Eacharm max1000exposures/protein or2h optimization window, evaluate every50,
3h Slurm hard limit. Jointgate = old TRAIN4 geometry criteria AND eachprotein's
AA-lDDT>=.90 at BOTH inference noises. Preserve per-noise scores; no best-of-K.
No DEV/test access. No automatic TRAIN32 or new-method launch after completion.
A small fit pass establishes trainability, not generalization/P1>=.7.

Code: train_scratch_overfit.py, validate_scratch_overfit.py,
report_scratch_overfit.py, smooth_lddt_supervision.py, scratch_overfit.py.
HPC3 isolatedroot /data/user/shuang886/Folding/esmc_scratch_overfit_v1_20260927,
source code_v1; CPUtests655572 COMPLETE0:0 (CUDAcase skipped onCPU).
TRAIN4 baseline655575 and smooth_lddt655576 RUNNING onH100/ACD1-28. Both
GPU deterministic loss tests and zero-update GPU preflights passed: exact
random-init/raw-coordinate replay, finite front/head gradients and c1/s1.
Independent acceptance runs inside each GPU allocation with CUDA hidden;
CPUreport655577 waits afterany onboth and requires accepted artifacts.
Source manifest SHA7ef22659af1070304132bfdcc9d6d4891533a2e2527477fceb35b2740708facc;
all9 new local source/protocol files match. No trained quality claim yet.
Model constructor, oldlabels/source hashes, finite gradients, true NFE,
checkpoint replay and independent dense CPU lDDT/smooth-loss checks gate acceptance.

## 2026-09-27 — All-atom 0.90 target and staged tail-recovery protocol

User explicitly clarifies0.90 means observed ALL-ATOM lDDT, not CA or confidence.
Native~.82 recovery is an intermediate gate, not the ultimate target or proof that
teacher distillation reaches.90. Concrete implementation plan:
docs/esmc_quality_recovery_plan_2026-09-27.md. Finish locked continuation first;
if fixed hard targets still decline, one GT+teacher local-distance retention
comparison before a separate zero-output nonlinear bridge; MLC separately,
core depth/Shortcut/MeanFlow deferred. Teacher labels TRAIN-only with GT anchoring,
no DEV-tail oversampling, no new frozen-test use. Plan is not a launched new
training recipe; no changes to ongoing continuation.

Added scripts/report_pretrained_fixed_tail.py. CPU655530 COMPLETE0:0; report SHA
 e358730e25997bcab9fef12163f5be6da10e38558b36fa40451ba3fa696e6fe1
matches remote/local. Confirms same7 AA targets at initial and both4096 endpoints.
Fixed CA-tail mean .46683 -> .40792/.39915. At8192-size step2048 re-ranked membership
differs temporarily (fixedAA .37005 vs re-ranked .36743); final membership identical.
Final follow-up CPU655531 after report655524; dependency strict reads fail if
upstream missing. No active polling controller. GPU partition remains acd_u.


## 2026-09-27 — Results collected; fixed continuation resumed on acd_u

User resumed work and authorized next-stage implementation, timely git commit/push,
and consideration of ESMC multi-layer concatenation. Two hours means an approximate
experiment cycle, not a hard deadline. MI250 has 8 available GCDs; consider larger
matrices/batches after a throughput and comparability check. Latest explicit HPC3
partition instruction: **acd_u, NOT acd_ue** for GPU jobs.

Original 4096-update pair and all audits/scores completed. DEV lDDT2048/8192
0.80339/0.80100, TM0.89475/0.89470, worst5 lDDT0.37934/0.37377.
Initial bridge0.79201/worst5 0.42397; native reference0.81956/worst5 0.50695.
Mean improved but lDDT tail worsened significantly; joint goal NOT passed.
Both final32-coordinate checkpoint audits exact. Seven GT final artifacts and
four old warmstart final artifacts remote/local SHA256 matched; both plots viewed.
Old geometry branch joint gate failed; no further geometry grid.

Bounded next stage: exact model AND AdamW continuation for2048/8192 to cumulative
16384 updates, same objective/LRs/data/c1s1K1; fixed exports4096,8192,16384.
Each resume must exactly reproduce320 parent coordinates before updates; optimizer
state digest checked. Compare equal updates plus explicitly unequal-compute equal
8 exposures. No temporal test, no best-of-K, no new objective grid.
Protocol docs/esmc_pretrained_gt_continuation_v1.md; final first-stage findings
in docs/esmc_pretrained_gt_results_2026-09-27.md. HPC3 existing2 focused tests pass.

Remote /data/user/shuang886/Folding/esmc_pretrained_gt_continuation_v1_20260927.
Training655518/655519, audit655520/655522, CPUscore655521/655523, report655524.
GPU partition acd_u; CPU debug. Original mistaken acd_ue jobs655511–655517
cancelled after95s, partial outputs archived in cancelled_acd_ue; not pooled into
results. New jobs start from the accepted parent4096, not partial aborted outputs.
Dependency batch is afterany plus strict artifact gates, no active controller.

MLC: historical500-group contact probe scored final layer AUROC~.706 versus
12/24/36 concat~.615; this is NOT an end-to-end folding trial. Current folding
uses final-only1152. User-authorized next candidate is a single controlled MLC
trial with exact initial final-only function and zero-initialized extra-layer
projections. Not yet implemented/launched; do not claim folding MLC was tested.
Preserve current locked continuation while preparing that separate comparison.
Original ESMC600M one-step folding goal remains open; user pause revoked.


## 2026-09-27 — User requested an unattended batch, then stop monitoring

User explicitly asks to submit a task batch for roughly a2h window and then stop
and wait. Existing experiments remain unchanged; do not add duplicate experiments
or extend the predeclared4096-update endpoint just to fill walltime. Actual work
may finish before the2h window. Pause the active goal after this handoff; no more
active polling or autonomous research until the user resumes.

TRAIN2048/8192 jobs654978/654980 continue on4H100 each. Local scoring/monitor
controllers740846 and743889 deliberately terminated for this handoff; oldwarmstart
controllers686444/745012 alreadyfinished. Do NOTrestart these controllers: their
remaining work is now queued as a Slurm dependency batch, with a separate jobrecord:
reports/esmc_pretrained_gt_2026-09-27/unattended_batch/jobs.json.

Queued audit2048=655033 -> CPUscore2048=655034, audit8192=655035 -> CPUscore8192=655036,
then finalreport/2048-and4096plots=655037. EachGPUaudit waits forits existingtrain;
eachCPUscore checks successful32-output checkpointaudit before scoring missing
2048/4096 exports. Report requires allscores/completeworkers. Dependencies use
AFTERANY plus strict artifactchecks, so a failed predecessor leads to an explicit
failure rather than an indefinitely NeverSatisfied job. No automatic retries.
Only3 pendingdebugjobs; no duplicatedtraining. Batchscripts onHPC3 under
esmc_pretrained_gt_hpc3_v1_20260927/unattended_batch. Outputs stay remote while
assistant ispaused; archive/hashcheck/review whenuserreturns.

Latest scientific evidence:1024update CPUscore655019/655020 andreport655022 completed.
DEVlddt2048/8192 .79090/.79272; TM .88848/.89026; worst5lddt .39040/.39711.
8192-2048 meanlddt+.00182 CI[+.00084,+.00295]; againstinitial mean+.00071 CIcrosses0,
tail-.02686 CI[-.04340,-.01369]. Small relativeadvantage, no overallquality/tailrecovery.
1024report JSON91156fe0dfe54d84d7916d9eb4801a72e43c7145f393b9d307c0dbf6649f08be,
PNG096ce8c20edee448bde0e519d870112e0b38ae7c121cb5dea9f2095625cf3cf2,
PDFd861ef7112dd931171b92fed4303bacdf7dbd3e5ba9bedfa0256569b6d3c875a andMD
b941ca3c2c3645ed215402051bff3d478d8eee84be522ae254ffac01cbeb37a6 verifiedremote/local;
PNGviewed. No recipechange based oninterimresults.

OldgeometryQA654984/654985 completed18m23s/17m39s; aggregate/report655023 completed13s,
primaryjointgate NOTpassed. Finalraw/geometryDEVlddt .58481/.57245, meanTM .73016/
.71799; geometrychirality100% butCNmae .28312A vsraw.24846A. RawfullTRAINbest.61750,
geometry.60959. Raw/geometrysavedoutputcounts4928/4672accepted, FP32exactGPUreplay,
geometryFP64formulaerror8.44e-14. Legacycrossprecisiongate remainsfailed(max1.77e-4),
not hidden. Oldplot655024completed viaisolatedplot_code_v2: AST-identicallockverifier
avoids unusedSciPyimport underoldplotNumPy. Oldtraining/scoringunchanged. Finalold
report/plot files still need localhashreview/PNGinspection atnextuserresume; do not
resubmitfinishedjobs. OriginalESMC600M/c1/s1/K1 goal remainsunachieved, user-paused.

## 2026-09-27 01:57 HKT — First512-update result accepted; no overall quality gain yet

Previous andcurrentgoalturns PROGRESS. CPUscore655006/655007 COMPLETED32s/30s:
all640savedpredictions checked,8 dense-lDDTchecks. Interimreport655011 COMPLETED6s.
ReportJSON SHA7744155bb3a54a95d342ed3c27954364ca1977c57ddababcb7bd9cadf66a36e2,
MD6424b945ee00f5256fc61f7e1a72c1ab5dbfb08de76ea3e883aa1a703ea59e5e,
PNG96d139406553fe01f396d5c771a8f19a622978951eeccc003ac9baf32aa9fa68,
PDFca38d7f6d0ec1ce888ad09abc88e82306af1c54aeb3ba106e158f608adb7e7de
verifiedremote/local; PNGviewed. docs/esmc_pretrained_gt_interim_512_2026-09-27.md.

DEVinitial/2048/8192 at512updates: allatomlDDT .79201/.79078/.78987;
TM .88586/.88886/.88865; worst5lddt .42397/.39925/.40511;
worst5TM .38911/.37995/.39258; CNmae .10248/.10284/.10399A.
Relativeinitial tail-lDDT drops -.02472 CI[-.03609,-.01546] / -.01886
[-.03032,-.01088]. No jointquality-and-tail recovery.8192-2048 meanlDDT
-.00091 CI[-.00205,+.00017], meanTM-.00021[-.00147,+.00117]; no meanadvantage.
8192TMtail +.01262[+.00295,+.01853] isearlyexploratory, notconfigurationselection.
TRAIN32probe .78502/.78773/.78430, notfullTRAIN.8192hasseenonly2048distinct
proteinsatthispoint, so do notinferconvergence orrejectscaling prematurely.
Continuebothlocked4096updates; no loss/architecture/optimizergrid orfrozen-testuse.

Plot655009 failedmissingMatplotlib; explicitlauncherrepair655010 thenfailedbecause
report_raw_warmstart geometry import pulled newSciPy intooldNumPyplotenv. Preserved
bothfailures. Isolatedinterim_code_v2 copies onlythegeometrysummary function
(ASTidentical) andusesexistingplot_deps_v2; no metricformulachange. Auxmonitor
isnow session61515/PID743889, monitor_jobs.json carriesfailedjobsandnewprefixv3.
Oldmonitor5870/PID742304 and60987/PID743446 exitedonverifiedfailures; notlive.
Maintraining/scoringcontroller44056/PID740846 remainslive andunchanged.

Userconfirmed transientDNS/connectivityfailures; waitfewminutesandretrybefore
changinghosts, neverinferjobfailure fromtimeout. DHreachableagainat01:55:52,
uptime13days; finalsnapshot2testspassed3.10s; noDHGTtraining. KeepcurrentHPC3pair
onmatchedhardware, no duplicatedata/experiments. OriginalgeometryQA654984/654985
stillrunning~12min; oldcontrollers686444/687435live. Goal OPEN.

## 2026-09-27 — User clarification: retry transient remote connection failures

User says occasional connection failures resolve after a few minutes due to DNS
instability. On future failures wait a few minutes and retry the same connection,
then inspect authoritative remote process/job state. A connection timeout is not
proof of host/job failure and never justifies restarting a live job. Avoid changing
hardware solely because of a brief outage. DiamondHill SSH recovered at01:55:52;
uptime13days confirms no reboot. No GT training was launched there; its final
snapshot tests actually completed2passed in3.10s. Current matchedHPC3 training
continues unchanged; do not duplicate it onDiamondHill or resume the abandoned
transfer without a new need.

## 2026-09-27 01:51 HKT — Checkpoint reconstruction accepted; fixed-step monitoring prepared

Previous goal turn PROGRESS; current turn PROGRESS. BothH100trainingjobs654978/
654980 and maincontroller740846 confirmedlive, no duplicate/restart. At01:50,
TRAIN8192 had368updates/1472uniqueproteins,~0.95s/update;128-stepcheckpointtakes~2s.
InitialCPUscoring654986/654987complete. Firstqualitycheckpoint remains512updates;
no interimqualityavailable yet andno change to4096primaryendpoint.

Added read-only interimreport/PNG/PDFscript forfixed512/1024/2048/4096: samepaired
proteinbootstrap/mean/worst5/dualnative-and-initialreferences, commonTRAIN32,
chemistry andexplicitno-best-of-K/no-convergencecaveats. Uses onlyindependently
acceptedCPUscorefiles, checksdata/model/export/sourcebindings. Itdoesnotalter
workers or select a checkpoint. Code isolatedinterim_code_v1.

Newindependentcheckpointaudit655003 COMPLETED0:0 in53s: strictreconstructionfrom
TRAIN2048 step0.pt;32exactpredictions (8length-spaced commonTRAINprobes +8DEV,
twofixedK1noises), c1/s1/zeroconfidence, sampler/frozenheads/weightsunchanged.
AuditSHA e8487894f70c28b15dda213e17ea023137c25b2f9ae58bf886f9b251e56b698f
verifiedremote/local. Nooptimizerupdates ornewselection. Final4096botharmswill
receive the sameaudit. Fulloriginalgoal stillOPEN.

Auxmonitor scripts/finish_pretrained_gt_monitor.py, session5870/PID742304,
uses SEPARATE reports/esmc_pretrained_gt_2026-09-27/monitor_jobs.json toavoid
concurrentwrites withmainjobs.json. It schedulesfixedinterimsafterbothscores and
finalcheckpointauditsafterverifiedtrainingcompletion, noautoretries. Earlieraux
session7448/PID742185 terminatedonlytofixarchiving, beforenewstageseligible;no
training/controllerrestart. Auxnowarchives itsownreports/figures/audits evenif
maincontrollerhasalreadyfinished. monitor_source_manifest.jsonpinsnewtools.
OriginalwarmgeometryCPUQA654984/654985stilllive; originalcontrollersunchanged.

## 2026-09-27 01:44 HKT — Matched TRAIN2048/8192 jobs running on eight H100s

Update01:45 HKT: both initial320-coordinate H100 bridge replays passed exactly.
Both arms completed32 real optimizer updates (128sample presentations), with
finite training and ~1.0s/update in the first32. Estimated4096-update completion
~75–90minutes including checkpoint/evaluation overhead; first512-update quality
~10minutes, both estimates provisional. InitialindependentCPUscore jobs654986/
654987 COMPLETED0:0 in33s/31s,320predictions each. Controller44056/PID740846healthy. H100initialDEV native/bridge
lDDT .819560245/.792011936; worst5 .506954899/.423968165; CAlddt .897540288/
.868844907; TM .913881361/.885856138. These within-backend referencevalues, not
trainedimprovement. OriginalgeometryGPUaudit654951completed andCPUQA654984/654985
running; originalreport/plotcontrollerspreserved.

Current goal turn PROGRESS. H100referencev2 job654973 completed0:0 in1m18s,
all640native/bridge predictions onfixedDEV128/commonTRAIN32; twofocusedtests pass.
CPUscore654975 completed0:0 in1m08s, all640coordinate hashes and16 independent
dense-lDDT checks passed. All4score hashes plusHPC3lock/source manifest archived
andverifiedremote/local. Firstreference654962 failed beforeGPUexecution onstale
common-files source-manifest binding; v1 preserved, no model/data/thresholdchange.

HPC3 root /data/user/shuang886/Folding/esmc_pretrained_gt_hpc3_v1_20260927.
LockSHA9a709fb1427f805336c1efbfe853db0a7930a8416acda6bd41fb403905781d7d,
sourceSHA9f446b7f56e40952782fc43273994cec754dacd95d3ab61204e64fc22589edf3.
Originalaccepted8320packets reused directly; dataacceptanceSHA
6814164d2215b461a4eff9e14a1720327789775052f6760eec17d05d46bfd8df.

TRAIN2048 job654978 andTRAIN8192 job654980 bothRUNNING onACD1-52,4H100each,
started~01:43. Same4096updates/16384samples; initial320exactH100bridge coordinate
replays perarm MUST pass beforeoptimization. At01:44 initialization stillrunning;
no trainedqualityclaim yet. BothenforceH10080GB/Torch2.7.1+cu128 andsamefrozen
runtime. No ESMC extractionneeded; finalconditionerESMC600M/c1/s1/K1 unchanged.

Newmetadata/scoring controller session44056/PID740846 islive:
python3 scripts/finish_pretrained_gt.py --archive reports/esmc_pretrained_gt_2026-09-27.
It submits CPUscoreonlyafteratomicexport, capsownscorejobs2, respects5debuglimit,
thenfixed4096reportaftertwo completeworkers/all10scores; neverretriesfailedjobs.
Do notlaunchduplicatecontroller/training. Metadata/scorearchive underexecution/.
Existingwarmstartcontrollers686444/687435remainlive; geometryaudit654951 stillruns,
oldtrainingcomplete. DHunreachable, partialfilesandlocks preserved; abandoned
transfercontrollerterminated beforefourdatastreams. NoDHGTtrainingwillautostart.
Goal OPEN; nextverifyinitialreplayandrealoptimizerprogress, estimatespeedfromtraining,
then inspectfirstfixed512-updatequality/tails. No methodgrid orfrozen-testaccess.

## 2026-09-27 01:38 HKT — DiamondHill connection lost; move unlaunched pair to HPC3

Current goal turn PROGRESS. DH SSH timed out from~01:30, includingfresh10s sessions;
optional userhardware-status question pending. No DHGTtraining launched. Its original
v1lock22ac5869d67b5ef862b2bc5c3663c735ed43b5a07d8f6e4797bb3b0b7e2bfb9c
andpartialdata preserved. Single-stream transfer intentionallystopped at~100MB/s;
3021filesverified,38579remainingpartitioned. Parallelcontroller27783/PID738016 was
terminated whilecopying list3, beforedatastreams/GPUtraining, toavoid duplicatework
whenDHreturns. transfer_abandoned.json records exactPIDs/reason. Two focusedtests
passed onDH temporarycompletepackage (firststagingattempt omitted models andfailed
collection; code/testsunchanged). Finalsnapshot test SSH6442 lostconnection afterone
dot; do not interpretas completed. PriorDDPpreflight34746 iscompleteaccepted.

UseroriginalHPC3preference andtimeconstraint authorizefallback; no furtherpermission
needed. HPC3dataalreadyaccepted. Same-model/data/recipe/budget, newH100baseline to
avoid cross-backend RNG replayassumptions. docs/esmc_pretrained_gt_v1.md amendedbefore
training; separateHPC3trainingroot esmc_pretrained_gt_hpc3_v1_20260927. Workeradds
GPUmodelassert, reportcostlabel GPUhours; immutableoldDHsnapshot untouched.

HPC3 DDP654959 COMPLETED0:0 in1m30s, H10080GB/Torch2.7.1+cu128. SameeightTRAIN,
twodiscardedupdates;1355gradienttensors serial/DDP relativeL2=3.70017499e-8,
maxabs4.768e-7, exactstate/optimizerroundtrip/allrankhashes, unchangedheads.
Warmfour-protein update0.657s (roughdiagnostic, notfulltrainingthroughput).
First H100reference654962 FAILED beforeGPU execution: bundle common-files manifest
still bound the old source manifest after adding the subset exporter. Preservev1.
Corrected isolatedbaselinev2 updated that source binding;654973 RUNNING:
 onlyfixedDEV128+commonTRAIN32, nativeandbridge,
twonoises,640predictions across4H100s. NoGTupdates. Twofocusedsched/optimizer tests
runfirst. SeparatebaselineCPUscoreandthennewHPC3lockwillbind allpredictions before
launching2048/8192,4H100 each,4096updates each. FullGTtraining NOTyetstarted.
OriginalDH's fullTRAIN512feature-fit/reference evidence remainsaccepted; H100
reference is needed for exactwithin-backend replay, notnewmethodselection.

HPC3originalgeometry654521 COMPLETED0:0 in4h16m46s; GPUaudit654951 stillRUNNING.
WorkerfinalmeanDEVlDDT raw~.584813 vsgeometry~.572450; fullTRAINbest~.617503 vs
.609594. These finalnumbers awaitgeometryindependentQA/pairedreport, notaccepted
jointclaim. Existingcontrollers686444/687435live, do notduplicate.
Newjobs tracked reports/esmc_pretrained_gt_2026-09-27/jobs.json. Goal OPEN.

## 2026-09-27 01:26 HKT — Distributed pretrained GT gate passed; matched2048/8192 protocol locked

Previous and current goal turns PROGRESS. DiamondHill four-GCD preflightPID1516484,
session34746 completed0, eight TRAIN rows33–256aa, two discarded optimizerupdates.
NCCLsum10;1355 tensor gradients match serial protein-mean reference relativeL2
4.15046584e-8 (maxabs4.768e-7); allrank gradient/state hashes identical; exact
model/optimizer save–reload and subsequentupdate; frozenheads unchanged. c1/s1/K1,
schedule[2560,0],gamma0=0,eta=1,lambda1.003,gamma_min1 recorded. Warmupdate1.68s;
firstcall10.86s includeswarmup. All four local rankreporthashes matchremote.
Preflightroot /media/PM982/onestepfold/esmc_pretrained_gt_preflight_v1_20260927.
No diagnostic checkpoint promotion; retain original native+bridge initialization.

Locked docs/esmc_pretrained_gt_v1.md: two4-GCD runs2048/8192, same4096updates,
16384samples (8vs2 exposures), freshAdamW bridge1e-4/core1e-5, originalA+.1F+R+10D,
constantLR,clip10. Lengthpool64 thenfour-protein batches preservesexactepochcoverage.
FixedDEV128/commonTRAIN32 export at0/512/1024/2048/4096 with twoK1noises; initial
320-coordinate exactbridge replayrequired beforefirstupdate. Final4096 primary,
notbestcheckpoint. IndependentHPC3saved-coordinate scoring required. Runtimecost
separate fromsamplebudget; no convergence/homology-independentgeneralizationclaim.
Four-hour hardlimit perrun; no silentautomaticretry. Training NOTyetlaunched.

Prepared newsharedobjective/scheduler and trainingentrypoint; twofocusedsched/optimizer
tests runningonDH. Immutabledata manifest assembling onHPC3 PID604693/session54102
beforecompressedtransfer toDH; all8320sourcepackets alreadyaccepted. No re-extraction
or frozen-testcoordinates. Existingwarmgeometry/controller untouched.
Goal remains OPEN: ESMC-600M c1/s1/K1 quality/tail/chemistry/confidence/end-to-end.

## 2026-09-27 01:07 HKT — TRAIN8192 accepted; frozen-core ESMC bridge reaches0.79190 DEV lDDT

Previous goal turn PROGRESS; current turn PROGRESS. All64 expansion preparation
workers completed, controller96658/PID730727 finished normally. Acceptance654890
COMPLETED0:0 in8m14s: all8320 packet files/source/selection links checked.
TRAIN8192/DEV128 ready; larger-model training NOT started. Acceptance SHA
e221458f2a539700f8c2a0bae1b031508b915c4ffe281e791bdf8d12def2ba45 verified
remote/local. All selected ESMC features present, no X570 extraction needed.

Sequence-only homology654923 COMPLETED1m38s, reportSHA
923d3b07c032e9c941be879a99fe95699c33d54a2c8a25ad8959bed3c3b13799 verified.
Old2048 results reproduce exactly. DEV identity strata(<.3,.3-.5,.5-.8,>=.8),
coverage>=.8 of shorter sequence: TRAIN2048=[0,72,9,47], TRAIN8192=[0,37,12,79].
Exact-distinct sequences are not independent low-homology proteins; no novel-fold
generalization claim from this DEV. Frozen temporal coordinates remain unused.

Actual ESMC input bridge fitted once on512 TRAIN/82362 residues, all inside old
TRAIN2048. Same fixed128 DEV, never used in moments or hyperparameter selection.
Protein-equal standardized affine ridge1152->449,lambda1e-3,varfloor1e-8,FP64 solve,
FP32 weights/bias. Frozen original Mini folding weights; no GT coordinate backward.
Fit654849 COMPLETED5m24s, three tests passed. Mean relative feature-MSE versus TRAIN
mean predictor .63735 TRAIN/.66215 DEV; feature residual does not define quality.
Checkpoint SHAfa93ea3733173c9a28dad97d7c57151d59bf29606bc018c9af6f36ae31f07e07,
fitreport999c3d90a78b4d4ba99ae80858f7aa430e22582d3917afdf502208314bd2cbd0 verified.

DiamondHill first extra CPU solver tests failed: self-builtTorch lacks CPU LAPACK.
Preserved failed preflight.log/exit; solve already passed onHPC3. Revised DH
preflight tests only needed loader/inference roles: two loader tests and four
longest-TRAIN native/ESMC x noise cases passed exact repeats, unchanged weights,
c1/s1/zero confidence,source/config checks. No recipe/threshold change.
PreflightSHA d579358bc73c0f3650ec59e9271c55a41bc5f954aeb63ce7bae11e5fe72f7862.
15GB bundle transfer plain session20508 intentionally stopped after measuring
35x compressibility of a12MB packet; losslessgzip session46030 finished0.
BundleSHA743d8468966d7d0b215bca7e858b8af0cf906e719f2cc57a82d8e0d6e554f158.
All transferred inputs hash checked. Four GCD workers PIDs1503866/67/68/70,
session21492 COMPLETED0, full_exit all0;2560 predictions, no best-of-K.
HPC3 score654907–654910 allCOMPLETED; allpred hashes,16 independent dense-lDDT
checks1e-12, same modelstate acrossworkers. Report654922 COMPLETED2s.

Accepted fullTRAIN512 native/ESMC: lDDT .81785/.78175, CAlddt .89663/.85910,
TM .91486/.87835, worst5lDDT .53348/.39955,CNmae .09349/.10491,
chiralitymacro .99845/.99795.
DEV128 native/ESMC: lDDT .81965/.79190, CAlddt .89761/.86870,
TM .91402/.88562, worst5lDDT .50746/.42412,CNmae .09342/.10241,
chiralitymacro .99811/.99859.
Bridge-native DEV meanlDDT -.02775 CI[-.03896,-.01777], worst5 -.08334
[-.14354,-.02552]; meanTM-.02840[-.04133,-.01683], worst5TM-.09637
[-.16559,-.02615]. Harm>.05:19lDDT,21TM,union23/intersection17 of128.
Tails remain clearly worse; not a fully recovered/final model. Chemistry incomplete.
Bootstrap5000seed20260926, protein resampling/unadjusted, single feature fit,
reused homologous DEV, no independent seed/test or end-to-end/confidence claim.
ReportSHA9b1a59073bf049da5f30eeeca50b0c53df623296b59da7fc6e04cfbe7736f060,
comparisonSHAf4de72f480ffe5085f26df03cf58ee6dbb70bd66ffc8210e72fa68ec8c46a6f4,
all four scores files verified remote/local.

This materially supports retaining mature folding priors and adapting ESMC.
Single-pass execution cannot alone explain prior scratch~.54-.58 quality.
Do not claim all causality isolated, ESMC universally beatsESM2, or scratch success.
Next: use this as the starting point for a bounded GT-supervised pretrained
initialization diagnostic at2048/8192, same recipe/init and matched budgets;
prepare multi-GCD gradient/optimizer preflight before locking run details.
No loss/noise/geometry method grid; scratch evidence remains a reference.
DH introspection confirms distributed/NCCL/Gloo available and8GCD, but collective
and distributed optimizer behavior NOT yet tested. CPU ridge stays onHPC3.

Original warmstart remains healthy: raw training/audit/CPUQA complete; geometry
654521 RUNNING after8192updates, finalbestTRAIN1232/4096 at01:07. Existing main
andplot controllers686444/687435 remain live. Finish their independentQA/report.
Original ESMC-600M c1/s1/K1 quality/tail/fullchemistry/confidence/end-to-end/independent
confirmation goal remains OPEN. See docs/esmc_pretrained_bridge_findings_2026-09-27.md.

## 2026-09-27 00:33 HKT — User-authorized TRAIN8192 expansion and native-path replay passed


At00:35, first workers had produced successful checked packets (~36 each after69s). Added CPU jobs654834/654835/654836 for workers4–15; four allocations submitted in total,16 worker shards/1536 new targets. Remaining48 shards await slots. Job IDs recorded immediately; no duplicate launches.

Previous goal turn PROGRESS (completed native path audit and cache/resource audit,
interrupted by user steering); current turn PROGRESS. User clarifies that training
size must expand, not remain a small interface exercise. This supersedes earlier
restriction to only preparing a small next experiment, while preserving the same
ESMC-600M/c1/s1/K1 objective and no loss/noise/geometry method grid.

Frozen TRAIN8192 is an exact nested extension of TRAIN2048, fixed DEV128 unchanged,
all original1600 DEV groups excluded. Same32–256 residues/canonical amino acids,
pre-cutoff valid TRAIN manifest, deterministic group hash ranking, no model-error
selection. Source global sequence catalog read for strings; frozen test manifests
and coordinates not read.13537 eligible groups; reuse2176 packets and prepare
6144 new ones. All8320 selected sequences have pinned ESMC cache entries: no new
extraction needed. Selection SHA207b6ba2ef603f47c267da9bbbd3e810698e412dfc347ef46d218c89442ccfd8,
report273d95e98d67ebaf1f95f6a11f0bbd74fa4c2296a4e21eb779db0c6421f694db.
Remote/local copies verified.

First selector mistakenly required HQ-eval status and failed before writing output:
790 existingTRAIN rows are valid training rows but not HQ-eval. Preserve failed
selector remotely; v2 restored original training eligibility. Old/new HQ counts
1258/2048 vs4982/8192; don't turn this into a label-noise diagnosis. New representatives
preserve old teacher choices when available; otherwise lowest resolution then
deterministic names among eligible TRAIN rows. Report composition and homology.

CPU prep654833 RUNNING at00:33, four workers0–3/64 (96 targets each),30min cap,
4CPUs48G, zero GPUs. Separate root esmc_expansion_data_v1_20260927, frozen108-file
source manifesta6d47aa0234c476443a071ab80ac4b1bea064e790b7ac315cf247ac0bc47761b.
Only prep-code change is explicit --input-root, default unchanged. Existing warm
experiment source untouched. Wait first successful packet checks/rate, then
dispatch remaining60 shards within scheduler limits. Combined8320-packet
acceptance required before training. Actual larger-run training budget remains
to lock after ESMC interface and hardware preflight; don't claim training started.
docs/esmc_training_expansion_2026-09-27.md records complete boundaries.

Native-path GPU654809 COMPLETED0:0 in58s. Two TRAIN proteins128/256, each native
and prepared chemical inputs: native upstream coordinate path vs frozen ESMC
wrapper with ORACLE native ESM2 projection exactly equal in all4 comparisons.
c1/s1/zero confidence/schedule[2560,0], unchanged weights. Report SHA
b73fee876f4e52a01e4e05274d3bb1600e9ca87b1ee05fd854fc96b1acfdad73 verified.
Not learned ESMC quality, not native/prepared cross-view quality equivalence.
Next fit actual ESMC interface, preserving pretrained folding core; ESM2 remains
diagnostic reference only. No claim ESMC invariably outperforms ESM2 for folding.

User also authorized X570 ESMC extraction. It is local husrcf-X570, idleR9700
32GB; Fold env torch2.9.1/ROCm7.2 available, esm package absent. No installation
or duplicate extraction performed. Pinned38400-sequence cache fully covers
current640 pairs,2176 scaling andnew8320 selection. Use X570 when real gaps arise.
GitNexus exploring skill read; no GitNexus server/tools available, direct frozen
source used instead (not a blocker).

Raw654520 and audit654798 plus bothCPUQA654800/654801 completed. Geometry654521
RUNNING7552 at00:33; controllers686444/687435 live, lifecycle no failures.
Keep current matched experiment through finalQA/report. Goal remains OPEN.

## 2026-09-27 00:20 HKT — Reprioritize folding-prior diagnostic; DiamondHill probe passed

User's new analysis corrects the overly broad claim that tiny-set capacity leaves
only generalization unknown. Archived raw2048 best checkpoint22528 has full
TRAIN2048 all-atom lDDT~.5521, CA-lDDT~.6274, TM~.7379 versus DEV128
~.5375/.6085/.6967. Larger-set fitting/optimization remains unresolved; reused
homologous DEV cannot establish generalization. Raw8192 denotes8192 extra updates,
not8192 proteins; same2048 TRAIN,30720 total sample exposures including parent.
Do not claim one-cycle capacity is sufficient at every data scale or attribute
the major teacher gap solely to geometry. Warmstart tests adaptation cost.

Preserve current HPC3 matched pair and QA. New priority is ONE diagnostic:
retain pretrained Mini-ESM folding core and adapt ESMC inputs. Scratch reference
and original ESMC-600M/c1/s1/K1 deployment goal remain; no new loss/noise/geometry
method grid or frozen-test use. More complete structural supervision and
multi-noise training are later candidates, not established fixes. Mini paper
batch64 x200K is sample-exposure context, not equal-FLOPs evidence.
See docs/folding_prior_reassessment_2026-09-27.md for source-checked findings,
limits and primary references.

HPC3 CPU audit654802 COMPLETED0:0 in33s. Native checkpoint SHA1301bba9...26664,
both models1613 tensors, no missing/unexpected keys; only mismatch is
input_embedder.linear_esm.weight native449x2560 vsESMC449x1152.
All1612 retained tensors/134067007 elements load exactly and compare equal.
Zero training/inference. Report/source remote-local SHA verified, report
269beae1d8a8cc9aad20a5815afbb2cd3f8c4892b4c97fb71f4d051e551b9ef0.
This proves tensor compatibility, not functional or semantic compatibility.
Next verify native-input replay, paired cached embedding alignment/distributions,
then lock one small adapter protocol using TRAIN only.640 existing teacher
sequence packets located in esmc_endpoint_v1_20260922; embedding contents not
yet validated for reuse. Avoid regenerating expensive ESM2 caches prematurely.

DiamondHill v1 failed strict config equality before GPU: launcher omitted
PROTENIX_ROOT_DIR, causing23 global dataset-path differences. Preserved failure.
V2 isolated root restored HPC3's declared environment with unchanged probe and
immutable staged inputs; no check bypass. All4 raw/geometry128/256 forward-backward
cases passed, finite gradients, c1/s1/zero confidence, unchanged weights,
zero optimizer updates. Runtime/source/config and checkpoint checks passed;
archive hashes verified. Maxallocated3159566336bytes; cold-first-call timing
does not prove H100 speedup, optimizer stability or8GCD scaling. New work may use
DH per user authorization; current matched H100 pair remains onHPC3.

00:20 HKT: raw654520 COMPLETED8192 and final outputs, audit654798 COMPLETED;
CPUQA654800/654801 RUNNING. geometry654521 RUNNING7008; no8192 paired result.
Controllers686444/687435 live, lifecycle no failures. Goal remains OPEN.

## 2026-09-27 00:07 HKT — Matched6144 and user-authorized DiamondHill portability check

Previous goal turn VERIFIED WAIT; current turn PROGRESS. Locked HPC3 summary654778
COMPLETED0:0 in9s; source/lock/contracts/history-at-read/snapshot/report hashes
verified including local archive. Raw/geometry mean lDDT .58264/.57043,
meanTM .72157/.72047; worst5 lDDT .28978/.30127, TM .24945/.24130.
Geometry-minusraw mean lDDT -.01221 CI[-.01926,-.00566]; meanTM -.00110
[-.01933,+.01757]; worst5 lDDT +.01149[-.01684,+.03578], TM -.00815
[-.02859,+.00891]. No joint advantage. Geometrychirality1.0, CNmae .30309A
vsraw .24502A. Geometry improves its owninitial mean lDDT+.06604 andTM+.02374,
but raw also improves: ownbaseline growth is not superiority. Reuseddev,
single trainingseed, unadjusted repeated-view intervals, no intermediate
coordinate QA. Keep8192 primary/4h cap and current H100 pair unchanged.

User asked training size and why raw initialization: both branches use same2048
TRAIN/128dev;32probe is a TRAIN subset. Parent has22528updates on same2048,
then up to8192 additional updates. Folding core scratch experiments already exist;
ESMC features are pretrained. Warmstart isolates geometry adaptation, not a claim
of superiority from random initialization; include parent cost in totaltraining.

User explicitly made DiamondHill's8GCD available and invited switching resources.
This supersedes prior HPC3-only resource preference for newly authorized use;
the current frozenH100 experiment stays onHPC3 through its existing QA.
Read-only inventory:8idle gfx90a MI250-series GCDs,~64GiB each. Existingfold env
/home/pc/anaconda3/envs/fold hasTorch2.12.0a0+git78258b9/HIP7.14.60850.
OneGCD bounded portability probe now running, PID1486260/session93788,
remote /media/PM982/onestepfold/diamondhill_runtime_v1_20260927.
Same frozen108source files andrawparent; two acceptedTRAIN packets length128/256;
four raw/geometry forward/backward cases, zero optimizerupdates,600s cap.
Verify upstreamsource/config, finitefront/headgradients,c1/s1/no confidence,
unchangedweights. No crossbackend equality/speedup/quality claim from this probe.
Do not start an8way training grid or migrate the current matchedpair.
Original ESMC-600M c1/s1/K1 quality/tail/fullchemistry goal OPEN.

At00:07 raw654520 RUNNING with8192updates, bestTRAIN files3252/4096;
geometry654521 RUNNING6464 with6144evaluation complete. Controllers live.
Docs: esmc_raw_warmstart_interim_6144_2026-09-27.md;
diamondhill_runtime_preflight_2026-09-27.md.

## 2026-09-26 23:08 HKT — Matched4096: geometry recovers most mean gap, joint advantage unproven

Previous goal turn VERIFIED WAIT; current turn PROGRESS. Locked HPC3 summary654685
COMPLETED0:0 in9s; source/manifest/lock/contracts/history-at-read/snapshot/report
hashes verified, including local archive. No independent4096 coordinate QA.
Raw/geometry mean lDDT .55229/.55100, meanTM .69655/.69080;
worst5 lDDT .28853/.30482, worst5TM .23941/.24172.
Geometry-minusraw mean lDDT -.00129 CI[-.00767,+.00469], TM -.00574
[-.02093,+.01033]; worst5 lDDT +.01629[-.01148,+.03889], TM +.00231
[-.01638,+.01539]. All four CIs crosszero: neither joint superiority nor
equivalence/noninferiority established. Loss>.05 counts12/128 lDDT,11/128TM,
versus25/27 at2048; counts alone do not prove the same targets recovered.
Geometry chirality1.0, CNmae .31683A vsraw .31456A; improved vs owninitial
.33419A and2048 .34643A, but no fullchemistry gate claim.
Geometry versus owninitial mean lDDT +.04661CI[.03881,.05406],
worst5 lDDT +.03325[.01288,.05126], meanTM -.00593[-.02737,+.01502].
TRAIN32probe raw .56500/.74689 vsgeometry .57446/.73604, notfull2048 TRAIN.
Provisional workerhistory, reuseddev/devselectedparent, one trainingseed,
unadjusted repeated-view bootstrap; no frozen test or independent generalization.
Keep8192 primary /4h optimization cap, unchangedloss/lr/sampling; next matched6144.
At23:08 raw654520 RUNNING6208 withhistory0/2048/4096/6144, geometry654521
RUNNING4224 withhistory0/2048/4096. Bothcontroller OS PIDs686444/687435 live.
No6144 pairedsummary untilbothhistories ready. Original c1/s1/K1 goal OPEN.
See docs/esmc_raw_warmstart_interim_4096_2026-09-26.md and
reports/esmc_raw_warmstart_2026-09-26/execution/interim_4096_v1.

## 2026-09-26 22:24 HKT — Revalidated existing C–N supervision against live frozen source

Current turn PROGRESS: source clarification, not a new numerical/gradient experiment.
Both warm-start arms already optimize A + 0.1F + R + 10D. D equally averages
N–CA, CA–C, C–O and consecutive C–N category MSEs; preparation asserts all four
nonempty, so C–N coefficient within 10D is 2.5. Labels use observed GT distances
and masks, not ideal bond constants or certified intact peptide bonds. PacketStore
checks accepted prepared/file hashes before loading supervision.pt. Four local
source hashes match the frozen HPC3 manifest bound by both run contracts.
This revalidates the known September 18 design; it does not establish the cause
of C–N worsening, relative gradient competition or sufficient chemical quality.
Do not duplicate the existing term or open a new weight grid. Keep the locked
8192-update / 4-hour optimization cap and matched4096 next comparison.
See docs/esmc_raw_warmstart_cn_supervision_2026-09-26.md and
reports/esmc_raw_warmstart_2026-09-26/cn_source_binding.json.
At22:24 raw654520 RUNNING3808, geometry654521 RUNNING2528; both histories0/2048.
Controllers32092/51405 remain live, no lifecycle failures. Original c1/s1/K1 goal OPEN.

## 2026-09-26 22:14 HKT — First matched2048 result: geometry mean quality worse so far

Previous goal turn VERIFIED WAIT; current turn PROGRESS. Both2048 evaluations
complete; lockedCPUsummary654605 COMPLETED0:0 in6s. Raw/geometry devmean lDDT
.55270/.51746, TM .70422/.66494. Geometry-minusraw meanlDDT -.03524
CI[-.04360,-.02776], meanTM -.03928[-.05981,-.01887]. Worst5 lDDT -.00979
[-.02278,+.01029], TM -.01009[-.03663,+.00949]; tailintervals crosszero.
Loss>.05 counts25/128 lDDT,27/128TM (overlapunknown; do notsum).
Geometrychirality1.0 but CNmae .34643A vsraw .31362A; bothworse than initial
.33419/.28192A respectively. No jointquality/chemistry recovery observed atthispoint.

Geometryfromowninitial: meanlDDT .50439->.51746 (+.01307CI[.00516,.02041]),
TM .69673->.66494 (-.03179CI[-.05102,-.01399]). RawmeanlDDT .53745->.55270,
TM .69673->.70422 (TMdifferenceCIcrosszero). Initialparameter-free CA preservation
does NOT guarantee preserving CAfold during freeparameter adaptation. Not a proved
implementationbug, capacityfailure or finalwarmstartfailure; onlyone newexposure.
TRAIN32probe meanlDDT/TM raw .56442/.74049 vsgeometry .52926/.69656, notfullTRAIN.

Allscores provisional workerhistory, notindependentintermediatecoordinateQA.
Bootstrap5000seed20260926, singletrainingseed, no multipleviewingcorrection,
historically reuseddev / devselectedparent. No frozen test. Source/manifest,
lock/contracts/history-at-read/snapshot/report hashes archivedverified.
docs/esmc_raw_warmstart_interim_2048_2026-09-26.md;
reports/esmc_raw_warmstart_2026-09-26/execution/interim_2048_v1.

Keep bothhealthy trainings, unchangedloss/lr/sampling/4hcap and8192primaryendpoint;
nextplannedmatchedmonitor4096. At22:14 raw654520 RUNNING3232, geometry654521
RUNNING2112, bothhistories0+2048. Controllers32092/51405 continue; no requeues
or newmethodbranch. Original ESMC-600M c1/s1/K1 quality/tail/fullchemistry goal OPEN.

## 2026-09-26 21:55 HKT — Raw2048 scheduled evaluation complete; matched geometry pending

Previous turn VERIFIED WAIT; current turn PROGRESS to completed firstscheduled
raw evaluation. HPC3 raw654520 remainsRUNNING and resumedupdates2080 after2048.
history containsstep0+2048, with256 devnoise rows and64 TRAINprobe rows at2048.
Archived immutable observation raw_2048_history.json under
reports/esmc_raw_warmstart_2026-09-26/observations; sourcehistorySHA verified:
478de3d2b47f60a6bbaec6001d97d09773051ad358d952bf3497c83f6b2b82d1.
This is workerhistory, not independentcheckpoint acceptance.

Geometry654521 RUNNING1440 at21:55, history onlystep0. Do NOT compare raw2048
with geometryinitial/currentunequalupdate. Wait geometry2048 evaluationcomplete
then submit preflightedinterim2048 once. No new quality ranking, stopdecision,
extra training or inference. Existing8192/4h gate andcontrollers unchanged.
Original c1/s1/K1 quality/tail/fullchemistry goal OPEN.

## 2026-09-26 21:45 HKT — Fixed-step warm-start monitoring prepared before results

Previous goal turn VERIFIED WAIT; current turn PROGRESS. New separately frozen
interim_code_v1/report_raw_warmstart_interim.py reuses locked final-report metrics,
bootstrap and geometry routines. Only2048/4096/6144 monitoring;8192 deliberately
reserved for finalacceptedreport. Requires botharms' exact scheduled point,
snapshots initial+current rows, pairs128same devtargets/two fixedK1noises,
reportsmean/p05/worst5/harm counts/geometry/TRAINprobe/within-arm initialchange.
All intermediate reports explicitly provisional andnotindependentlycoordinateQA'd;
no model/checkpoint/seed/stop selection or newqualityclaim.

HPC3 preflight654582 COMPLETED0:0 in22s, verifying imports/source lock/paired
contracts only. No interimnumeric analysis yet. Localremote source hash matched
d104c221905546bcebd040b5a045f33639ad2b6180b0adff0f43520d47d386b1.
Jobs trackedseparately reports/esmc_raw_warmstart_2026-09-26/interim_jobs.json.
Submit eachCPUsummary once AFTER both histories contain itsstep; no extra watcher
or modifying existingmainlifecycle32092/plotwatcher51405. Frozen trainingcode unchanged.

Both654520/654521 freshsacctRUNNING30:35; raw1600/8192, geometry1024/8192,
onlystep0 historysofar. Firstmatched2048 comparison notready. Keep4h cap,
originalone-stepquality/tail/fullchemistrygoal OPEN.

## 2026-09-26 21:36 HKT — Matched timing estimate: geometry budget margin is limited

Previous goal turn VERIFIED WAIT; current turn PROGRESS. CPU654565 completed0:0
under1s; read-only first512 actual matched updates, source/prefix/contract hashes
archivedverified. Raw two256-update rates1.0267/1.0302s; geometry1.5533/1.5437s.
Initial320 eval costs145.0/178.2s. Scenario optimization+scheduled/wallcheck eval
estimates8978-9294s raw,13352-13780s geometry vs14400s cap. Geometry margin
620-1048s (~10-17min), not guaranteed; maintain stopping budget if reached.
Final4992 prediction eval extrapolation2262s raw/2780s geometry. Conditional worker
finish9/27HKT00:26-00:31 raw,01:48-01:55 geometry; excludes queues, checkpointI/O,
GPUaudit/CPUQA/report/plot and workload/cache changes. These are scenario estimates,
notCIs or completion promises. No quality analysis or contractchange.
Full assumptions docs/esmc_raw_warmstart_runtime_2026-09-26.md.

Both654520/654521 confirmedRUNNING21:39 elapsed atlastsacct. Snapshot1056 raw,
672 geometry, stillonlystep0 histories. Controllers32092/51405 remainalive.
Nextactualquality2048; observe real timing, do not extend budget or restart to
force8192. Original c1/s1/K1 quality/tail/fullchemistry goal OPEN.

## 2026-09-26 21:24 HKT — Actual first64 schedule matched; final curves pipeline prepared

Previous goal turn PROGRESS; current turn PROGRESS. HPC3 CPU654548 COMPLETED0:0
in8s. Bothfirst64 update records match eachother and locked continuation scheduler:
sameepoch12/order/noise/lr/samples/residues;17 contractfields equal and bothinitial
320rawreplay acceptances bound. Prefix/source/manifest/contract hashes archivedchecked.
Differentlosses are intended because outputrepresentation differs. This is execution
matching evidence, not final scientific acceptance.
Artifact reports/esmc_raw_warmstart_2026-09-26/execution/dispatch_audit_v1/acceptance.json.

Separately frozen plot_code_v1 prepares final sixpanel mean/worst5 lDDT/TM,
CNmae/chirality curves from acceptedreport only. No smoothing/bestselection; stepzero
geometryoutput already differs while rawweights match. Stdlib plotpoints must match
acceptedmean/tail differences and finalgeometry<=1e-12. Existing isolated Matplotlib
3.9.2/NumPy1.26.4 import/sourcecompile passed in654548; trainingenv untouched.
Actual finalfigures notgenerated yet and will require visualreview.

Mainlifecycle32092 remainslive and unchanged. Separate plotwatcher51405 islive,
scripts/finish_raw_warmstart_plot.py, waiting for main jobs.json reportjob + successful
sacctstate and then submits lockedCPUplot respectingdebugcap. Its separate
plot_jobs.json avoids racing/restarting maincontroller. Do not assume32092 tracksplot.
No newtraining, requeues, extra data or altered8192 primarygate.

At2026-09-26 21:24 HKT bothmain654520/654521 authoritativelyRUNNING10:15;
raw384/8192, geometry224/8192, onlystep0 histories exist. Nextqualityevaluation2048.
Original ESMC-600M c1/s1/K1 quality/tail/fullchemistry goal OPEN.

## 2026-09-26 21:20 HKT — Both warm-start arms passed all320 initial raw replays

BothH100 workers654520/654521 stillRUNNING (lastsacct4:23). Initial raw exact
replay320/320 perarm PASSED before firstupdate; initial acceptance/contract hashes
archivedchecked. Seventeen paired contract fields match: parent/state/config,
optimizer/reset/budgets/data/probe/noise/GPU/precision/runtime sources. Initialweights
f7868bae151bae6bdcb5e27cb31a07b472ae3c6088477677d5b3937b612393ed.
Rawprogress32 at21:19HKT, epoch12; geometry initialchecks complete and entering
updates, nextprogress file at32. This is starting-condition proof, notfinalQA or
quality evidence. reports/esmc_raw_warmstart_2026-09-26/initial_pair_acceptance.json.
Lifecycle32092 live, locked downstream code prepared; no duplicate submissions.
Next scheduled quality comparison2048. Goal OPEN; current turn PROGRESS.

## 2026-09-26 21:17 HKT — Raw-to-geometry matched warm-start pair launched on HPC3

Previous goal turn PROGRESS; current turn PROGRESS. Archived scan45 contracts in
stage1b coordinate_refiner/Folding two-level scope found no training from raw2048
best checkpoint (scope-limited coverage, not whole filesystem proof). New locked
protocol docs/esmc_raw_warmstart_v1.md;108 source files preserve original scaling
implementation;15 input hashes bind parent/data/attribution evidence.
Parent raw2048 beststep22528, checkpointSHA
3d650e00292f7ac33a1076defe27595f85c24f24ec4df45c2872da58b84724e9.

Only two arms: raw_continue vs geometry_adapt (existingArticulatedOutput).
Same2048TRAIN/128dev, parentweights, freshAdamW1e-4 wd1e-4 clip10 batch1,
A+.1F+R+10D, nextsampler epoch12 after11 parentepochs. No teacher/newloss.
ESMC-600M c1/s1/K1 preserved via runtimehooks; no frozen-test access.
8192 additionalupdates or4h optimization/evaluation,7h workerreservation;
4 newexposures, notconvergenceproof. Primary8192 mean/worst5 lDDT/TM paired
bootstrap5000seed20260926; bestseparate, chemistryseparate, parentcost retained.
Eacharm MUST reproduce320 raw initialdev/probe outputs exactly before updates.

Lock654516 COMPLETED0:0 in14s,5 tests passed. GPU preflights654517/654518
COMPLETED0:0 in45s/29s, longest backward/identity/zeroupdates passed.
Both7hH100 trainingjobs654520(raw)/654521(geometry) nowRUNNING, initialevaluation
in progress; no trainingquality conclusion yet. Preflight/lock archivehashes checked.
Lifecyclecontroller session32092 active, source scripts/finish_raw_warmstart.py,
metadata-only: submits locked rawidentity/GPUprojection audits,2CPUQAparts perarm,
then exact-disjoint aggregation/report after verified successful predecessors.
Respects5 debug pending/running jobs, never retries failedstages or restarts training.
All sciencecode/QA/reporter alreadyfrozen in code_v1. Do not launch anothercontroller
without checking session/flock and persistedjobs. Jobs dynamicallyrecorded in
reports/esmc_raw_warmstart_2026-09-26/jobs.json; resultsroot
/data/user/shuang886/Folding/esmc_raw_warmstart_v1_20260926.

Next: confirm320 initial rawreplays perarm, compare first schedules/source/precision,
then wait for planned2048/4096/6144/8192 evaluations and finalQA. Partial elapsed
observation is notfailure. Original one-step quality/tail/fullchemistry goal OPEN.

## 2026-09-26 21:03 HKT — Projection attribution closed; sidechain and N-end effects localized

Previous goal turn PROGRESS; current turn PROGRESS. Same64 raw/projected TRAIN
outputs, no network calls/updates or new dev/test coordinates. New protocol
 docs/esmc_projection_attribution_v1.md;464 inputs and108 source files hashlocked.
HPC3 CPU654482 completed0:0 in11s,2 tests passed; independent scalar/target/input
validator654489 completed0:0 under1s. Reports/rows/QA/lock hashes archivedchecked.

Two-factor order-average lDDT changes: backbone -.00042994, sidechain -.02980837,
total -.03023831; sidechain share98.6% of this macro net drop. C-N MAE changes:
C-end +.00591284A, nextN-end +.04649815A, total +.05241099A; Nshare88.7%.
Interaction -.00006675 /+.01004644 respectively already split into the contributions.
Not unique physical causality or per-target universal shares. Hybrids only diagnostic,
not chemical-valid candidates. CA coordinates/TM unchanged; CA-center allatom lDDT
can drop because neighbors move. Sidechain mean displacement2.2858A, N .4884A,
C .1966A. Do not conflate center-atom loss attribution with moving-atom attribution.

All parentendpoint scores reproduce<=1e-12; all contributions close. Independent
QA checks algebra/aggregation/provenance, not a second full-array hybrid score run;
independent dense synthetic test passed. TRAIN-only historical dev-selectedcheckpoint,
no generalization/fullchemistry/independent trainingseed claim.
Interpretation docs/esmc_projection_attribution_findings_2026-09-26.md; report
reports/esmc_projection_attribution_2026-09-26.md.

Next candidate: matched raw-to-geometry warm-start adaptation from existing raw
checkpoint, with raw continuation from same start/updatebudget to separate geometry
adaptation from furthertraining. FIRST check prior experimentcoverage, then lock one
paired protocol; NOT yet implemented/submitted/approved as a successful method.
Initial search found historical scaling/capacity protocols used fresh init, but verify
actual artifacts before concluding this combination is new. No cycle/weightsearch/data
expansion or frozen-test use. Original ESMC-600M c1/s1/K1 goal OPEN.

## 2026-09-26 20:53 HKT — Raw projection diagnostic closed: local repair costs quality/chain geometry

Previous goal turn PROGRESS; current turn PROGRESS with new measured evidence.
HPC3 CPU654473 COMPLETED0:0 in48s (4 tests passed,64 saved TRAIN predictions);
independent report/array/provenance aggregation654479 COMPLETED0:0 in1s.
Keep failed missing-test preflight654472 exit4 before numerical work; supplement
was hash-locked separately, original experimental source/data lock unchanged.

Historicalraw2048 best_train_probe32, two fixed noises, no folding networkcalls
or updates, no dev/test coordinate access. Raw -> unchanged ArticulatedOutput:
meanlDDT .549430 -> .519192; worst5mean .269416 -> .280709; meanTM .725740
andworst5TM .266323 unchanged. All64 CAmaxdisplacement0/TMchange0.
4/32 targetmean lDDT losses>.05; TM losses0/32. CAchirality .867652 ->1.0;
N_CA MAE .178591->.018481, CA_C .194712->.043353, C_O .142193->.035323A;
consecutiveCN MAE .270509->.322920A. Local repair is NOT wholechain repair.

Native64 vs independentNumPy64 max1.776e-14A; savedCPU32 vsoracle64 max2.497e-5A;
dense lDDT verificationerror0. Existing scorer FP32 atom37 mapping retained;
precisionquality sensitivity maxlDDT1.043e-6/TM0, too small to explain loss.
64 CPUprojection calls total1.341s, notGPU/end-to-end deployment timing.
Metadata/report/rows/QA hash archivechecked; predictionNPZ remain HPC3.
Report reports/esmc_raw_projection_2026-09-26.md; interpretation
 docs/esmc_raw_projection_findings_2026-09-26.md.

Decision: do not promote raw+currentprojection or expand validation/scaling now.
Existing residue-local builder preservesCA fold but changes nonCA positions and
has no coupled peptide linkage constraint. Next action: localize nonCA quality
loss and跨残基C-N mismatch before locking ONE corrective intervention. No new
weight tree, cycle increase or frozen-test use. TRAIN-only, historical dev-selected
checkpoint, no trainingreplicates/CI/fullchemistry acceptance. Goal OPEN.

## 2026-09-26 — Missing-test preflight repaired before any numerical work

Job654472 FAILED exit4 in1s: original scaling source snapshot did not contain
referenced test_articulated_output.py. No diagnostic/result directory created.
Preserved code_v1, lock.json and failed log; staged existing local adapter test
as test_supplement_v1 with manifest, SHA checked by run_v2.sh before pytest.
Replacement654473 submitted only after original job terminal and result absent.
No data/config/comparison change or duplicate training. Monitor654473, not654472.

## 2026-09-26 20:48 HKT — Saved-raw projection diagnostic locked and submitted

Previous goal turn PROGRESS: teacherweight1 follow-up closed with no joint gain.
Current turn PROGRESS: freeze docs/esmc_raw_projection_diagnostic_v1.md and code,
bind395 input files, preserve all original scaling source files; launch HPC3 CPU
job654472(debug,2CPU,16GB,30min) after empty user queue verified. Root
/data/user/shuang886/Folding/esmc_raw_projection_v1_20260926. No GPU/network forward, no new training.

Use only historical raw2048 best_train_probe32 x fixednoise12345/54321 (64files),
not current badsample selection. Best checkpoint previously selected on dev;
this is NOT independent confirmation. Project using unchanged parameter-free
ArticulatedOutput in CPUFP32, then score againstTRAIN GT; bind original metadata,
reproduce old raw scores, exact new replay, native64/NumPy64 formula<=1e-8 and
independent dense lDDT check. RecordCA/TM changes, local geometry/CN/chirality,
mean/p05/worst5 descriptive quality and per-target deltas. No bootstrap/newseeds.

Run existing adapter tests and new summary tests before diagnostic. Preserve
partial output on failure; inspect exact job before any retry. No additional dev
or frozen test use. Result pending, cannot claim projection repairs chemistry.
Original c1/s1/K1 goal OPEN; this is one bounded diagnostic, not weight search.

## 2026-09-26 20:42 HKT — Weight1 follow-up closed: no confirmed joint benefit

HPC3 jobs654107/654108/654109/654110/654313 all COMPLETED0:0. Final8192
mean dev lDDT/TM: GT .3969/.4678; teacher0.1 .3963/.4717; teacher1 .3937/.4719.
Weight1 minusGT mean lDDT -.0032 CI[-.0065,+.0002], meanTM +.0041
[-.0028,+.0112], worst5 lDDT +.0064[-.0069,+.0192], worst5TM -.0147
[-.0288,+.0026]. All four intervals crosszero: joint_gate_not_passed.
CAchirality remains1.0 but CNmae .4488A vsGT .4275A; not full chemistry acceptance.
Do not substitute selectedbest7168 or positive4096 for locked8192 endpoint.
One trainingseed, two fixednoise averages, exploratory targetbootstrap, no frozen test.

IndependentCPUQA accepted8192 updates/1792 unique outputs; GPU32 exactreplay;
all-output FP64 formula max6.99885e-13 A. Legacy crossprecision1e-4 retains
one failure (max.000297965A, lDDT/TM sensitivity0). Twelve comparison input hashes,
QA/audit/source chain, curves and PNG/PDF hashes checked; figure visually reviewed.
Observer50087 exitedsuccess. Metadata/figures archived, weights/NPZ remain HPC3.
Interpretation docs/esmc_endpoint_weight1_findings_2026-09-26.md; complete report
reports/esmc_endpoint_weight1_2026-09-26.md and acceptance.json in matching directory.

Decision: close this single-dose follow-up without extending weight search or promoting
weight1. Original ESMC-600M c1/s1/K1 quality/tail/chemistry goal remains OPEN.
Possible next bounded diagnostic: TRAIN-only existing raw outputs through existing
parameter-free geometry builder, measuring quality retention and chemistry. Proposal
only, NOT locked/submitted; do not claim projection preserves CA/TM or fixes all geometry.
Current turn PROGRESS, no blocked condition and no running jobs in this experiment.

## 2026-09-26 20:21 HKT — GPU replay audit accepted; independent CPU QA running

GPUaudit654108 COMPLETED0:0 in4:51: all1792 unique saved outputs replayexactly
in CUDAFP32, maxerror0. One legacy savedFP32 vsNumPyFP64 outlier remains,
max0.0002979649 A; nativeTorchFP64 vsNumPyFP64 difference atthatoutlier
6.99885e-13 A. Retain legacy_all_pass=false, never call the old1e-4 gate passed.
GPU audit/report hash binding checked locally. This is not yet all-output FP64
formula/metric/loss acceptance: independentCPUQA654109 nowRUNNING from20:21.

Main training654107 alreadycomplete8192, selectedbest7168. Report654110 and
curves654313 remain pending. Await CPUQA, paired8192 mean/tail/chemistryreport,
then visually inspect/archive figures. No new training, restarts or extra
interim analysis. Previous turn PROGRESS; current turn PROGRESS toGPUacceptance.
Original ESMC-600M c1/s1/K1 quality/tail/chemistry goal OPEN.

## 2026-09-26 20:16 HKT — Main training worker complete; GPU acceptance running

Main654107 COMPLETED0:0 in2:54:27. Worker report complete with8192 updates,
best_step7168, best_replay_exact true and frozen_weights_unchanged true.
All1024 selected-checkpoint full-TRAIN predictions saved. Worker metadata archived;
contract/history/training hashes match report. This closes the training worker,
not independent acceptance or the original scientific goal.

GPU projection audit654108 now RUNNING; CPUQA654109 -> pairedreport654110 ->
finalcurves654313 remain queued. Keep8192 primary endpoint; selectedbest7168
must not replace it. No interim8192 job or extra training. Next actions: finish
independent acceptance, inspect final comparisons, visually inspect/archive
curves. Mainobserver50087 tracks original chain, not extra plot654313.
Previous turn VERIFIED WAIT; current turn PROGRESS. Goal OPEN.

## 2026-09-26 20:01 HKT — Prespecified8192 updates reached; final evaluation pending

Previous turn VERIFIED WAIT; current turn PROGRESS to the locked update endpoint.
Authoritative HPC3 progress.json nowstep8192, optimization wall9346.37s (<4h cap).
Job654107 remainsRUNNING: final8192 evaluation history and worker report are not
written yet. This proves the update budget was reached, not training-job/QA or
scientific goal completion. Do not extend or submit interim8192 analysis.

Wait for scheduled final validation, selected-checkpoint replay/full-TRAIN scoring
and worker report, then existing GPUaudit654108 -> independentCPUQA654109 ->
report654110. Final plot654313 separately followsreport; explicit visual/archive
check still required. No duplicate submissions, config changes or frozen-test use.
Latest quality evidence remains7168 (no confirmed joint benefit). Goal OPEN.

## 2026-09-26 19:44 HKT — All planned interim checks complete; wait for final8192

Previous turn VERIFIED WAIT; current turn PROGRESS. HPC3 CPU7168 monitor654369
completed0:0 (3s), archived snapshot/source hashes verified. Fixed128 dev targets,
two-noise mean: GT / weight0.1 / weight1 mean lDDT .3963 / .3962 / .3974;
mean TM .4634 / .4714 / .4698. Weight1 minus GT mean lDDT +.0011
CI[-.0019,+.0042], mean TM +.0063[-.0005,+.0133]; worst5 lDDT +.0050
[-.0050,+.0144], worst5 TM +.0002[-.0089,+.0067]. All four intervals crosszero.
No joint benefit established. Prior6144 negative mean lDDT and4096 positive
lDDT must not be cherry-picked; final8192 gate, data, seed and configuration stayfixed.

All seven scheduled intermediate summaries1024..7168 complete. No new interim
job at8192 (script deliberately excludes the final endpoint). Main654107 RUNNING
7264/8192 at19:44HKT; await full worker completion then audit654108 -> QA654109
-> report654110. Post-report curves654313 must be separately checked and visually
inspected/archived; original observer50087 does not include this extra job.
Current scores are worker-history monitoring, not final independent QA. Target
bootstrap intervals are exploratory and unadjusted for repeated viewing, not
training-seed replication. Original c1/s1/K1 quality/tail/chemistry goal OPEN.
Report reports/esmc_endpoint_weight1_2026-09-26/execution/interim_7168_v1/report.md.

## 2026-09-26 19:26 HKT — 6144 comparison archived; teacher-weight benefit unconfirmed

HPC3 CPU summary654316 completed 0:0 (3s); fixed128 development targets,
two predefined noises averaged per target, snapshot and locked-source hashes
verified. Mean lDDT GT / weight0.1 / weight1.0 = .3878 / .3855 / .3791;
mean TM = .4578 / .4637 / .4603. Weight1 minus GT mean lDDT -.0087,
CI[-.0127,-.0046]; mean TM +.0024[-.0067,+.0117]; worst5 lDDT
-.0071[-.0180,+.0057], worst5 TM -.0003[-.0110,+.0096]. Weight1 minus0.1
mean lDDT -.0064[-.0099,-.0029]. No joint gain established. These remain
exploratory intermediate worker scores, not final QA or training-seed replication.

Previous turn VERIFIED WAIT; this turn PROGRESS (6144 evidence and final-curve
pipeline). Main654107 still RUNNING, latest progress6208/8192; no restart or
configuration change. Next scheduled monitor7168, primary8192 gate unchanged.
Final plot654313 pending after acceptedreport654110 and preflight654312; explicitly
check/archive it because existing observer50087 does not track this extra job.
Archive: reports/esmc_endpoint_weight1_2026-09-26/execution/interim_6144_v1.
One-step quality/tail/chemistry goal remains OPEN.

## 2026-09-26 19:23 HKT — Final learning curves queued after accepted report

Previous turn VERIFIED WAIT; current turn PROGRESS on the already requested
convergence-curve deliverable. Add only a post-acceptance CPU plot of all saved
history points: mean lDDT/TM, worst5 means, C-N MAE and CA chirality. No smoothing,
no selected-best substitution, two fixed noises averaged per target. Standard-
library scalar recomputation must match accepted final views and all common-step
paired differences within1e-12. Figures do not introduce tests or change the8192 gate.

Immutable plot_code_v1/source+manifest staged separately from original code_v1.
Reuse objective audit's isolated Matplotlib3.9.2 / NumPy1.26.4 plot dependencies;
training environment unchanged. HPC3 preflight654312 passed imports/source compile
(7s); final plot654313 queued afterok654110:654312 (1CPU/8GB/10min). Planned PNG/PDF
and hash-bound point JSON under curves_v1, not yet generated. Jobs in separate
plot_jobs.json; read-only main observer50087 loaded its original job table and
will not specifically wait for this extra plot job. Check/inspect/archive it
explicitly after main report, without restarting an observer or any training.

Main654107 RUNNING6144/8192, scheduled evaluation not yet complete at19:23HKT.
Original single-dose experiment, fixed graph/data, c1/s1/K1 and frozen-test
boundary unchanged. Goal OPEN; no new quality claim. Next monitor6144 when ready.

## 2026-09-26 19:10 HKT — 5120 interim comparison complete; earlier gain not stable

Previous goal turn VERIFIED WAIT; current turn PROGRESS. Main job654107 is
RUNNING5280/8192, validated directly through HPC3 sacct. Scheduled5120 evaluation
finished; CPU-only locked summary654294 COMPLETED0:0 in3s, snapshot/source hashes
verified locally. GT / endpoint0.1 / endpoint1.0 mean lDDT:
.3811 / .3677 / .3803; mean TM: .4635 / .4554 / .4621.
Weight1 minus GT mean lDDT -.0008 CI[-.0040,+.0025], mean TM -.0014
[-.0097,+.0066]; worst5 lDDT -.0002[-.0080,+.0072], worst5 TM +.0033
[-.0111,+.0143]. All four target intervals cross zero. The positive4096 lDDT
observation did not persist at5120; no stable joint gain can be claimed.
Weight1 vs0.1 lDDT mean+.0126[.0089,.0167], worst5+.0118[.0051,.0174], but
this secondary contrast does not replace GT control or the8192 primary endpoint.

Keep configuration, single training seed and fixed8192 gate. No earlystop, best
intermediate checkpoint substitution, teacher regeneration or frozen-test access.
Interim history scores remain provisional, not final checkpoint QA; bootstrap
intervals are target-level and unadjusted for repeated viewing. Next scheduled
monitor6144. GPUaudit654108 -> CPUQA654109 -> report654110 normaldependencies.
Report: reports/esmc_endpoint_weight1_2026-09-26/execution/interim_5120_v1/report.md.
Mutable live status .agents/memory/active_experiment_status.json; original goal OPEN.

## 2026-09-26 19:02 HKT — Scaling report closed; generalization claim narrowed

Current goal turn: PROGRESS. Historical two QA repairs complete, eight-run
matched-budget/homology report654285 complete (29s), independent stdlib scalar /
budget / pairing / harm checks654288 complete (1s):44 run-budget views and54
paired comparisons. Four focused tests654259 passed. Local analysis/report/QA
hashes verified; reports/esmc_scaling_reanalysis_2026-09-26/acceptance.json binds
accepted report only, not overall goal. Interpretation:
docs/esmc_scaling_findings_2026-09-26.md. No new training, models or test access.

At16384updates, geometry128/512/2048 devmean lDDT=.2890/.3066/.2820,
TM=.2814/.3757/.3293: no monotonic positive ladder. Geometry2048 vs512 is also
worse at8h crossing. Raw2048 has .4258/.5626 and beatsgeometry2048 by
+.1437 lDDT / +.2332 TM (mean andworst5 CIs positive) at16384, but CAchirality
only .6255, CNmae .4340A; geometry2048 preservesCAchirality1.0 but CNmae .8462A.
Do not extend tiny32 chemistry acceptance to this development dataset.
Raw2048 vsraw128 mean lDDT+.0611 yetworst5 lDDT-.0382 CI[-.0536,-.0089].
Rawquality advantage is useful evidence, not deployment readiness or universal
parameterization superiority. Fixedupdates are not equalFLOPs; wallbudgets
reported separately, missing checkpoints never replaced bybest.

Archived homology policy (aligned-residue identity, shorter coverage>=.8)
relative tomax2048 TRAIN yields strata <.3:0, .3-.5:72, .5-.8:9, >=.8:47.
No lowhomology/newfold generalization claim. One trainingseed, noiseaverages
notreplicates; targetbootstrap10000seed101 unadjusted. Intermediate history
bound by acceptedreport hashes, not independent coordinateQA at everybudget.

Next action remains finish alreadylocked teacherweight1.0, not expand methods.
At19:02HKT main654107 authoritativelyRUNNING4832/8192; GPUaudit654108 ->
CPUQA654109 -> report654110 PENDING Dependency. Read-onlyobserver50087 remains
responsible for archiving; repaircontroller83175 finished and mustnotrestart.
Latest scheduledmonitor4096: lDDTmean/tail better but TMtailunresolved; don't
change endpoint8192 or call original c1/s1/K1 quality-and-tail goal achieved.

## 2026-09-26 18:58 HKT — Both historical scaling QA repairs accepted

Control2048 CPU parts654208/654209 completed 0:0 (19:22/19:09); cosine part
654213 completed earlier. Aggregate/report654284 completed 0:0 (1:16), with
exact disjoint coverage of all4608/1024 unique outputs verified. GPUFP32 replay
error0; independentTorch/NumPyFP64 max1.83e-13/8.88e-14 A. Originalcrossprecision
1e-4 failure retained:2/1 outliers, max0.000102042/0.000107584 A; their lDDT/TM
sensitivity is zero. This is post-run precision-v2 acceptance, not an originalgate
pass or a scientific scaling success. Local report/QA/part hashes verified.
Report: reports/esmc_scaling_precision_2026-09-26.md. Repair controller83175
finished successfully; do not restart it or duplicate any repair jobs.

Eight-run matched-budget/homology analysis654285 submitted afterok654284 and is
RUNNING, immutable code_v3, four tests654259 passed. New analysis reads only old
accepted reports/history and original homology audit, never executes a model.
All8 contracts share initial weights, config, source, precision and evaluation
seeds (HPC3 metadata equality checked). Optimizer diagnostics stay separate.
Mainweight1 654107 remains RUNNING, observed4480/8192 at18:56; no dose/default
change based on interim lDDT gain or unresolved TM tail. Original goal OPEN.

## 2026-09-26 18:53 HKT — 4096-update midpoint is mixed, not a joint pass

HPC3 CPU monitor 654260 completed 0:0 (18 s), fixed128 targets and two noises
averaged per target. GT / endpoint0.1 / endpoint1.0 mean lDDT:
0.3791 / 0.3831 / 0.3898; mean TM: 0.4555 / 0.4593 / 0.4613.
Weight1 minus GT mean lDDT +0.0107 CI[0.0070,0.0145], worst5 lDDT +0.0094
[0.0018,0.0167]. Mean TM +0.0058 [-0.0037,0.0156], worst5 TM -0.0146
[-0.0310,0.0019]. Thus clearer lDDT improvement but no confirmed joint
quality/tail gain. Interim target CIs are exploratory, not training replicates
or sequentially corrected. No stopping/selection/configuration change;
main654107 continues to the locked8192 endpoint. Archive interim_4096_v1.

Scaling reanalysis source code_v3 handles both native initial-history rows
without budget_crossings and the no-eligible-homology sentinel. Four focused
HPC3 tests654259 passed; original v1/v2 snapshots and test jobs preserved.
CPU repair parts654208/654209 still RUNNING, so final eight-run comparison
must wait for their complete QA plus aggregation. Goal remains OPEN.

## 2026-09-26 — Complete the originally required scaling budget/homology analysis

Previous goal turn: PROGRESS (3072 matched monitoring accepted; repair jobs
advanced and archives/memory updated). Current main 654107 and repair CPU jobs
654208/654209 are authoritatively RUNNING; no failure or restart is inferred.

Prepare docs/esmc_scaling_reanalysis_v1.md to finish already authorized scaling
reporting, not a new experiment branch. Exact original update budgets
8192/16384/24576/32768 and wall crossings 2/4/8h; absent budgets stay missing.
Report two-noise target means, lDDT/TM mean/tails, paired target bootstrap
10000 seed101, per-target degradation, chemistry, real compute and fixed
homology strata relative to maximal2048 TRAIN. Post-hoc descriptive identity
bins are not a new split or confirmatory gate. Original aligned-residue identity
and shorter-sequence coverage>=.8 policy retained. Best/last/full-TRAIN separate;
intermediate worker history is not mislabeled independent coordinate replay.
No frozen test, new training or changes to the endpoint1.0 protocol.

New analysis code staged at HPC3 esmc_scaling_reanalysis_v1_20260926/code_v2.
Version1 tests654249 passed4; version2 explicitly handles the archived
no-eligible-homology sentinel, preserves v1, and has tests654251 submitted.
Report generation must await full repair acceptance and all eight QA records.
Archive reports/esmc_scaling_reanalysis_2026-09-26. Original c1/s1/K1 quality
and tail objective remains OPEN; no scaling success claim from best scores.

## 2026-09-26 18:39 HKT — 3072-update observation; historical QA progressing

HPC3 CPU monitor 654227 completed (3 s). Fixed 128 development targets, two
predefined noise realizations averaged per target, no best-of-K selection.
At matched 3072 updates, GT / weight0.1 / weight1.0 mean lDDT is
0.3752 / 0.3806 / 0.3814; mean TM is 0.4583 / 0.4532 / 0.4502.
Weight1.0 minus GT: mean lDDT +0.0063, target-bootstrap CI [0.0023, 0.0102];
mean TM -0.0080 [-0.0172, 0.0010]. Worst5% mean differences: lDDT +0.0034
[-0.0044, 0.0111], TM -0.0059 [-0.0180, 0.0101]. No joint mean/tail benefit
established. This is provisional worker-score monitoring, not checkpoint QA,
independent training replication or a multiplicity-adjusted sequential test.
Keep the locked 8192-update endpoint and c1/s1/K1 configuration unchanged.
Snapshot/report: reports/esmc_endpoint_weight1_2026-09-26/execution/interim_3072_v1.

Historical scaling GPU audits 654202 / 654207 completed with exact FP32 replay
of 4608 / 1024 unique saved outputs. Legacy cross-precision maxima remain
0.000102042 / 0.000107584 A, with 2 / 1 outlier outputs. Cosine CPU part
654213 completed (6:57): all 1024 outputs checked, FP64 formula max difference
8.88e-14, independent lDDT difference zero; that legacy outlier has zero
lDDT/TM sensitivity. The two control2048 CPU parts 654208 / 654209 are RUNNING.
Full precision-v2 acceptance still awaits all parts and exact coverage aggregation.
Controller 83175 remains responsible only for the planned final aggregate/report;
main training observer 50087 is read-only. No duplicate training or test access.
The original one-step quality-and-tail research goal remains OPEN.

## 2026-09-26 — Finish two outstanding scaling artifact validations in parallel

Originalscaling control2048(633798) andcosine128(633800) training completed but
cross-precision1e-4 projectionQAfailed. Userauthorizedscaling work remains
unfinished; this is artifactreacceptance only, not a newmodel/methodtree or new
training. Post-run amendment docs/esmc_scaling_precision_repair_v2.md requires
alluniqueoutputs CUDAFP32 exactbuilderreplay + nativeTorch/NumPyFP64 equivalence
atol1e-8; retain originallegacyfailures andalloldsource/data/weights/metrics/loss/
mask/trainingmembership checks. Olddirectories readonly, newreports separate.
Sourcecopy mustmatch ALLoriginalfiles; newlock hashes originalartifacts+newcode.
No foldingnetwork calls, optimizerupdates, testaccess or teacher cachegeneration.
HPC3 root: esmc_scaling_precision_v2_20260926; local archive:
reports/esmc_scaling_precision_2026-09-26. Lock 654201 and CPU partition lock
654206 completed. GPU cosine128 654207 passed exact replay of all 1024 saved
outputs; original cross-precision failure remains recorded (max 0.000107584 A).
GPU control2048 654202 is still running. Full CPU checks are not yet accepted.

Resource amendment: debug MaxTime is 30 minutes, so the initial 90-minute
request was rejected without creating a job. Frozen cpu_validation_v2 splits
control2048 into 2330/2278 unique outputs by group hash, with cosine128 retaining
one 1024-output part. CPU jobs 654208/654209 depend on the 2048 GPU audit;
cosine CPU job 654213 is running. Exact disjoint coverage is mandatory before
aggregation. Numerical gates, inputs and scientific scope are unchanged.
Controller session 83175 submits only missing planned CPU/aggregate jobs, waits
on debug's five-submission quota, and never retrains, restarts or cancels jobs.
Metadata: controller.json, jobs.json and status.json in the repair archive.

At 18:34 HKT, weight1 training 654107 is healthy at 3328/8192 updates. Scheduled
3072 evaluation is complete; its CPU comparison waits for a debug submission
slot. Existing audit/QA/report dependencies remain queued. Overall goal OPEN:
ESMC-600M, MSA-free, all heavy atoms, c1/s1/K1; no new method or frozen-test use.


## 2026-09-26 — Weight1.0 preflight passed; main GPU worker RUNNING on HPC3

CPUlock654105 COMPLETED0:0:5focusedtests passed, original255sourcefiles andpinned
controls accepted. GPUpreflight654106 COMPLETED0:0 in59s onACD1-25: longest
backward finite, teacher gradients reachfront/decoder, actualtrunk1/structure1,
zero optimizerupdates. Maintrain654107 RUNNING onACD1-25 (start17:21:48HKT); all256initialraw/projected
predictions+metrics exactlymatchedGTcontrol beforeupdates. Verifiedstep2240/8192 at18:11HKT,
finiteGT andteacherlosses, lr1e-4,2738.9s optimization time; weight1.0 active.
Earlyread-onlyHPC3 dispatchcheck acceptedfirst64updates: sameorder/noise/lr/sample
counts across3arms; first4GTlosses identical; teacherterm .491736678→4.917366782,
EXACT10x. Evidence execution/dispatch_audit_v1/acceptance.json. CurrentGPUmodel
NVIDIA H10080GBHBM3 matchesbothcontrols; driver610.43.02 recordedseparately.
No extraGPUexperiment, changedweights, or new scientificconfiguration.
GPUaudit654108 -> independentCPUQA654109 -> report654110 dependencies queued.
Exact256initialGT-controlreplay PASSED before the firsttrainingupdate. Read-onlyobserver
execsession50087 active; archive reports/esmc_endpoint_weight1_2026-09-26.
All304acd_ue GPUs wereallocated atresourcecheck; queuestart estimateschange and
are not ETA guarantees. Priorworker~3h; earlycurrentthroughput suggests~3–4h plusQA~15min (GPUauditqueue extra).
One newdose only; priorGT/0.1 controls+teacher reused. c1/s1/K1 unchanged; no
frozen-test access. Scopeprotocol docs/esmc_endpoint_weight1_v1.md. GoalOPEN.
Previous goal turn VERIFIED WAIT. Current turn PROGRESS:2048 scheduledmonitor
CPU654178 COMPLETED0:0(2s), snapshotarchived(interim_2048_v1). GT/0.1/1.0
meanlDDT=.3736/.3751/.3781; meanTM=.4458/.4460/.4474. Weight1vsGT lDDTmean
+.0045 CI[+.0011,+.0081], TM+.0016[-.0074,+.0110]; worst5lDDT-.0015
[-.0090,+.0075], TM-.0073[-.0214,+.0062]. No jointmean/tail benefit established.
Exploratoryworker scores, not finalQA or trainingseedreplication. Keep8192endpoint
and configuration. Main654107 live; nextscheduledmonitor3072. GoalOPEN.

Reconciled historicalscaling: all8jobs terminal; raw2048(633804) COMPLETED0:0
and independentQA/report hashes accepted. OldRUNNING tablefixed. Best22528 of
24504updates; devmeanlDDT .53745/TM .69673, macrochirality .80926, CNmae .28192A.
Retain as usefulreference but chemistry notdeploymentready; dataset/budget differ
from512endpointpilot, no representation-superiority/newfoldclaim. Lightmetadata
archived andhashed, notallNPZ redownloaded. control2048/cosine128 finishedtraining
but originalprojectionQAfailed1e-4; theirprecision-separated reacceptance remains
outstanding. Do not inheritendpointQA verdict. No newGPUjob or trainingtree.
Report reports/esmc_scaling_2026-09-19.md and reconciliation_2026-09-26 artifact.

## 2026-09-26 — Single teacher-weight1.0 follow-up locked for HPC3

User said continue. Prespecified docs/esmc_endpoint_weight1_v1.md: ONLY add1.0T
arm from originalcontrol512 parent; reuse acceptedGT-only/0.1 controls andteacher
cache. Same512TRAIN/128dev, inputfeatures, graph, GTloss, AdamWreset/lr/clip/order/
noise, c1/s1/K1,8192updates or4hsoftbudget. No tailweights/recycle/data expansion
or frozen test. Gradientdiagnostic12%-18% influence motivates dose test, not a
claim that strongerteacherwillwork. Beforefirstupdate require all256initialdev
raw/projected predictions+scores toexactlymatch oldGTcontrol. New schema andsource
snapshot; original files/lock/results immutable. Precision-v2 QA locked before run.

Primary8192 endpoint−GT: bothmean(lDDT,TM) andworst5means musthave pairedbootstrap
CI lower>0 for exploratoryjointquality/tailgate. Secondaryvs0.1; no intermediate
checkpointselection tochangegate; missing8192 meansbudgetunmet. Geometry reported
separately, no claim finalgoalachieved evenifthisqualitysubgatepasses.5focusedtests
plannedHPC3; GPUpreflight/train/audit thenindependentCPUQA andreport dependencies.
Archive reports/esmc_endpoint_weight1_2026-09-26; rootHPC3
/data/user/shuang886/Folding/esmc_endpoint_weight1_v1_20260926. Submissionpending.


## 2026-09-26 — Objective audit and report fully archived; one-step goal remains open

All required objective-audit jobs terminal COMPLETE0:0: tests653945(3passed),
GPU653946/653947/653948, offlineplotsetup653980, report653981, verification653982.
Accepted report reports/esmc_endpoint_objective_2026-09-26.md; authoritative
execution/report.md, analysis.json, figure.png/pdf, report_validation.json bound
by hashes; jobs/accounting/status archived. Added docs/progress_2026-09-26.md.
Cross-runtime recomputation(nativeNumPy2.1.2 vs isolatedplotNumPy1.26.4) agreed
within1e-12 for paired mean/P05/worst5 CIs;3 known-answer bootstrap cases passed.
Plot deps isolated, never used for training. Failedreport653975 and cancelled
online setup/report653977/653978 retained; no diagnosticGPUjob repeated.
Previous pending figure/package/session notes below are now historical, superseded.

Scientific outcome unchanged: bounded endpoint0.1 pilot did not confirm mean+tail
recovery. Full-gradient teacher influence~12%-18%, generally aligned; does not
prove a stronger weight will help. Next single hypothesis is stronger terminal
supervision from the same start at matched updates with GTcontrol; no new training
submitted this turn. No multi-cycle default, method-tree expansion, frozen-test
access, or local experiment. All experiments remain HPC3-only; overall goal OPEN.
This goal turn is PROGRESS: new48 gradient cases plus accepted analysis and docs.


## 2026-09-26 — Completed endpoint objective attribution; no quality-recovery claim

Previous goal turn classified progress: implemented precision-separated QA repair.
This turn verified643804/643805/643806 COMPLETED and archived accepted pilot outputs.
Both students8192 updates, best=last. endpoint−GT mean lDDT−.000565(CI crosses0),
TM+.003870(CI crosses0); paired worst5 lDDT+.00413/TM−.00668, both CIs cross0.
11/128 devtargets degrade>0.05 in at least one metric vsGT-only. train512/dev128
lDDT GT=.6101/.3969, endpoint=.6119/.3963. Teacher c1_s1/c4_s2=.8200/.8486;
ESM2teacher vsESMCstudent includes pretraining/weights differences, not a clean PLM
attribution. Original cross-precision1e-4 check still failed; precision-v2 passed.

HPC3 focusedtests653945 passed3; zero-update full-gradient jobs653946/653947/653948
all COMPLETED0:0 (~110s each, total .0914 allocatedGPUh). ExistingTRAINprobe8 by
length, two noises, initial/GTfinal/endpointfinal; no test access. All32finalprobe
predictions bit-exact replay, all3weightsunchanged. Weightedteacher/GT fullparameter
norm median(initial/GT/endpoint)=.1217/.1764/.1215, cosine=.5967/.3500/.4430,
negativecos0/1/1 outof16, no GT ascent along negative combined Euclidean gradient.
No evidence of a widespread gradient break/conflict; teacher is modest auxiliary.
Last512steps all clip10; preclipmedian119/132. Do not infer AdamW updates or a
causal generalization fix from these Euclidean, preclip,8target diagnostics.

Docs: docs/progress_2026-09-26.md; protocol docs/esmc_endpoint_objective_audit_v1.md.
Archive reports/esmc_endpoint_objective_2026-09-26. No new training launched.
Next bounded hypothesis: stronger teacher endpoint influence at same initialweights
and updatebudget, retain GTcontrol and joint mean/tail gates. No recycle expansion,
no new objective tree, tail weighting, or frozen test. Overall one-step goal OPEN.

Numerical supplement completed; report653975 failed only missingmatplotlib after
writing numbers. Onlineplotsetup653977 was live but networktimedout; cancelled it
and its pending report653978 deliberately, no GPU diagnostics rerun. Offlinewheel
fetch in local session59255 is package retrieval only; all numerical work remains
HPC3-only. Figure/report finalization pending; preserve failed/cancelledjobhistory.


## 2026-09-26 — Endpoint pilot closed; bounded objective attribution next

Verified sacct: precision QA643804/643805 and report643806 COMPLETED0:0. Both
students finished8192 updates (16 new exposures), best=last8192. Final paired
endpoint−GT lDDT−.000565 [−.003817,+.002772], TM+.003870 [−.003024,+.010661];
no confirmed mean+tail recovery. Teacher c1_s1/c4_s2 dev lDDT .8200/.8486 vs
students~.396; do not claim one-step quality goal achieved. Precision-v2 QA passes,
original cross-precision1e-4 gate remains failed. Light archive refreshed fromHPC3;
all original pilot jobs terminal, historical RUNNING observer entries superseded.

Next: zero-update objective audit, docs/esmc_endpoint_objective_audit_v1.md.
8 TRAIN probes chosen from original32 by length positions2,6,...30 before gradients;
initial + GT-final + endpoint-final, two fixed noises,3 concurrentHPC3GPUs atmost
30min each. Full trainable gradient norms/cosines, module and raw/builder output
attribution; final predictions exact-replayed, hashes locked, weightsunchanged.
No new training/method tree, tail weighting, frozen-test access, or local experiments.
Archive reports/esmc_endpoint_objective_2026-09-26. Submission IDs pending.


Updated: 2026-09-26

## 2026-09-23 — Endpoint report dependency failure: precision-separated QA repair

Both training jobs643267/643269 COMPLETED8192updates; original CPUQA643268/643270
FAILED at saved CUDA FP32 vs independent NumPy FP64 projection maxabs<=1e-4.
Report643271 was DependencyNeverSatisfied, then cancelled/replaced by643806.
HPC3 diagnostic643793/643794 checked1536uniqueoutputs per arm. CUDAFP32 raw-to-
articulated replay is bit-exact for all. Cross-precision outliers4(GT)/1(endpoint),
max2.63158e-4/1.17462e-4 A; nativeTorch64 vsNumPy64 outlier errors<1e-14.
Raw pose/torsion probe perpendicular norms~.0015-.0034 A explain conditioning.
No retraining, altered predictions or relaxed original threshold. Original
cross-precision gate remains failed. Explicit post-run QA amendment separates
FP32 artifact exact replay from FP64 formula equivalence(atol1e-8), preserving
all original data/source/checkpoint/metric/loss checks and legacy failure records.
New validators643804/643805 running; new report643806 afterok both. All onHPC3.
Read-only observer restarted as session8415; old4988 exited on original failure.
New files stay in precision_validation_v2; originalcode_v1 immutable. Report:
reports/esmc_endpoint_projection_failure_2026-09-23.md. Final quality remains
pending full independent QA; do not call legacy original acceptance passed.
Other esmcA/esmcB formal jobs seen in queue belong to other work, left untouched.

### 2026-09-22 — Endpoint pilot: teacher and GPU preflights accepted; training running

Teacher768 predictions accepted by643264. All8 shards complete. GPU preflights
643265/643266 both COMPLETE0:0 in66sec; endpoint teacher loss has finite nonzero
gradients to ESMC projection and decoder. Actual core calls remain1trunk/1structure.
Training jobs643267(gt_only) and643269(endpoint) RUNNING; first they repeat preflight
and initial dev evaluation, then optimize. CPUQA643268/643270 and finalreport643271
afterok dependencies remain. No final scientific result yet. Read-only observer
exec session4988 updates reports/esmc_endpoint_2026-09-22.{md, directory/status.json}.
Do not duplicate this observer or any active job. All future experiments HPC3-only.

## 2026-09-22 — Endpoint distillation pilot authorized; HPC3-only experiments

User approved trying one-step terminal supervision and requires all subsequent
experiments on HPC3. Protocol docs/esmc_endpoint_distillation_v1.md; literature
review docs/one_step_quality_recovery_literature_2026-09-22.md. No GPU experiments
or tests run locally. HPC3 lock643255 passed3 focused tests and pinned accepted
control_512/best.pt plus unchanged512TRAIN/128development data. Two matching
continuations: GT-only vs GT +0.1 full-canonical teacher terminal aligned MSE,
all student folding trunk/decoder trainable, ESMC frozen, c1/s1/K1 and existing
articulated geometry retained. Reset identical AdamW, lr1e-4;8192updates or4h
optimization/evaluation budget,7h reservation. This bounded warm-start pilot is
not proof of convergence and is not formal consistency trajectory training.

Teacher fixed Protenix-Mini ESM2-3B c4_s2/seed103/K1; only sequence input.8GPU
shards643256..643263 generate512TRAIN terminals and128paired c1_s1/c4_s2 dev
references (768predictions), QA643264. Missing GT remains masked; teacher is
separate pseudolabel, not student input. Preflights643265/643266; matched train
643267/643269; CPUQA643268/643270; paired report643271. Strict afterok dependencies.
Authoritative jobs.json in reports/esmc_endpoint_2026-09-22. Root HPC3
/data/user/shuang886/Folding/esmc_endpoint_v1_20260922; sourcecode_v1 immutable.
No tail weighting or test-based selection; remaining frozen test untouched.

HPC3 queue was empty before submission. Old scaling jobs have all terminated:
633798(control2048) and633800(cosine128) FAILED;633804(raw2048) COMPLETED, so older
local RUNNING/observer entries are stale. No old run restarted/cancelled here.
Current endpoint teacher work pending/running; do not duplicate. Archive and
check preflights before claiming either student training is active.

## Historical status — Stage0 minimal confirmation completed and accepted

All 2,304 formal K=1 predictions completed and passed scoring/source/execution QA:
1,536 repeats (128 targets, seeds 103/107/109/113, three settings) and 768 locked
confirmations (256 new targets, seed127, same settings). No best-of-seed or
configuration expansion. All three prespecified directional claims confirmed.
Confirm mean TM/lDDT: c4_s5 .8966/.8450, c4_s2 .9016/.8528, c2_s2 .8957/.8456.
c4_s2 vs c4_s5 mean lDDT +.00776; c2_s2 vs c4_s2 −.00724, paired geometric
warm time ratio .585 (41.5% less), but 13/256 TM losses >.05. Near-zero mean
c2_s2 vs c4_s5 does not imply tail equivalence. c4_s2 leads both mean metrics
in all four repeat seeds; old c4_s2 tails did not reproduce, c2_s2 tails partly did.

HPC3: 16 shards per phase; per-user GPU quota16 with8 existing scaling jobs
meant at most8 concurrent confirmation GPUs. Total 1.612 GPU-hours including
preflight/diagnostics; first prep to final QA 36.1min; confirmation inference
span5.05min. Jobs634046/634068 completed; no Stage0 work remains pending.
Final report reports/stage0_confirmation_2026-09-19.md; authoritative artifact
archive reports/stage0_confirmation_2026-09-19/{jobs.json,accounting.psv,execution/}.
Remote /data/user/shuang886/Folding/stage0_confirmation_v1_20260919, code_v2
actual inference/evaluation; initial code_v1 and failed preflight preserved.

Final lock preceded frozen metadata read. Selected256 are disjoint from all1024
dev and now scored; remaining2184 coordinates unused by this experiment.
Deterministic kernels passed atom-exact plain/plain and hook/plain preflight;
original MC/sampler unchanged, fixed features and per-target seed resets differ
from old A800 sequential RNG protocol. MC branch off for103, on107/109/113/127.
These are conditional K=1 findings, not proof of arbitrary sampler superiority
or scratch generalization. Existing8 scratch scaling jobs/observer continue;
do not duplicate or cancel. Overall research goal remains open.

## 2026-09-19 — Scaling-v1 generalization ladder declared and submitted

User explicitly prioritizes generalization scaling128/512/2048 with rawcontrol,
fixedvalidation, matchedcompute/convergencecurves, isolatedLRdiagnostics andno
frozen temporaltest. Corrected: rawCapacity-C650 passedchemistry; tinysetcapacity
alone doesnotprove extra recycle/diffusionsteps uselessforgeneralization.
Protocol docs/esmc_scaling_v1.md. Maximal2048TRAIN plus128fixeddevelopmentval,
32..256residues, fromexisting16000pre-cutoffmetadata. Originalexact-group14400/
1600split reconstructed(seed101), matchedaccepted32TRAIN/64val. Excludeprevious64
fromnewval; trainprefix32acceptedanchors thenhashranknested128/512/2048. Every
selected(sample,group) verifiedpre-cutofftrainmanifest anddate<=2021-09-30.
Frozen temporalmanifests/coordinatesnotread. Nearhomologynotdeduplicated; existing
Biopythonidentitypolicy auditsthe128val against32/128/512/2048trainprefixes.
No homology-basedsplitmodification, no novel-foldclaim fromaggregatevalidation.

CPU preparation633766 COMPLETE0:0 in8:39: all2176packets,16shards, eachrawmmCIF
rebuildexact, ESMCexact, independentobservedmask/atomnames, CCDcanonical/terminal
bonds, NumPyprojection andadapterdirectionalFD. ACDCPU-onlyarray rejected;
debug16CPUrequestexceededQOS. ActualoneCPUdebugjob4CPUs/48G,4parallelworkers,
zeroGPUs. Sourcecode_esmc_scaling_data_v1_20260919(89files). CPUaggregatehash/
homologyaudit633794 currentlyRUNNING; dataacceptance gates GPUjobs.

Trainingcode_esmc_scaling_v1_20260919(98files), unchangedacceptedcore/loss/adapter.
Sixmainrunsgeometry/raw×128/512/2048, plusgeometry128lr3e-4constant andgeometry128
cosine1e-4to1e-5. Sharedfreshseed101,1cycle/1structure/1sample,frozenESMC,
A+.1F+R+10D,AdamWwd1e-4clip10. Mainlr1e-4constant. Max32768updates OR8h
optimization+scheduled-evalwall;12hSlurmallowsfullfinaltrain/valandCPUQA.
Noearlysuccess/plateaustop. Fixedcheckpoints8192/16384/24576/32768updates;
2/4/8hwallcrossings, actualsamples/residues/train/eval/workerwallcostrecorded.
Evaluateevery2048updatesonfixed128val and32TRAINprobe. Best=maxworst-noise
macrovalallatomlDDT,earliesttie; fullTRAINevaluatedatselectedcheckpointatfinish.
BudgetlimiteddoesNOTmeanconverged; equalupdate andequalwallcomparisonsseparate.

lDDTper-atommean excludesintraresiduepairs; observedreference<15A,.5/1/2/4A.
TM-align usesfixedobservedsequencealignment via tmtools0.3.0 (isolated
scaling_eval_deps_v1, wheelstagedandbinaryhashbound). NoKabschTMproxy. Missing
coordinatesneverimputed. Validationneverusedinbackward,includingGPUpreflight:
longestTRAINbackward, longestVALforwardonly. TwoGPUzero-updatepreflights gates.
Fournewfocusedtests andlintpass. No temporal/confidence/longsequence/fullESMCcost
claim. Do notchangeoldaccepteddata/modelsource snapshots.

Observer exec72060 ACTIVE: scripts/finish_esmc_scaling.py --archive
reports/esmc_scaling_2026-09-19. Sourcearchivedsource/observer. Readsqueue,archives
terminalnoncheckpointartifacts,checksQA/hashresults,plotscurves,comparesfixedupdate
budgets andpairedproteinbootstrap. Noautosubmit/restart/cancel. Do notduplicate.
All GPUtrainingjobs submitted but dependency-pending atthisrecord; authoritative
jobs.json and completion_workflow.json inlocalarchive.
- data_prepare: 633766 (cpu_prepare)
- data_acceptance: 633794 (cpu_acceptance)
- preflight_control: 633795 (preflight)
- control_128: 633796 (train)
- control_512: 633797 (train)
- control_2048: 633798 (train)
- control_128_lr3: 633799 (train)
- control_128_cosine: 633800 (train)
- preflight_raw: 633801 (preflight)
- raw_128: 633802 (train)
- raw_512: 633803 (train)
- raw_2048: 633804 (train)

Originalresearchgoal remainsopen; thesearedevelopmentexperiments.

## 2026-09-19 — Capacity-C COMPLETE: both 32-protein arms PASS

Ten training jobs plus two zero-update preflights all COMPLETED0:0 and accepted.
Observer77137 finished, completion_workflow.json complete/all_accepted=true,
HPC3 userqueue empty. No restart/repeatedQA/newtraining in this status check.
Current c1 articulated model PASSES original32 jointgate at400exposures/protein
(12800updates): worst-noise pooledatom0.915022405 A, pooledCApair0.537686926 A,
CN0.281202511 A, hand100%,32/32<2A atbothnoises,23/22<1A; worstprotein1.12644A.
Raw32 PASSES at650exposures(20800updates): atom0.652113031A,CApair0.466689680A,
CN0.297326982A,hand100%,32/32<1A atbothnoises,worstprotein0.907597A.
Elapsedcontrol32=3:04:53,raw32=3:21:55. ReportsSHA respectively
80d362b752b0d6f64c5bdd72a7963ac3c1a470fc112ed5f26adc6e1b35ecd116 and
23107e312ba1eedc70664164ffa3c91e1d5686c7fe213e0f82a449e3143efc2e.

Critical correction: control32 at100exposures EXACTLY reproduces all64 old
per-example/noise metrics AND geometry dictionaries. Its pooledatomcurve is
100:3.77099858,200:1.66552182,300:1.12895577,400:0.91502241 A. Same architecture,
loss and schedule with larger predeclared optimization budget passes. Old100epoch
failure does not establish incapacity/rawgauge/decoder bottleneck. Raw atmatched400
atom0.91603270 A is almost identical, but jointgeometryfails; don't rank final
0.652vs0.915 as a matched-budgetrawwin. Currentarticulated mainline is justified
byearlier32jointgate; oneproteinrawspeedwin didnotuniversallytransfer.

Control4 passes550exposures atom0.803956831A; raw4 passes400 atom0.676073414A.
Bothall4<1A. Raw4hand99.26/99.75%,not100%. Newrawsingle0/7/31 allstrictpass:
600/.443846881,650/.459209442,700/.456502289(exposure/atomA).
Controlsingle31 passes1000/.476241022; single0 and7 hit1000budget withoutstrict
<.5gate: best950/.571759701 and900/.500294089. AllartifactQAaccepted is not
allscientificgatespass. Differentsetsizegates prevent comparingstoptimesas
intrinsicdifficulty. Oneinitialization,twoevaluationnoises,TRAINonly; noheldout,
calibratedconfidence/longsequence/fullESMCcost claim. Originalresearchgoalopen.
Report/curves reports/esmc_capacity_c_2026-09-19.{md,png}; accepted_analysis.json
records old100exposure equality and matched400raw comparison. Nextstageplanning
canproceedfrompassedcapacitygate; requirepredeclareddata/budget/evaluationprotocol.

## 2026-09-19 — Capacity-C exposure-controlled parallel wave declared

User approved starting the exposure-aware comparison and maximizing informative
parallel GPU jobs on HPC3. Protocol docs/esmc_capacity_c_v1.md: ten training jobs,
control/raw each for size4 and32 plus six singleton controls at indices0,7,31.
Four-set indices[0,7,15,31] chosen from existing length-ordered TRAIN32 metadata;
reuse accepted index15 singleton rather than retraining it. Fresh sharedseed101,
unchanged c1 model/loss/optimizer, max1000exposures per sample, evalevery50,
per-group/exposure noise and Random(101+epoch) order. No plateau stop. Size32
retains original joint geometry/pooledRMSD/>=29-of-32 gate; size4 requiresall<1A
plus pooledgeometry; size1 retainsstrict<.5A. Selectminimumjointnormalizedscore.
Timecensored runs do not establish matched-exposure failure. Total optimizer
updates/weightdecay differ across setsize and must be reported alongside exposure.
Two zero-update GPU preflights precede the tenjobs with afterok dependencies.
Sixfocusedtests+lint pass; new32jointscore exactly reproduces acceptedold3.77099858.
Source snapshot code_esmc_capacity_c_v1_20260919; localarchive
reports/esmc_capacity_c_2026-09-19/source/execution_v1. Capacity-C submitted on HPC3. GPU preflights632721/632727 completed0:0 in1:30/1:27,
64initialpredictions/longestgradient checked, zerooptimizerupdates. Latest checked: seventrainingjobsRUNNING, threerawsingletonjobsPENDING
(Resources/Priority); both32 and both4 jobsRUNNING. Sixearlyjobs alreadyhave
optimizerupdates; raw4 was started45seconds later. Observerstate/report nowwritten.
Historical launch status: observer exec77137 was active; it has now completed (see latest entry).
It retries startup rsync until outputfolders exist, copies livehistory/progress,
archives terminal artifacts, checks CPUQA/localhashes and renders report/curves.
Observer source archived in source/observer; noautomatictrainingresubmission.
Jobs (authoritative specs: reports/esmc_capacity_c_2026-09-19/jobs.json):
- preflight_control: 632721 (dependency none)
- control_32: 632722 (dependency 632721)
- control_4: 632723 (dependency 632721)
- control_single0: 632724 (dependency 632721)
- control_single7: 632725 (dependency 632721)
- control_single31: 632726 (dependency 632721)
- preflight_raw: 632727 (dependency none)
- raw_32: 632728 (dependency 632727)
- raw_4: 632729 (dependency 632727)
- raw_single0: 632730 (dependency 632727)
- raw_single7: 632731 (dependency 632727)
- raw_single31: 632732 (dependency 632727)
Selected lengths for indices0/7/15/31 are35/105/128/166residues.
Immutable snapshot83files, includes acceptedcore/loss unchanged. No accepted
Capacity-B or old32 artifacts modified. All originalprojectgoals remainopen.

No broadergrid,heldoutuse,warmstart,teacherinput oracceptedsource mutation.

## 2026-09-19 — Capacity-B first wave COMPLETE and accepted

All five final HPC3 jobs completed 0:0; independent CPU QA, exact GPU best
replay and local report hashes passed. Completion observer finished; no remaining
first-wave jobs or observer need restarting. This supersedes running/pending
status in the historical entries below.

| Arm | Job | Best update | Worst-noise atom RMSD (A) | Strict joint gate | Slurm elapsed |
|---|---|---:|---:|---|---|
| control | 632527 | 950 | 0.483115584 | True | 00:14:23 |
| raw | 632528 | 650 | 0.401894391 | True | 00:07:48 |
| allframe | 632529 | 1000 | 0.496017247 | True | 00:15:01 |
| oracle | 632553 | 1600 | 0.505524874 | False | 00:10:38 |
| c4 | 632549 | 850 | 0.486812383 | True | 00:17:06 |

Oracle stopped at its 1600-update budget; one noise RMSD=0.505524874 A misses
strict <0.5 A, while both noise cases pass <1 A and the separate geometry
thresholds. All arms have 118/118 chirality agreement at both evaluation noises.
QA acceptance is artifact correctness, not equivalence to a scientific gate pass.

The original c1 articulated core and raw XYZ both memorize this TRAIN128 example
below 0.5 A. Whole-protein SE(3) gauge is not established as the blocker: existing
losses are invariant; prior raw-representation Jacobian conditioning is distinct.
Allframe shows no clear improvement here; c4 reaches the gate in fewer updates
(850 vs 950) but more elapsed time (17:06 vs 14:23). No replicate significance
or universal architecture ranking follows from one protein/one initialization.
Oracle is native-shaped free conditioning, not a compact ID oracle, and c4 uses
last-cycle-only gradients. Direct frame/torsion head was not tested.

Critical next control: old 32-protein/3200-update run saw each protein only 100
times, versus 650–1000 exposures for passing single-protein arms. At 100 exposures
single articulated RMSD=4.23531 A versus 3.82787 A for the same protein in the old
32-protein run. Neither multi-protein interference nor sufficient optimization
budget is established. Next stage remains a predeclared exposure-aware 4/32
comparison; no larger training or new jobs were launched during this status check.
Report and curves: reports/esmc_capacity_b_2026-09-19.{md,png}; per-arm immutable
reports/QA and source snapshots are archived in the matching directory.

## 2026-09-19 — First Capacity-B result ACCEPTED; four arms still running

RAW XYZ job632528 COMPLETE0:0 in7:48; strict_single_pass at650updates, best650,
worker440.42s. IndependentCPUQA and localarchivehashchecks PASS. Seed12345/54321
atomRMSD0.39788556/0.40189439 A; CA-distance0.22102907/0.23184045 A;
CN0.21657091/0.22558273 A, allthreeotherbondRMSEs<.10 A;
hand118/118 atbothseeds. All6initial/best/lastpredictions fixednames/maskschecked,
GPUbestreloadexact, independentlyrecomputedRMSDmaxerror6.54e-7 A. ReportSHA
e995bfa4cd8e0d2571ed7e660bacc7cc7a7d692599804a0271f6d63776429172.
This establishes one scratchc1/rawXYZ/decoder canfitthisTRAIN128proteinbelow.5A;
no generalization,32-setcapacitypass or architectureuniversalclaim.

CRITICAL budgetcomparison: prior32TRAIN3200updates meant100exposures/protein;
newraw1proteinneeded650updates/exposures. Raw1at100=3.49244A. Articulated1at100
=4.23531A vs sameprotein inold32articulatedepoch100 worstseed3.82787A. Thus
currentevidence doesNOTestablish multi-proteininterference or rawXYZincapacity;
per-exampleoptimizationbudgetmustbecontrolledin4/32followups. Do not blindly
attribute improvement/failuretoSE3gauge or increaseepochswithoutdeclaredcomparison.

Current activejobs: control632527(v1),allframe632529(v1),c4_632549(v2),
oracle632553(v3). All nowpassed actualtraininggradientandinitialreplay checks.
Oracle632548(v2)stoppedbeforeanyupdatebecauseanoverstrictcheckdemandedall3native
conditionshavenonzeroinitialgradients. v3preservesoriginaldecoderrequires_gradflags,
includingfixedFourierfeatures; initialconditionnorms[0,0,.00155437]afterclip are
allowedwithnonzerocombinednorm. Byupdate94all3conditiongradnormsnonzero
[.30375,.27167,.02291]. No disconnectedoraclepath. v2blanketdecoderunfreezewas
correctedbeforeanyoptimizerupdate; v2failedsource/outputpreserved.
Currentoraclecode code_esmc_capacity_b_v3_20260919(77files), output
esmc_capacity_b_oracle_v3_20260919. Other3activejobsnotrestarted.

Oldobserver99560 deliberatelyterminated(143)tochangetheoraclejobID. Only current
completionobserver exec66294 remainsRUNNING: scripts/finish_esmc_capacity_b.py
--archive reports/esmc_capacity_b_2026-09-19 --jobs same-directory/jobs.json.
Do NOTstartanotherobserver orrerunQA/training. Itarchivesallterminaljobsandgenerates
finaltable/curves; allacceptedstatusincompletion_workflow.json. Previousobserver
statepreserved ascompletion_workflow.previous_observer.json. Failedoracle_v1,
c4_v1,oracle_v2 anddispatchauditlogs/sources arelocallyarchived. Executionv1/v2/v3
manifestsareseparatelypreserved; observeractualsourcearchivedbeforelaterreportwording.
Preliminaryreport/curve reports/esmc_capacity_b_2026-09-19.{md,png}currentlyshows
onlyacceptedrawresult; remainingarmsstillrunning/unaccepted. Finalreportwillupdate.
Threefocusedtestsandlintpass. .summaryandmemoryupdated. Four/32-stage remains
conditionalonfullfirstwaveQAandnewpredeclaredbudget/control; fullprojectgoalopen.

## 2026-09-19 — Capacity-B dispatch failures isolated and repaired

Three original arms continue unchanged: control632527/raw632528/allframe632529.
Original oracle632530 FAILED0updates in59s on initialreplay; c4_632531 FAILED0updates
in1:07 on firstbackward(checkpointmetadatamismatch). Preserve allv1sources/outputs.
No accepted training was restarted and no failed-arm optimizer update occurred.

GPU diagnostic632537 measured exactoracleconditionvalues but51.5996Aoutputdifference
anddifferentRNG; native one-rowsequence-onlyMSA sampler consumesCPU/CUDARNG. v2
reproduces onlysample_indices(n=1)fororacle and restores first-cycleRNGbeforedecoder
forc4. No evolutionaryMSA orGTinputadded. C4 no-grad earlycycles contaminateautocast
weightcache; disablingcache preservesBF16 and finalcycle-onlygradientpolicy.
632537 obtainednonzeroESMCgradient withcacheoff. Confirmatory632547 COMPLETE0:0:
oracle frozen/unfrozen exactoutput (max0), CPU/CUDARNGexact; c4CPU/CUDARNGexact,
c4initialoutputmax0, c4backwardfinitewithfrontgrad0.7948399. Neither auditupdatesweights.

Replacement training oracle632548/c4_632549 submitted with immutable77-file
code_esmc_capacity_b_v2_20260919; outputs esmc_capacity_b_{oracle,c4}_v2_20260919.
Originalworkingarmssnapshotv1(76files) unchanged. Sameinputs,loss,optimizer,budget;
nohyperparametersearch. GPUpreflight/realtraininggradientforreplacementjobsstillpending.
ThirdfocusedCPUtest nowconfirms existingfullobjectiveSE3invariance and covariant
gradients/equalnorms, threefocusedtestsandlintpass; originalv1testsourcepreserved.

Local read-only completion observer exec99560 is RUNNING, scripts/finish_esmc_capacity_b.py,
reports/esmc_capacity_b_2026-09-19/jobs.json fixesfiveacceptedattemptIDs/versions.
It never submits/restarts; archivesafterterminalstatus,requiresreport/CPUQA/hashchecks,
generatesreports/esmc_capacity_b_2026-09-19.{md,png}; completion_workflow.json tracksstate.
Do not launchduplicateobserver. Initialfailedattempts andtwoauditlogs retained separately.
No newcapacityresult accepted yet; all tiny-set results remainpendingQA. Update this
state on actual completion, then decide controlled4/32followups/directposehead.

## 2026-09-19 — Capacity-B first wave submitted at user request

User explicitly requested parallel tiny-set / decoder-oracle / frame / recycle
diagnostics before scaling. Protocol docs/esmc_capacity_b_v1.md supersedes earlier
single-intervention restriction. Five independent HPC3 H100 jobs submitted:
control632527, raw632528, allframe632529, oracle632530, c4_632531.
Source code_esmc_capacity_b_v1_20260919 (76-file verified manifest); outputs
esmc_capacity_b_{control,raw,allframe,oracle,c4}_v1_20260919. Initial GPU preflight,
training, final CPU QA and results are PENDING; submission is not acceptance.

Same index15 TRAIN128 group36e538543c24414069b77ac1a24e0597ea526b6c77eb19f02ef2c671db700f37,
selected by length/order only; no held-out data. Fresh shared init101/baad41,
1600 updates max,45-minute soft optimization/65-minute hard job,AdamW1e-4 wd1e-4
clip10,batch1,dropout0,BF16trunk/FP32decoder+adapter,TF32off,1NFE/1sample,
confidence frozen/off. Shared varied training noise; eval12345/54321 every50.
Primary best selection lowest worst-noise atom RMSD; desired<.5A,minimum<1A,
chemistry tracked independently. Early stop only atom<.5 plus original geometry
criteria; no plateau stop or autoextension. CPU QA runs with CUDA hidden after
training in same job. Exact best replay and hashes required before conclusions.

Corrections to causal premise: current A is Kabsch-aligned, F/R are proper-local-
frame losses and D distance, so existing supervision is already SE(3)-invariant.
Prior3–4x sensitivity is redundant raw internal coordinates, not globalrotation.
Articulated adapter already preserves fixed chemical geometry; this is not a
new direct-frame/torsion head. allframe changes ONLY F coverage15A->allobserved
frame/point pairs with same squared loss/.1coefficient, not canonicalclampedFAPE.
Oracle learns native-shaped s_inputs/s/z initialized from freshc1 (noGT), bypasses
and freezes upstream, trains same scratchdecoder+adapter; permissive conditioning
oracle, not compactIDembedding. c4 retains native final-cycle-only gradients;
not fullyunrolledcapacityupperbound. Failures do not prove structuralimpossibility.

Two focused CPU tests (fullframe masks/invariance/gradcheck;oracle nativevalue and
upstreamdisconnection) and lint/shellsyntax pass. Acceptedmodel/adapter/lossfiles
unchanged. New helpers src/fastglycan/capacity_b.py;trainer/validator/Slurm
scripts/*esmc_capacity_b*.py/.sh. 4/32-protein, directpose/torsionhead and deeperc1
remain conditional followups requiring results/QA/newprotocol, not automaticgrid.
Original full onecycle/allheavy/confidence/heldout/ESMCinclusivecostgoal remainsopen.

### Previously accepted findings

User-requested detailed gradient/root-cause report COMPLETE:
reports/esmc_articulated_root_cause_2026-09-19.{md,png,json} (Chinese report).
HPC3 CPU632468 COMPLETE0:0 in54s (4CPU16GB/noGPU, actual37.58s) covered128
initial/selected × two-seed saved-coordinate cases. GPU632473 COMPLETE0:0 in1:27
covered selected100 TRAIN35/166 with seed12345, actual four weighted losses and
combined parameter gradients. No optimizer update, retraining, held-out access or
full-length rerun. No live jobs/observers for this audit; do not repeat it.

Independent QA PASSED: NumPy projection max3.20e-14 A, scalar1.37e-12 A²,
three-factor VJP additivity4.92e-14 relative, independent central FD max5.48e-8,
GPU/CPU coordinate gradient max1.81e-6; BF16 parameter sum mismatch0.434%/0.371%.
Exact saved raw/adapted and train/eval replays; weights/features/adapters unchanged;
actual1trunk/1structure/0confidence. All75CPU/71GPU source files and128 coordinate
NPZ gradient artifacts, parameter Gram matrices, logs/accounting/hashes verified.
Two focused tests include factor additivity, translation identity, structural
zeros, Gram conflict and positive-scale invariance/Jacobian scaling; lint passes.

Confirmed computational mechanism: positive per-residue radial scale about CA is
invisible to output/loss but rescales orientation/internal Jacobians by1/s while
nondegenerate. All60,944 actual nonzero residue/loss radial derivative checks
maxrelative3.12e-13. Final median-of-case median rawCA-C0.546 A, N-plane0.552 A;
smallest perpendicular scale0.006855 A (above1e-4, so zero fallbacks is not proof
of well-conditioned derivatives). Same-output retracted-coordinate counterfactual
changes weighted raw gradient norms by median ratios A3.092,F3.785,R3.155,D3.959;
output error<=7.24e-14 A. Retraction changes raw lengths AND shapes: do not attribute
all3–4x to uniform scale alone. Adding another differentiable projection to the
existing graph leaves the composite chain rule unchanged; not a demonstrated fix.

Final64 factor norms (A/.1F/R/10D): translation .523/.161/~0/.575;
orientation4.21/4.76/~0/3.19; internal3.38/.344/2.60/~0. R cannot train rigid pose;
10D's fixed intra-residue distances plus C–N cannot train internal angles. About
16.31% raw atoms are structurally unused by probes; their zero direct gradients
are expected.88 unobserved raw atom entries have gradients through probes, while
unobserved final-output label gradients are zero; no missing GT was introduced.

Final64 negative-total directions: output harms no component; raw harmsF1/R4,
retracted harmsnone. Initial raw harmsR32/64. Actual global parameter directions
lower all4 losses in both audited cases; no general loss-conflict/ESMC-disconnection
claim. Combined ESMCprojection norms73.673/60.863, Pairformer58.838/58.444,
atomdecoder371.035/294.379. Component A/F/R/D norms35:229.45/109.14/288.61/66.90;
166:156.81/122.98/91.11/97.69. Clip10 scales.02364/.02907 do not establish effective
AdamW learning-rate reductions; no optimizer-history step was simulated. Shared
parameter subgroups can have local conflicts despite globally descending direction.

These facts establish parameterization sensitivity and supervision coverage, not
proof that removing scale freedom alone resolves the failed capacity gate. Next
research action: design one bounded scale-freedom intervention or explicit latent
pose/internal parameterization, verify unchanged expressivity/GT-free inputs and
stable derivatives, then predeclare one controlled comparison if justified. Do
not launch a loss grid, extend632192 or simply compose the projection twice.
No new architecture/training protocol has yet been selected. Original full
ESMC/all-heavy-atom/confidence/calibration/held-out/full-cost objective stays open.

CPUreportSHA ea9eba241d6fb481a25e1262206293698c647ef89bb08941a89e5fc147b3cc2f;
GPUreportSHA08cfaed9a3fb23093523bd8270f75dc1470427821d072a6cbe0cf7ec89f0379f;
QAsha2bdb8705280b100eaa80c0c7679ca027b95f1021938934e3b4fa3e68adf982f8;
Chinese reportSHA3d2617f5cff4f42944c8f623f7a795e9403ae261eeabb63fbf0244151cb4bdd4.
Local archives reports/esmc_articulated_trace_{cpu,gpu}_2026-09-18/; actualcode
code_esmc_articulated_trace_{cpu,gpu}_v1_20260918 and matchingoutputroots onHPC3.
Final-analysis source and report/QA uploaded; actualexecution snapshots unchanged.

## Previously accepted training (next actions superseded above)

HPC3 training 632192 COMPLETED 0:0 in 47:09. All 100 epochs / 3,200 updates
finished; stop=epoch_budget, selected epoch=100. Observer exec 39881 finished 0;
independent heavy CPU QA and local archive verification pass. No live training or
completion observer remains for this experiment. Do not repeat training/final QA.

Two seeds 12345/54321: atom RMSD 3.770999/3.765907 A, CA RMSD
2.644914/2.649466 A, CA-distance RMSE 2.434685/2.440849 A, consecutive C–N
RMSE 1.070060/1.072503 A. N–CA/CA–C/C–O errors 0.021327/0.046526/0.039083 A;
handedness 100%, but 0/32 proteins have atom RMSD <=2 A. Joint score 3.770999
fails the <=1 capacity gate. No extension, checkpoint promotion or larger-data
training. This rejects this candidate/budget, not every articulated architecture.

Selected comparison improves atom 4.180549 -> 3.770999 A and joint score, but
selection epochs differ (Cartesian 75 vs articulated 100). At shared epoch 95,
Cartesian atom 3.508625 vs articulated 3.968887 A; joint score 7.136072 vs
3.968887; C–N 1.145933 vs 1.126853 A; handedness 64.32% vs 100%. Do not claim
faster coordinate fitting from the selected-checkpoint comparison.

All64 selected raw+adapted replays exact; all128 raw->adapted CPU reconstructions,
original inputs/frozen heads/adapter buffers and heavy checkpoint checks pass.
All128 local predictions, 93 execution source files, QA sources, report/contract/
history/curve hashes verified. Fallback counts remain zero. Maximum independent
adapter error 3.90319e-5 A, metric error 3.18230e-6 A; frame/same-residue/distance
scalar errors 2.21857e-4/6.45825e-7/4.29960e-5 A². Peak training allocation
2,963,639,808 bytes (~2.760 GiB) on the short subset; model-work time 2798.40 s.
Neither is a full-length or ESMC-inclusive inference benchmark.

Post-acceptance CPU shape diagnosis completed on all64 selected predictions:
free proper per-residue GT poses leave RMSD 1.025592/1.023123 A, about 7.40%/7.38%
of global SSE. Centroid errors 2.876009/2.869440 A; centered internal errors
2.439057/2.438927 A (these include orientation). Pose correction removes much
error, but internal shape remains inaccurate relative to accepted articulated
attained inverse fit 0.150398 A. Cached rigid-reference floor is 1.046758 A.
These GT-dependent corrections are diagnostic only, not inference, an orthogonal
physical energy decomposition, a model-gradient attribution or proof of learnability.
No earlier inverse fits or GPU forwards were repeated. Saved observed-only64
artifacts/source hashes checked; diagnosis uploaded to HPC3 and SHA verified.

Report/curves/archive: reports/esmc_articulated_capacity_2026-09-18.{md,png,json}
and directory; pose/shape report in that directory/articulated_shape_diagnostic.md.
Report SHA 57c9863836acf674202d7e4100299a1c11c5cca07fb83964d0ebf797c3b86379;
QA SHA 2acd2fbb6a6ded9fefefc7ce697b508f42bed943a0d8f784baa110da733a6cb9;
diagnostic SHA 417d898652f67f35da3f229b8605b65c6597ba4c13b0a5b73dbbd35a8a1c03d2.
Best checkpoint SHA 9d71fd4820032ec52d2893c1ed18291f9da4fa3fe2ef1ff982c7c826f75060fb;
last SHA 73cc35346d65fd4e089edf2d3d76c7ad90ffc7d3f3c2e121d3bddb84185472a8.
Large checkpoints remain on HPC3; hashes checked by heavy QA. Worker log, Slurm
accounting, local_archive_acceptance.json and completed workflow are archived.
Code/output: code_esmc_articulated_capacity_v1_20260918 /
esmc_articulated_capacity_v1_20260918; preserve immutable execution sources.

Next: before another training configuration, define a bounded saved-coordinate CPU
sensitivity diagnostic of actual loss gradients through raw->articulated output,
with the original labels/masks and fixed coefficients. It should distinguish
coordinate-level evidence from parameter/AdamW behavior and check derivatives
numerically. No new weight choice, architecture or GPU experiment is declared yet.
Original frozen-ESMC/no-MSA/all-heavy-atom/one-cycle/one-structure/confidence/
calibration/formal-held-out/full-ESMC-cost objective remains unfinished.

## Prior accepted work (execution plans superseded above)

GT-free articulated output interface and actual-core CUDA audit632148 COMPLETE0:0 in1:21; independentCPUQA passed. No live jobs or optimizer updates. Source/output code_esmc_articulated_output_v1_20260918 / esmc_articulated_output_gpu_v1_20260918. Fresh unchangedcore hashbaad41,35/951 TRAIN inputs, actual1trunk/1structure/0confidence, exacttrain/eval +35rawinitial replay, unchangedweights/features/adapterbuffers. ESMCgradientnorm15.87618/3.08475, finalprojection19870.01/19608.74, rawgradient55.60486/12.59380;413nonzeroparametertensors each. Longestpeak47.156825GiB (short1.100345), fallbackcounts0. Adaptertimings0.21846/0.06132s are singlecold/warm audit measurements, not a latency benchmark or fullESMCcost. Confidence remains frozen/disabled; eventualhead must consume finaladaptedcoords.

IndependentCPU observed-label/mask/source/hash/scalar/NumPyoutput/FP64 raw-gradient QA passes: outputmaxabs1.18e-5 A, projectedgradientmaxrelative2.87e-7, rawgradientmaxrelative1.74e-7, NumPycentralFDmaxrelative4.94e-10. Projectedlossgradientszero outsideobservations; raw gradients can legitimately reach unobserved predicted probe atoms, though these2caseshave0. No missingGTlabels introduced. InitialCPUvalidator stopped on Tensor/NumPy subtraction beforeacceptance; corrected explicitNumPy conversion, same unchangedGPUartifacts/tolerances, noGPUrerun. ReportSHAa91dea42d8b96a606cfcf6fa0a30a8f97c83e8f3006e64daa42f3c836f482995; QAsha8c52bdd57b6b19e52f69e31cca1640a5024c0dd2e7ca0c47d7c0556114384c48 uploaded/remoteverified. reports/esmc_articulated_output_gpu_2026-09-18.md and directory includes actualexecution/QA source,2caseschemicalrefs/GT/labels/raw+adaptedcoords+gradients,log/accounting/hashes/completedworkflow. Do not repeat accepted audit/QA.

CPU interface report07d2b5f5ebdca0c2d4b9193ca989adc49cc16ff6a6fa557d8accbf271a85e8e2: reports/esmc_articulated_output_2026-09-18.md and directory/source/128projectedpredictions, copiedHPC3 esmc_articulated_output_cpu_v1_20260918. All32chemicalinputs/3,979residues/36variants generatedreconstruction FP64max1.64e-14 A/FP32max7.15e-6; idempotence/geometrystable; saved35/166coordinateFD<8.1e-10relative;zero128fallbacks. Parameter-free grouped ArticulatedOutput in src/fastglycan/articulated_output.py uses onlychemicalreferences/inventory/sequence/pinnedCCD andpredictedNCA/Cpose+fixedprobedihedrals, noGTfittedangles/poses/targets/masks. Explicitworldbasisfallforcollapsedframes is finitebutnotrotation-equivariantatdegeneracy. Six focused builder/fit/outputtests andlint/shellsyntaxpass. Do not alteracceptedcore/model/loss sources.

Deterministic postprocessing selected631937 makesworstatom4.18055->4.66058 A andseed12345CN1.14195->1.93888 A, despiteNCA/CAC/CO .021/.047/.039 A and100%CAhand. CApositionsandCAmetricsunchanged. This is not a trainedgain, checkpointpromotion orgatepass. Needlearnthroughinterface.

Next controlledtraining is declared docs/esmc_articulated_capacity_v1.md, NOT yet implemented/submitted: addonlyauditedparameter-free outputadapter to accepted631937 fresh32TRAIN training; sameinit/inputs/labels/loss atom+.1F+R+10D/optimizer/seeds/precision/budget/dualseedjointgates/stop. Require64rawinitial exactbaseline matches and64adaptedinitial CPU maxabs<=5e-5 A; save raw+adaptedinitial/selected coordinates, exactselectedreplays, unchangedinputs/frozenheads/adapters and finalheavyindependentCPUQA. Adaptergeometry largely fixes3distancecategories but coefficientskeptunchangedtoisolateinterface. Logfallbackswithoutchanginggates; finalvalidator must supportdeclaredfallbacks ifencountered (currentauditNumPyhelpercoversnondegeneratecasesonly). No warmstart/grid/extraepochs. Next action implement isolatedtrainer/control/validator/report/observer/Slurm andlaunchsingleHPC3H100 aftercontrolchecks; no permissionneeded. Full originalfrozenESMC/noMSA/all-heavy-atom/onecycle/onestructure/confidence/calibration/formalheldout/fullend-to-endcostobjective remainsunfinished.

## Earlier accepted work (next-action text superseded above)

Articulated observed-GT inverse fit632103 COMPLETE0:0 in56s onHPC3 debug, actual4CPU/12GB/noGPU. Initial acd_u CPU-only submission was rejected because that queue requires GPUs; explicit debug partition override succeeded, no change to solver/data/budget. Worker used4 independent protein processes and96,262 objective evaluations under declared2-start/80iteration/200hardfunctionevaluation limits; one unsuccessful start retained with best actual evaluation, no retries. No network forward/weight update/heldout read.

Independent NumPy saved-angle/pose/geometry/mask/identity/hash/spectral-pose QA PASSED on32 TRAIN groups/3,809 observed residues/30,437 observed atoms. Pooled attainable all-atomRMSD0.150397917 A versus rigidfloor1.046757701 A; macro0.149195575 A;32/32 proteins<=1 A. Maximum coordinate replay2.84217e-14 A, reference geometry preservation3.48610e-14. Local NCA/CAC/CO RMSE0.021327/0.046526/0.039083 A; consecutiveCN0.093335 A. Eligible CA3579/3579,ILE_CB198/198,THR_CB219/219 hand agreement. Original target masks/names fixed; no missing target fitted/imputed. Independent residue poses are permissive and do not enforce chain connectivity/clashes; low CN residual here is diagnostic only. Numerical attained errors are upper bounds on representation minima, not proven lower bounds or trained quality.

Four focused builder/fit tests plus lint/shellsyntax pass. Source/output code_esmc_articulated_fit_v1_20260918 / esmc_articulated_fit_v1_20260918. ReportSHA8f3c5bb84e265641eb3649a1828b0f753d8f3173c9ffb13e06d0ba7b8ef640e8; QAsha41a9bc4907186708dd7a3b4943d27755c36330f11b82bc624a6074b69efb1af4 uploaded and remoteverified. Local reports/esmc_articulated_fit_2026-09-18.{md,png} and directory includes all32observed coordinate/angle/pose artifacts, accepted reference hashes, actual execution/QA sources, workerlog,Slurmaccounting and completedworkflow. ActualQA source archived; subsequent line-wrap-only formatting in working script does not change its accepted archivedsource. No live jobs or duplicate QA; do not rerun the completed fit.

Next: implement and test a GT-free articulated output interface using only chemical references/inventories and predicted pose/internal-angle information, before more model training. Candidate bridge from current Cartesian decoder: derive residue pose from predicted N/CA/C and internal rotations from fixed-name predicted dihedrals; reconstruct constrained reference coordinates. First verify exact reconstruction on generated admissible coordinates, proper-motion equivariance, missing-label independence, degeneracy handling and usable gradients. This extraction choice is a proposed interface candidate, not an accepted learned architecture or a declared training experiment. The GT-aware inverse-fit solver/angles/poses must never be inference inputs. If CPU interface checks pass, perform a bounded actual one-trunk/one-structure CUDA gradient/memory/replay audit onHPC3 before a single controlled training comparison. Preserve original frozenESMC/noMSA/all-heavy-atom/confidence/calibration/formalheldout/fullend-to-end cost objective, still unfinished. Parallelize only necessary independent work; no speculative loss/model grid.

## Earlier accepted prerequisites (next-action text superseded above)

Fixed-graph articulated-reference prerequisite completed on saved32 TRAIN references, without GPU or GT fitting. Native CCD20 blocks streamed/pinned on HPC3; fullassetSHA bb31ae5cf6c8bc669924313077cb4231ee5ffefd3a20118cd14f3ec89f8bb6a5, subsetSHA fef99e421ab902dde026627fefe32138f006f49a3f9e3711d24a31b1ff87a73e, manifestSHA734d07bf5cba4e931f13e17b0bd7ec767ce3a02967e8ae7f42f4e2b0583d3cf2. Installed ccd.py/configs_data.py and actual extraction source archived; full pickle not loaded. Extraction used stdlib bounded streaming on HPC3; local compact-reference checks used1CPU/noGPU.

Implemented src/fastglycan/articulated_reference.py: deterministic single-bond bridges oriented away fromCA, excluding N-CA and empty distal branches, proper Rodrigues rotations of full distal components in root-to-leaf order. Rings are uncut; carbonylCA-C and sidechain rotations allowed, branches rotate together, no renaming/reference-as-GT. It is a geometry representation, not an energy model; amide single-bond bridges are not assigned torsional barriers. Independent residue poses still do not enforce peptide connectivity. Two focused branched/ring/chirality/equivariance/gradient/invalid-input tests and lint pass.

All3,979 chemical residue inventories (36variants/20AA) map with matching names/elements, connected CCD-induced graphs and fully valid references. Earlier3,809 count was residues with observedGT; no target-mask expansion. Zeroangles exact identity; bond-length/cosine/rigidcomponentdistance errors<3e-15FP64; maxcentralFDgradienterror5.73e-9 on all36variants. Eligible reference/GT handedness matches CA3579/3579,ILE_CB198/198,THR_CB219/219; rotations preserve signed volumes. All32 saved-reference hashes and archived/current execution source hashes checked. Diagnostic reportSHA82b1a7f10bc32f46fe33e11ae0df5e2a5df18c9a2045e1d653d567e862ac960d; reports/esmc_articulation_2026-09-18.md and directory, uploadedHPC3 esmc_articulation_v1_20260918. Graph archive reports/esmc_ccd_graphs_2026-09-18 / remoteesmc_ccd_graphs_v1_20260918. Protocol docs/esmc_articulated_reference_v1.md. No new model, GT inverse fit or GPU training has run.

Next declare a bounded numerical observed-GT inverse-fit solver/budget before executing it, using these pinned graphs and original masks. Attained fit error is an upper bound on the representation's minimum, not a proven lower bound. Only after adequate representability/geometry/derivative evidence consider integrating a constrained output into the fresh ESMC core. Do not rerun accepted diagnostics or launch speculative parallel training. Parallelize independent necessary CPU fits/checks when worthwhile; prefer HPC3. The full original ESMC/all-heavy-atom/confidence/heldout/one-evaluation/end-to-end cost objective remains unfinished; no live jobs.

## Prior accepted results (next-action text superseded above)

HPC3 distance-supervised run631937 COMPLETE0:0 in38:19;95epochs/3040updates, declared plateau20 stop, selected75. Independent heavy CPU QA and local execution/QA/history/all128 prediction hashes pass. Jointscore4.180549>1: seeds12345/54321 atom4.180019/4.180549 A, CA3.017095/3.015147 A, CA-distance3.438506/3.444098 A;0/32atom<=2 A. NCA0.241248/0.238837,CAC0.273451/0.270179,CO0.246484/0.247216,CN1.141953/1.139095 A; hand79.60/79.80%. Same-residue MSE5.455444/5.432639 A², unweighted distanceMSE0.367587/0.365370 A². No extension/promotion/scale-up or automatic loss-weight grid. This rejects this candidate/budget, not every Cartesian architecture.

All64initial matched and64best replays exact; actual1trunk/1structure/0confidence, unchanged inputs/frozen heads;peak2,962,043,904B (~2.759GiB) on shortsubset. QA maxcoordinate2.71315e-6 A,frame0.000239914,same-residue0.000102223,distance0.0000630593 A². Observer83638 finished0/completion_workflow.complete; no live project jobs. No duplicate final QA/observer. Sourcecode_esmc_distance_capacity_v1_20260918/outputesmc_distance_capacity_v1_20260918. ReportSHA8ff68aef2e56d801ce64b1736ab50c4525ff03451090bcd179de1ab5bfe500ab; QAsha43fbe1747e490b4939a6c59237fbaa80294dc96148c64cd1d695bcaf16bcecc9; bestSHA07ffe81827dc063b92075af87483e6dd098ecbb703cb42bd5d8ba96c780e0a36; lastSHA55c573e5af9d8c1e5cb78e2defca7498597ff2f04c1dcc238fe05030eb92848d. Reports/curves/archive reports/esmc_distance_capacity_2026-09-18.* and directory; current actual reporting source archived separately from immutable execution.

Latest-common-epoch reporting corrected to retain an equal-update comparison even when selected epochs differ beyond baseline duration. At shared55, previous631737 versus distance631937: atom3.590827->4.877475 A, CN3.763924->1.388851 A, hand87.3149%->91.5060%, jointscore12.546414->4.877475. Selected35 versus75 is not faster coordinate fitting. Last95 atom3.508625 A but jointscore7.136072, so preserve selected75. Reporting-only change, live/training/QA sources unchanged.

Post-QA independent CPU shape and B-versus10D diagnostics completed concurrently using saved selected64 coordinates, no extra GPU forwards. Residue radii1.153833/1.152367 A versus GT2.196170; centroid3.382608/3.383475 A, centeredinternal2.455712/2.455421 A, ~34.5%SSEinternal. Two-seed disagreement0.303489 A does not establish correctness. B=actual atom+0.1globalframe+same-residue,10D uses actual distance coefficient. MacroB41.4582/41.3692 and10D3.67587/3.65370 A²; median coordinate normratio10D/B0.275084/0.279323,cosines0.124584/0.103722. Negative combined coordinate gradient locally lowers both in64/64 cases; no parameter-gradient/AdamW claim. No coincident distance pairs; analytic distance-gradient error1.49e-16/additivity1.07e-16. ShapeJSONsha9fc91cbd2e09a6a167dcfc62ad853dabc22b21f429b306c7706a12ef545a82a1; balanceJSONsha c1ecd92d45969217baf92a5c4c0f25760ae17fe7c1c587408cb52cefaf068d95. Both uploadedHPC3 and remoteSHAverified. Balance report/source reports/esmc_distance_balance_2026-09-18.*. Old frame-only attribution now refuses distance-weighted contracts; never omit D from the recorded objective.

SpareCPU reference diagnostic631937.0 accepted separately:1CPU/20s/noGPU, all32TRAIN30,437 observed atoms. Exact cached conformers under independently optimal proper per-residue poses have pooledfloor1.046757701 A,30/32protein floors>1 A. Independent saved-reference QA matches8.49e-15 A; reportSHA40909d6dee6f23e5b8f2e0abb542922dafa97e3ff1068324c888e05c54f597e4,QAshab12b023b79cb15771dacbfeb432fe2190be6d5482ec1235e243ed590836264ba uploaded+verified. Reports/source/32ref+GTmask+observedfit artifacts: reports/esmc_reference_shape_2026-09-18.* and directory. Original input/feature/GT/label hashes checked byworker; localQA doesnotreloadheavyfeatures. It is a GT-dependent lower bound without chain-connectivity constraints, not folding inference. Do not train a head restricted only to rigid transforms of these exact cached residue conformers. Internally flexible/torsion heads are not ruled out. Two focused tests/lint pass; six installed runtime source files archived.

Next research action: inspect/pin the fixed CCD residue connectivity and test an articulated reference-coordinate builder with internal bond-axis rotations, proper poses, preserved rings/atom identities/missing masks and explicit handedness checks, before allocating another model-training job. First establish whether that representation can fit the fixed observed GT accurately and has usable derivatives; do not substitute reference coordinates for GT or claim numerical inverse fits are global lower bounds. This is a proposed feasibility direction, not an implemented/newly accepted architecture or a new GPU training protocol. Current failure and persistent internal shrinkage justify testing structural constraints; they do not prove the existing model can never learn them. No new job submitted. Original frozenESMC/MSA-free/all-heavy-atom/one-cycle/one-structure/confidence/calibration/formalheldout/fullcost objective remains active and unfinished.

## Earlier accepted evidence (historical execution plans superseded above)

Distance audit631888 COMPLETE0:0 in1:40, actual73.951s, no updates. All4cases exact saved/train-eval replay, unchanged model/features,1trunk/1structure/0confidence, peak2.320608GiB. Independent CPU label/scalar/FP64gradient/moment/module/source/artifact QA passes; maxcoordinategradient relativeerror7.60276e-7. Initial35/166 andbest35/166 D/B parameter ratios0.403610/0.427366/0.171419/0.084900; cosines+0.864597/+0.949296/+0.210103/-0.037071. Negative actual unitprobe gradient locally decreases both losses in4/4cases; no AdamW/quality claim. Reconstruction0.0078–0.5481%; no coincident distance pairs. ReportSHA3428d1af5978de4b132ee8a01e0bc6cba4adbfa6a1bc8485f8aad36450a24587; QAsha95183056d6162beedb4ef63f5305f6dcdeb104427111fa5c0157e8e48ccb5ec6 uploaded and remotely verified. Full report/heatmap/4case/source/QA archive reports/esmc_distance_gradients_2026-09-18.* and directory. No live audit/duplicate QA.

Next controlled training declared docs/esmc_distance_capacity_v1.md and implemented: add10*D to accepted631737 loss, all other controls unchanged. Coefficient10 chosen once from saved TRAIN parameter scales (trained ratios1.714/0.849 after arithmetic rescaling; initial4.04/4.27 with positive cosines), not a measured weight10 backward or quality optimum. Samefresh32/init/sampler/optimizer/precision/budget/dualseed gates/stop; require64initialmatches and final independent heavy/four-scalar/geometry/selection QA. No grid/warmstart/scale-up. Four-component logging does not alter selection summaries.14focused tests/lint/shellsyntax pass; actualmatchedcontract and pinned distance-loss source verified. Immutable code_esmc_distance_capacity_v1_20260918 prepared with execution/validation/reporting/observer; outputesmc_distance_capacity_v1_20260918 now running as631937. Original goal remains open.

HPC3 same-residue capacity run **631737 complete 0:0 in20:18**; independent heavy CPU QA and local execution/QA/history/all128 prediction hashes pass. Stopped55epochs/1760updates by declared plateau rule; selected35. Jointscore9.232090>1, both seeds fail: atom7.725098/7.710630 A, CA-distance7.330022/7.302640 A; NCA0.7686/0.7706, CAC0.8620/0.8636, CO0.6714/0.6718, consecutiveCN2.7479/2.7696 A. Handedness88.71/87.93%,0/32 atom<=2 A. Compared with accepted631592 at the same selected epoch35, handedness improves from~51%, but worst atom error worsens7.1880->7.7251 A. Do not extend/promote/scale up this configuration.

All64 initial controls and64 selected replays exact; inputs/frozenheads unchanged,1trunk/1structure/0confidence; peak2.759GiB for shortsubset. QA metric/frame/same-residue maximum discrepancies2.713e-6 A/0.000239914 A²/0.000102223 A². Observer59184 finished0; no live631737 job or duplicate QA. ReportSHAeb1ee70815f0b6c009879a1db6ea0f6f07c6c4d27b6549ca6928c7b81f746cbb; bestSHA0dd13b6c2b0171636ece7d7edbfc3d701f6227d7abc27c55ea49fbdc6207101a; lastSHAeda28c5f555206c62ee66d6173545a8a5fe1085c7b4dda72167c68ae30a2d2ed. Source/output code_esmc_local_capacity_v1_20260918 / esmc_local_capacity_v1_20260918. Report/curves/archive reports/esmc_local_capacity_2026-09-18.* and directory.

Independent saved-coordinate shape and recorded-weight frame attribution ran concurrently on CPU after final QA, without GPU forwards. Residue radii1.1771/1.1779 A versus GT2.1962 A (accepted631592~1.47 A), centroiderror7.3134/7.2979 A, centeredinternalerror2.4883/2.4888 A; seed disagreement0.652556 A. Same-residue contribution is22.55/22.58% of actual geometry scalar and median same/cross coordinategradient ratio0.7178/0.7622. Direct FP64 weighted-gradient reconstruction relativeerror2.56e-15; NumPy scalar8.53e-14; no frame anchors hit norm floor. This is coordinate-gradient evidence, not parameter/optimizer attribution. Saved reports/esmc_frame_attribution_local_2026-09-18.* include actual diagnostic source. Do not repeat accepted diagnostics.

GT-only observed-distance sanity on same32TRAIN targets:3774 consecutiveCN pairs mean1.330538 A,std0.009775 A,range1.255854–1.402533 A. This narrow target distribution does not explain several-A predicted CN error; no broader chemical-quality claim. JSON/source in reports/esmc_local_capacity_2026-09-18/gt_distance_diagnostic*. No new labels/masks/gates.

Decision: local supervision improved handedness but did not recover correct local distances or global structure; actual geometry contribution is no longer negligible. A further coefficient grid is not justified by these diagnostics. Next research step must distinguish missing explicit distance constraints from limitations of the unconstrained Cartesian output, with a bounded predeclared diagnostic before more training. No next GPU run is yet declared/submitted. Original ESMC/all-heavy-atom/one-evaluation/confidence/heldout/full-cost goal remains open. Parallelize only independent necessary checks or experiments, reuse accepted artifacts, and prefer HPC3 for GPU work.

## Historical context (execution plans superseded by current status above)

Same-residue network-gradient audit631704 COMPLETE0:0 in1:36, actual audit78.25s,
no optimizer/update. Initial/best35 x35/166 TRAIN,seed12345; exact saved-coordinate
and train/eval replays, actual1trunk/1structure/0confidence, unchanged model/input
hashes. Global parameters121,673,521 in1,361tensors; each component1,354present,
413nonzero atinitial and1,347atbest. Peak2.320580GiB on short inputs.
Independent CPU source/artifact/GT/scalar/FP64 coordinate-gradient/moment/disjoint
aggregation QA passes; maximum coordinate derivative relativeL2 error4.49399e-6
versus predeclared1e-3. Full parameter gradients not archived/CPU does not repeat
GPU network backward.12focused tests/lint/shellsyntax pass. No live project jobs.

R is separately normalized existing same-residue frame supervision; B is existing
atom+0.1globalframe, P=B+R unit derivative probe. Global R/B parameter norm ratios
initial35/166:0.788504/0.672400; best35/166:0.777374/0.233012. Coordinate ratios
2.652052/2.198787/0.677495/0.802088. Parameter cosines+0.549901/+0.541551/
-0.095414/+0.074413. Actual negative P gradient locally decreases both scalars in
all4cases, not an AdamW/finite-step or trained-quality claim. Reconstruction errors
0.000110851/0.000082137/0.00656946/0.00613369, mixed-precision effects measured.
Best ESMC projection ratios0.353/0.0964; atomdecoder1.26/0.703; all module gradients
covered. No geometry gate improved merely by this audit.

Accepted reportSHAbe50f3383d595fec58dc74aab7c35d79dbdb6cfc5d3782589a5127316f2c2c63;
remote code_esmc_local_gradients_v1_20260918/outputesmc_local_gradients_v1_20260918.
Local reports/esmc_local_gradients_2026-09-18.{md,png,json} and directory include
4casecoords/labels/coordinategradients/parameter moments/source/QA/log/preflight;
all execution/QA/artifact hashes verify, heatmap inspected. QA uploadedremote.
No duplicate audit or new initial/selected forwards needed.

Next experiment predeclared docs/esmc_local_capacity_v1.md: add unit same-residue
frame MSE to existing atom+0.1globalframe loss, fresh matched initialization and
same32inputs/noise/shuffle/optimizer/precision/budget/dual-seed joint gates as631592.
Require accepted631592+631704 provenance and64exact initial predictions before
optimization. No warmstart, grid, new labels/imputation, new thresholds, epoch
extension or scale-up. Unitweight chosen for comparable measured parameter scales,
not optimum/quality proof. Separately log all3terms; independent CPU heavy/FP64/
scalar/geometry/selection/stop QA required. Implementation/launch pending.
Original ESMC/all-heavy-atom/one-cycle/one-structure/confidence/heldout/full-cost
objective remains active and unfinished.

Controlled coefficient0.1 run631592 COMPLETE0:0 in18:28; observer76770 finished0,
completion_workflow.complete=True. Independent heavy CPU/source/GT/FP64/local-
geometry/selection/stopping QA passes; local execution/QA/128prediction/curve hashes
verified. All64initial matches and64best replays exact, inputs/frozen heads unchanged,
actual1trunk/1structure/0confidence. Peak short-input training2.758617GiB. Stop at
45epochs/1,440updates under unchanged plateau20 rule; selectedepoch35. No extension.

Selected seeds12345/54321 atom7.186252/7.187972 A, CA6.511313/6.514956 A,
CA-distance6.115377/6.114417 A; zero/32 atom<=2 A. NCA0.850417/0.857001,
CAC0.959899/0.961490,CO0.918181/0.921468,CN2.828913/2.840415 A;
handedness51.24/50.68%. Jointscore9.863090>1, limiting54321handedness: failed gate.
Old0.001 selected25 score10.586732/atom9.112429 improves at the protocol-selected
checkpoint, but stopping/selected epochs differ; same-epoch atom fit is not faster
(e.g.epoch35 old6.938849 versusnew7.187972 A). Higher coefficient lowers C-N errors
but does not restore local geometry/handedness. Last45 atom5.304211 A has worse
score10.296021; do not substitute last weights or promote/full-data train.

Final report/curves/compact archive reports/esmc_geometry_capacity_weight01_2026-09-18.*
and directory, plus _comparison.png. Remote outputesmc_geometry_capacity_weight01_v1_20260918,
sourcecode_esmc_geometry_weight01_v1_20260918, QAcode_esmc_geometry_weight01_validation_v1_20260918.
ReportSHAff534b92b7f3275aac03bd4ccd02a574f0eee3c02edaf67d036a9edcfccfd8d9;
bestSHA83e8f6dd5aaa5adfcec92cd8e07b0838f645cb5635865bf19a603a8b668efff1;
lastSHAdc0330781caa89ddebb906d32e16b871c27aa56a2d8834f421dc2d3b99be0482.
QA maxcoordinate2.71315e-6 A/frame2.39914e-4 A². No live project jobs; no duplicate QA.

Final CPU residue decomposition: predicted within-residue radii1.472975/1.470371 A
versusGT2.196170; centroiderror6.685470/6.687586 A, centeredcoordinateerror2.635661/
2.634982 A. Two-seed disagreement1.025678 A (~old0.0011.026217): stable wrong
predictions. coordinate_diagnostics.json/source archived and uploadedremote.
Final0.1 frame attribution has same-residue macroMSEcontribution0.265079/0.260057
out of220.748725/219.031431 (~0.12%), median same/cross coordinategradientratios
0.00172461/0.00155863; zero anchors hit the norm floor. CPU scalar/gradientadditivity,
NumPy max5.68434e-14 A²,shortest finite differences/missingmasks/sourcehashes pass.
Reports/source reports/esmc_frame_attribution_01_2026-09-18.{json,md} and directory;
also uploaded asframe_attribution.json with old0.001 attribution in its oldroot.
These are coordinate gradients, not network/AdamW evidence; cross terms act onanchors.

Next predeclared docs/esmc_local_frame_gradient_audit_v1.md: four-case actual network
parameter-gradient audit of B=existing atom+0.1globalframe and R=separately normalized
existing same-residue frame pairs. Initial/best35 x35/166res,seed12345, one H100/no
optimizer, P=B+R unit-coefficient derivative probe only. No training coefficient or
new training loss selected yet. Require exact replay/provenance/finite gradients,
module/global moments and independent CPU QA before another training protocol.
That audit is now complete as631704 above. Original trained ESMC/allatom/confidence/heldout/full
cost goal active; preserve all labels/masks and one-cycle/one-structure objective.

Actual loss-component parameter-gradient audit COMPLETE, accepted. HPC3 631551
COMPLETED0:0 in1:41, model/audit work78.61s, no optimizer/updates. Four TRAINcases:
best25 andlast40 x35/166res, seed12345. Exact best-coordinate and last-eval-metric
replay, train/eval exact, all weight/input hashes unchanged, one trunk/one structure/
zero confidence. Max peak2.323076GiB. All1,361trainabletensors/121,673,521params
covered; each component1,354present/1,347nonzero, finite gradients in every case.
Independent CPU artifact/scalar/coordinate/moment identities/disjoint aggregation
QA passes. It does not repeat GPU derivatives; full parameter gradients not archived.

Current0.001-weighted frame/atom parameter norm ratios (best35,best166,last35,last166):
0.01747058/0.002119165/0.005740626/0.006425122. Simultaneous coordinate ratios
0.126300/0.054200/0.144512/0.133495. Cosines -0.001843/-0.080359/+0.326317/+0.322948.
Best166 negativecombined raw-gradient direction locally increases frame scalar;
otherthree decrease it. This is not an AdamW update prediction or universal conflict.
Combined-vs-component gradient reconstruction relative errors0.006887/0.004867/
0.006596/0.006320; BF16trunk modules~0.4–0.9%,FP32diffusion~1e-6. Consistent with
backward rounding, not proof all small geometry gradients vanish. Coordinate-only
scaling did not establish actual network loss balance; geometry term is weak here.

Report/heatmap/summary reports/esmc_loss_gradients_2026-09-18.{md,png,json};
compact4casecoords/labels/coordinategrads/parameter moments/source/QA archived in
the directory. All hashes verified; reportSHA1cd518283ac343e625369faee75a85fa0e4bf17294b9a66fac9ba60bf4f8cf95.
Immutable remote code_esmc_loss_gradients_v1_20260918/outputesmc_loss_gradients_v1_20260918.
No live jobs; do not duplicate audit. Ten focused tests/lint pass, no unrelated edits.

Next predeclared docs/esmc_geometry_capacity_weight01_v1.md: ONE controlled fresh-
init TRAIN32 experiment changes onlyframeweight0.001->0.1. At existing audited
states linear norm rescaling gives0.212–1.747,median0.608; an arithmetic estimate,
not an optimality/quality claim or GPU coefficient trial. Preserve identicaldata,
initialstate,noise/shuffle,precision,optimizer,budget100epochs/3200steps,stopping/
selection and every jointgeometry gate from631506. Match all64initialpredictions
beforetraining. No warmstart, no grid/automaticextension. Implementation/launch complete as631592; final result pending. Original trained
core/confidence/formalheldout/end-to-endcost goal active.

Scaled geometry + varied-sampler capacity experiment COMPLETE, negative gate.
HPC3 631506 COMPLETED0:0 in17:00, stopped at40epochs/1,280updates by the declared
20-epoch plateau rule. Selectedepoch25 jointscore10.586732 (limit<=1), worst
criterion54321:consecutive_C_N. Both seeds fail; zero of32 atomRMSD<=2 A.
Selected seed12345/54321 pooledatom9.106989/9.112429 A, CA8.618491/8.614477 A,
CAdistance7.722455/7.735322 A; NCA1.118120/1.116080,CAC1.110656/1.113081,
CO1.111359/1.103334,consecutiveCN3.175600/3.176020 A; handedness49.43/50.43%.
Last40 pooledatom improves to~5.44 A but jointscore worsens12.575799; preserve
predeclared selection, do not promote last weights or extend this configuration.

Independent CPU heavy checkpoint/input/source/FP64/geometry/selection/stopping
QA passes: max coordinate metric error2.713151e-6 A, frame scalar2.399144e-4 A²
(within declared FP32-vs-FP64 tolerance). All64 best predictions exactly replay,
initial32 match prior fresh initialization, input/frozen heads unchanged, actual
one trunk/one structure/zero confidence. Peak short-subset training2.758617 GiB.
Best SHAac71cd061032b88fb1bcd90df3e64100a3782537dfe05fc77938889bac709360;
last SHAc4f9d6d353b2b456d6f5474b0935382deb4edb17509a18e8347b1e1d99927013;
report SHA3ed3356f348d36e61d81768bf740dcc78305ca2cee11bbe7b9d2ac3712fe5de3.
Immutable code_esmc_geometry_capacity_v1_20260918/outputesmc_geometry_capacity_32_v1_20260918;
QAcode_esmc_geometry_validation_v1_20260918. Observer exec1691 finished0,
completion_workflow.complete=True. No live project jobs; do not duplicate QA.
Heavy checkpoints/oldinputpackets remainHPC3. Compact128predictions,32GT/inventories,
frame labels,histories,QA,sources/diagnostics archived reports/esmc_geometry_capacity_2026-09-18/;
report/curves/summary sameprefix.{md,png,json}. Final source/report hashes verified.

CPU shape/seed diagnosis complete under docs/esmc_geometry_diagnostics_v1.md:
new selected two-seed disagreementatom1.026217,CA1.059547,dist0.912455 A versus
old fixed-RNG selected8.632539/8.682719/8.020517 A. More similar predictions are
still inaccurate. New within-residue radii1.561642/1.556248 A versus GT2.196170;
centroid errors8.699980/8.706789 A, residue-centered errors2.692136/2.688531 A
(includes local orientation). This is less collapsed than oldradius0.553 but
incorrect local geometry/handedness; no quality success or isolated causal claim.
New CPU module src/fastglycan/coordinate_diagnostics.py, focused pose/missing/
collapse test passes; baseline decomposition matches prior accepted result.

Completed next diagnostic (accepted details above), docs/esmc_loss_gradient_balance_v1.md:
existing35/166 TRAIN inputs x own best25/last40 checkpoints, fixedseed12345,
no optimizer or new epochs. Measure separate aligned/frame and actual0.001-weighted
parameter-gradient norms/directions globally and by disjoint modules, with exact
replay/unchangedweights and independentCPU scalar/moment/source QA. Coordinate-
gradient scaling did not establish actual network-gradient balance. No new
coefficient grid, no951repeat (memoryalreadyverified), no architecture/loss change
yet. Audit631551 is complete; next fixed0.1 training protocol is above. Original ESMC/all-heavy-atom/
confidence/one-NFE/formalheldout/end-to-endcost goal remains unfinished and active.

Local-frame derivative audit COMPLETE and independently accepted. HPC3 631479
COMPLETED0:0 in2:15; actual model work90.39s. TRAIN35/166/951 exact capacity
replay (two applicable inputs), one trunk/one structure/no confidence, exact
train/eval replay for varied epoch1 seeds. Finite gradients through1,347 nonzero
parameter tensors; ESMC projection norms216.043/162.888/157.735. Backward peaks
1.1003/1.8061/47.1558 GiB. Short disposable final-projection L2=9.99953e-6 step
reduces summed scalar203.523255 ->203.486547; exact weights restored. No optimizer
or epochs. Input and final model hashes unchanged; both TF32 flags False.
Independent CPU source/artifact/GT-anchor/neighborhood/local-label/FP64 scalar QA
passes (max frame discrepancy1.63275e-5 A², aligned5.68434e-13 A²). Report/hash:
reports/esmc_frame_supervision_2026-09-18.md and directory; GPU reportSHA4ab48258e4f9b14646e6331268bbf05450cc0a336bd22f0cfceb293b4b78b1eb.
Actual CPU/GPU/validator sources and compact labels/predictions archived locally.
Immutable remote code_esmc_frame_audit_v1_20260918 / esmc_frame_audit_v1_20260918.
No live project jobs; do not rerun the accepted audit. Ten focused tests/lint pass.

New local-frame loss is usable as a derivative path, not yet a trained result.
Post-hoc coordinate-gradient ratios to aligned-MSE on32 best predictions have
min/median/max433/654/2263, versus initial3.26/3.62/6.21 and second seed88/153/578.
Equal audit coefficients are not production weights. The separately declared
scaled-geometry + varied-sampler training631506 has completed its negative
multi-seed capacity/geometry result above. Do not launch a speculative parallel hyperparameter grid.
Original trained core/confidence/formal held-out/end-to-end cost remain open.

Direct experimental-GT capacity run COMPLETE, fails its declared gate. HPC3
631201 completed0:0 in35:00,100epochs/3,200updates, best epoch85.32 training
proteins35–166res,121,673,521 trainable parameters from134,584,255 fresh core.
Pooled selected all-atom/CA/CA-distance errors2.542979/1.809505/1.513566 A;
0/32 atom RMSD<=2 A. Another sampler seed54321 gives9.066434/8.783899/8.179035 A.
Initial errors29.916716/29.615588/24.476017 A. Fixed-RNG fitting is insufficient.
Do not promote, extend epochs, restart this configuration or scale it up.

Final best checkpoint reload and all32 repeats exact; all input/frozen-head
hashes unchanged; one trunk/one structure call per output, confidence disabled.
Short-subset training peak2.758616 GiB. Independent CPU final heavy-artifact/
source/checkpoint/FP64 metric audit passes, max error2.713151e-6 A. Initial input
QA631201.0 passed32 cached ESMC/30,437 observed labels/1,496 masked atoms.

Local-geometry diagnosis: selected N-CA/CA-C/C-O distance RMSE1.060404/1.133064/
0.851764 A; consecutive observed C-N3.520176 A; GT-relative CA handedness49.04%
(1755/3579). Post-hoc exact centroid/within-residue decomposition: RMS radius
0.552642 A versus GT2.196170 A,71.7973% of aligned SSE in residue-centered
coordinate error (including local orientation error), centroid RMSE1.350481 A.
Second seed centroid RMSE8.797516 A and within-residue radius0.530218 A.
These show local atom collapse plus sampler-RNG sensitivity, not trained success.

Report/curves/archive reports/esmc_capacity_2026-09-18.* and directory:96 final/
initial predictions,32 GT/inventories, histories, QA/diagnostics and actual source
snapshots. Heavy initial/best/last weights and features remain HPC3 output
esmc_capacity_32_v2_20260918; immutable source code_esmc_capacity_v2_20260918.
Best SHA4d861a1e6037e84a7d5796ffee6280e096b822d463305f799b74dae55f54aced;
report SHAea15ac86b031d87b5cd0641baa99909b63eb07b769fd1ae0168c91cc8f3120ac.
Observer session44172 finished0; no live project jobs. Do not duplicate final QA.

First task631181 failed before optimization (51s): PyTorch seed alone did not
control SciPy/NumPy initialization. Fixed constructor seeds/restores all three
RNGs; CPU repeated default/capacity initial state hash
baad41b475327b40f3b458d04e7ee85696639776096a12699b661b2b87b908ea.
Old interface checkpoint/reload remains valid; retain original/failed snapshots.
18 original focused tests and5 local-geometry tests passed (3 overlap); lint
passes. Actual post-hoc diagnostic source is archived; current script differs
only by a line wrap after the verified execution.

Useful spare-CPU audits completed without another GPU:951-residue input
535,739,097bytes contains470,017,800-byte zero bond_mask; standard PyTorch ZIP
DEFLATE level1 gives4,433,548bytes with exact all-feature/label roundtrip. No
active input was changed; decompressed memory is unchanged. Future versioned
cache can use compressed packets/lazy loading. Report
reports/esmc_feature_storage_2026-09-18.md. Confidence audit records inference
resolution=-1 versus GT1.0 A, native confidence loss gate[0.1,4.0], default
alpha_pae=0, bespoke pLDDT target and need for modified-sidechain resolved-label
eligibility. Frozen-head capacity training is unaffected. Report/source archive
reports/esmc_confidence_interface_2026-09-18.md and directory.

Geometry-aware coordinate supervision and varying-sampler derivative audit is
now accepted; bounded scaled-loss experiment631506 is complete and negative above.
Do not merely extend this failed fixed-RNG/aligned-MSE configuration. New loss
coefficients/budget are now declared above. Original trained ESMC/all-heavy-atom/
confidence/one-cycle/one-NFE, formal held-out quality and full inference cost
remain open. Parallelize independent necessary work only, per user preference.

Fresh ESMC core interface gate is complete: HPC3 631114 completed 0:0 in 2:06,
independent CPU source/artifact/cache/label audit passes. 134,584,255 random core
parameters; no folding checkpoint/ESM2/teacher-state input. Initial hash
29588108548a225370c84410699dbfd8c4c3c9474d2b31e149495ef0470e11a4.
Actual one trunk/structure/confidence call and one sample for training lengths
35/951. Exact GPU replay/checkpoint reload, finite coordinates/confidence logits,
nonzero ESMC projection gradients4.577025/3.973495 and 413 nonzero parameter-tensor
gradients in both cases. Backward peaks1.100/47.155 GiB. Initial zero projection
is ESMC-insensitive; disposable L2=0.1 update gives max0.0510254-A same-RNG input
sensitivity on the short case. This is an untrained interface/derivative gate.

Both raw-GT rebuilds exact: 289/7,665 generated atoms, 289/7,446 observed GT atoms,
0/27 missing residues. CPU QA independently verifies all saved masks/coordinates
and accepted-cache features, initial weight/source hashes; it does not repeat
GPU derivatives. Actual matmul/cuDNN TF32 both False. Timings are cold/warm-mixed
first-call diagnostics, not an end-to-end benchmark. Fifteen focused tests/lint
pass. Execution snapshot/output code_esmc_core_interface_v1_20260918 /
esmc_core_interface_v1_20260918; CPU validator code_esmc_core_validation_v1_20260918.
Report/archive reports/esmc_core_interface_2026-09-18.md and directory; initial.pt
and large input tensors remain HPC3. No current core-interface job remains live.

Historical interface next-step note is superseded by the completed capacity
result and current next action above. Preserve the original objective.

Response-supervised pilot and selected-checkpoint experimental assessment are
complete. Training 630851 COMPLETED 0:0 (49:11), decode 630855_[0-3] COMPLETED
0:0 (2:15–2:34), corrected exact QA 631039 COMPLETED 0:0 (2:11). Best epoch2,
response macro/pooled ratios 0.9582185557065/0.9480782861723; best SHA
f6b93ede83357e4feff5492c359c9424cbbc69e60913266dffb907bf2c23501c.
Full-sampler all-atom/CA-distance errors 2.940202631/2.052314430 A versus c1
2.904473879/2.036335564; ratios 1.012301282/1.007846873. All-atom/distance harms
28/64 and 32/64. Joint 0.95-of-c1 gate and c2 parity both fail. Preserve this
negative result; don't extend epochs, expand teacher-loss grids or promote it.

QA 630856 and diagnostic 631028 failed only the response-revalidation equality:
the generic validator set cuDNN TF32=False, while original response training,
export and decode retained True. Protenix enable_tf32=False controls matmul,
not cuDNN fused conv2d. A same-pair False/True toggle exactly reproduces failed
and training losses respectively. Restoring actual matmul=False/cuDNN=True
reproduces all 64 response records exactly and passes every pair/identity atom/
source/hash/metric check. No model, coordinate or tolerance change. Explicitly
record actual backend flags; do not call the old config flag globally TF32-off.
Original snapshot code_response_training_v1_20260918 remains immutable; accepted
QA snapshot/root code_response_validation_v3_20260918 /
response_validation_v3_20260918. Failed v2 diagnostic is archived in qa_v2/.

Final training JSON/best/last weights, 128 decoded coordinates, worker traces,
accepted QA/precision diagnostics and actual training/validation source files
are locally archived and hash-verified in
reports/stage1b_response_supervision_2026-09-18/. Final report/curves/summary use
the same prefix. Bulk pair/cache tensors remain HPC3. Experimental CPU append
is complete in reports/stage1b_experimental_validation_2026-09-18/response_validation.json;
all unchanged GT/member/identity and independent FP64 metrics pass. Response
GT all-atom/CA/CA-distance errors 4.797496/4.583442/3.107093 A; only ~0.35%/1.26%
all-atom/distance improvement over c1, worse than c2 and accepted raw-state
learners. No intermediate checkpoint was selected/evaluated on GT. All six
conditions now appear in the experimental report/figure. No temporal-test read.

Historical next-step note (superseded by current capacity task above):
Next work was predeclared in docs/esmc_core_interface_v1.md: implement fresh random
ESMC-conditioned all-atom core using explicit Mini topology as an implementation
baseline, no pretrained folding checkpoint or teacher-state inputs. Start with
CPU construction/data checks and the already verified 35/951 training examples,
then measure actual one-cycle/one-NFE outputs/confidence, gradients, conditioning
and memory on one necessary GPU. No core implementation/GPU trial started yet.
After interface evidence, separately specify bounded direct experimental-GT
capacity training. The original trained ESMC-600M/all-atom/confidence/one-cycle/
one-structure-evaluation and formal quality/end-to-end cost gates remain open.
No jobs remain active in this response pipeline. Do not rerun completed pilots.

## Earlier preparation and result records (status superseded above)

ESMC input boundary implemented in src/fastglycan/esmc_features.py, with strict
pinned-spec/sequence/one-based-residue/single-chain/name/BF16/finite checks and
no silent replacement of ESM2 features. Fourteen focused tests and lint pass.
Actual Protenix chemical/token mapping plus accepted cached ESMC features passes
fixed shortest/longest training sequences 35/951 (289/7,665 atoms), exact mapping
and unchanged chemical features. CPU step 630851.3 completed 0:0 in 26s, no extra
GPU. Snapshot code_esmc_boundary_v1_20260918; output esmc_boundary_v2_20260918;
reports/stage1b_esmc_feature_boundary_2026-09-18.{md,json}. Source hashes checked
locally. Step .2 failed before featurization because Slurm overwrote CUDA visibility;
unchanged source succeeded with `srun --gres=none ... /usr/bin/env
CUDA_VISIBLE_DEVICES= python ...`. Set visibility after srun, not only --export.
This is only the input boundary; no ESMC folding model/loss/training claim yet.

Read-only original-objective interface audit is recorded in
reports/stage1b_esmc_interface_audit_2026-09-18.{md,json}, including installed
HPC3 source hashes/excerpts. Accepted ESMC final features are BF16 [L,1152];
Mini-ESM uses ESM2-3B width 2560 projected to 449, with single/pair 384/128.
The inference dataset also precomputes ESM2 embeddings, so swapping projection
dimensions alone does not create an ESMC path. No ESMC all-atom folding core is
implemented locally yet; ESMCShardStore currently feeds the CA refiner. Preserve
the original separately trained/randomly initialized folding-core contract.
The source initializes the sequence projection to zero; future conditioning
checks must verify gradient/use after an update, not only identity at init.
No GPU/GT/test reads or new model training were needed for this audit. Corrected
the obsolete deferred-production-cache paragraph in docs/esmc_cache_v1.md.

User preference: parallelize genuinely independent, necessary experiments to
save time, avoiding redundant computation or indiscriminate GPU/loss grids.
Experimental GT baseline assessment and independent QA completed 0:0 as CPU
steps 630851.0 (40s) / 630851.1 (12s), using one reserved CPU and no extra GPU.
ACD rejects standalone CPU batch jobs; use --overlap --gres=none within a live
allocation only when appropriate. Exactly 64 raw mmCIF-derived GT records
rebuild bit-exactly; all metrics independently recompute in FP64. There are
140,457 observed atoms, 18,014 CA atoms, 944 masked missing residues; prediction
coverage on observed GT is 100% in every condition. GT pooled all-atom errors
c1/c2/c4/pointwise/triangle: 4.814416/4.694222/4.537611/4.708911/4.706845 A;
CA-distance: 3.146723/3.088734/2.871992/2.996987/2.994481 A. Old learned models
modestly improve experimental error despite worsening teacher-relative error;
preserve both results and their original failed teacher gates. No automatic
promotion; these pre-cutoff validation groups do not establish temporal-test
generalization or absence of teacher pretraining overlap. Five focused tests
and lint pass. Source snapshots code_experimental_assessment_v1_20260918 /
code_experimental_validation_v1_20260918; output experimental_assessment_64_v1.
Local reports/figure/archive reports/stage1b_experimental_validation_2026-09-18.*
and directory; actual immutable validator source is archived in source/.
Temporal-test manifests/coordinates were not opened/evaluated.

After response training/decode/QA finish, archive their final JSON/checkpoints
and 128 coordinates, run report_response_pilot.py, then run
scripts/append_response_experimental.py --assessment-root
reports/stage1b_experimental_validation_2026-09-18 --response-archive
reports/stage1b_response_supervision_2026-09-18 locally on CPU. It requires
completed original response QA, verifies unchanged GT/identity provenance and
compares F32/F64 metrics before creating response_validation.json. Then rerun
report_experimental_assessment.py to add the sixth condition. Do not evaluate
intermediate checkpoints on experimental GT or alter running selection rules.

Current response pipeline: training 630851 running; 630855_[0-3] native decoding
and 630856 final QA wait on verified success dependencies. Combined 951-residue
learner/decoder smoke passes two optimizer steps, exact BF16 identity/reload,
nonzero second-step endpoint/context gradients and unchanged teacher weights;
peak 12,107,940,352 bytes (~11.276 GiB). Fresh initial weights match accepted
pointwise baseline exactly. Sixteen epochs are complete; best epoch two has
validation response macro/pooled ratios 0.958219/0.948078. Later training loss
continues down while validation worsens (epoch sixteen 1.216048/1.204748), so best
two remains selected; no full-sampler quality result yet. Keep fixed twenty
epochs and the existing selection rule; no new hyperparameter grid.
Progress figure/data: reports/stage1b_response_training_progress_2026-09-18.*.
Thirteen focused tests and lint pass. Immutable
code_response_training_v1_20260918; response_emulator_128x64_v1 /
response_decoded_64_v1. Held-out response losses exist, but final decoded quality
is pending; don't duplicate live/queued jobs. Current critical path is training,
then four independent decode shards, then QA. The independent CPU GT assessment
is already complete, so no additional GPU experiment is presently justified.

Response export 630834_[0-3] and acceptance 630844 completed 0:0 (4:33–5:00 /
5:03): all 192 samples, 27,005,917,279 bytes, atoms/lineages/sources and longest
train/validation c1/oracle direct response/cache replays pass. Cache
response_cache_128x64_v1; snapshots code_response_export_v1_20260918 /
code_response_acceptance_v1_20260918. Acceptance SHA
3f02dff8ce1ee57d2c76709dbe985c71e88beda88c0dcc12eefd1cc90b8ca62f.
Controls/traces/384 coordinates locally archived and hash-verified under
reports/stage1b_response_supervision_2026-09-18/cache; bulk tensors remain HPC3.
These paragraphs supersede older execution/next-step status below.

Latest decoder-gradient result: HPC3 630782 (2:57) and independent saved-result
QA 630783 (0:35) completed 0:0. Lengths 35/91/408/951 all have exact c1/oracle
response and c1 atom replays, finite nonzero gradients through pair_z and p_lm,
unchanged teacher weights and no teacher parameter gradients; c_l is reference
only. Longest peak allocation 14.410 GiB; shortest finite-difference relative
errors 0.0002032/0.00005409 pass. BF16 rounding attenuates the tested corrections.
Both old learners have a locally ascending response-loss update at length 408;
these four training controls do not establish population quality. QA recomputes
all saved scalars/directions/FD and learned pairs and verifies all lineage and
artifact hashes, without a second decoder backward. Thirteen focused tests
and lint pass. Snapshot code_decoder_gradient_v2_20260918; output
decoder_gradient_audit_v2_20260918. Reports/figure/archive:
reports/stage1b_decoder_gradients_2026-09-18.* and directory. Initial 630777 failed
on missing torch.utils.checkpoint import; v2 only imports that submodule. V1 QA
630780 dependency-cancelled. All jobs complete; do not rerun completed audits.

Next contract: docs/stage1b_decoder_supervision_pilot_v1.md. Same pointwise
architecture, fresh matched initialization, fixed 128/64 selection, full-pair
first-response MSE through frozen decoder, twenty epochs and mandatory final
64-target structural gates. Separate response cache QA and combined learner/
decoder longest-target smoke precede training. No export/training submitted.
Feasibility is not learned quality; original ESMC-600M/all-atom/one-evaluation,
experimental-GT and full 1,600 validation requirements remain unfinished.
This supersedes the historical pending/no-gradient-job paragraphs below.

Latest triangle pilot: training 630661 (2:57), full decoding 630663_[0-3]
(2:19–2:52) and independent QA 630664 (0:42) completed 0:0. Best epoch 20 has
state-MSE macro/pooled ratios 0.791984/0.776587, but all-atom/CA-distance ratios
to c1 are 1.018139/1.024451 (to pointwise: 1.004051/1.001982), failing both
structural gates and c2 parity. Actual shared initialization and non-architecture
contracts match; longest 951-residue GPU check peaks at 1.867 GiB with finite
nonzero triangle gradients. Eleven focused tests, exact 64 pair/c1-atom replays,
selected-checkpoint revalidation and all lineage/source/artifact checks pass.
Immutable code_triangle_pair_v1_20260918; outputs triangle_pair_emulator_128x64_v1
and triangle_pair_decoded_64_v1 under coordinate_refiner. Report/figure/full
archive reports/stage1b_triangle_pair_2026-09-18.* and its directory. All jobs
complete, no live project jobs. Stop extending pointwise/triangle raw-MSE pilots.

Next step predeclared in docs/stage1b_decoder_gradient_audit_v1.md: four fixed
training-only groups (shortest/longest plus two stratified, seed 107), capture
first actual denoiser response at shared noise, retain c1 singles, freeze teacher
weights and rebuild all pair-dependent caches differentiably. Check replay,
pair gradients and shortest-target finite differences, plus longest memory.
DiffusionModule.forward is directly callable with inplace_safe=False; the
runner.predict wrapper is no-grad. Actual sampling autocast is disabled and
pair_z is FP32, but these flags must be verified at runtime. A denoiser response
is not the final Euler-updated sampler output. No gradient-audit or new-loss
training job submitted yet. Decoder-output supervision remains unproven; the
original ESMC-600M/all-atom/one-structure-evaluation objective remains unchanged.

Latest component audit: 630609_[0-3] and independent QA 630632 completed 0:0
(2:24–3:41 / 3:35). Initial QA 630623 stopped on relp preprocessing; corrected
immutable validator code_pair_components_validation_v2_20260918 calls the same
generate_relp function, preserving initial predictions/sources. All 88 actual
pair_z caches, eight learned pairs, all compositions/c1-c4 atom replays and
source/coordinate hashes pass independent recomputation. Median interaction
target energy fraction 0.7762, remaining learned interaction error ratio 0.8387
(global 0.1267). Learned raw/cache MSE ratios 0.7692/0.7584 give all-atom
4.8245 A versus c1 4.8551 A; oracle interaction gives 0.4659 A and improves 8/8.
Eight training-only target-aware controls do not establish a learned remedy.
Snapshot code_pair_components_v1_20260918 and output pair_component_audit_v1_20260918
under coordinate_refiner; reports/figure/archive stage1b_pair_components_2026-09-18.
No live project jobs remain. Do not rerun completed predictions or failed QA v1.

Next model is predeclared in docs/stage1b_triangle_pair_pilot_v1.md: one 16-channel
directional shared-neighbor branch, preserving baseline shared initialization,
all c1-only inputs, raw loss, split and twenty-epoch schedule. Separate class
src/fastglycan/models/triangle_pair_state_emulator.py has 195,568 parameters and
three passing CPU tests; two component tests also pass. GPU capacity and
training/decoder/QA pipeline integration remain undone, with no new training
job submitted. Test this one relational-information hypothesis without sweeping
architectures/losses, and retain all decoded structural gates and original
ESMC-600M/all-atom/one-structure-evaluation requirements.

Latest completed result: decoder 630570_[0-3] and independent QA 630576
completed 0:0 (2:13–2:48 / 1:04), finishing the learned 128/64 pilot. All 64
predicted pair tensors recompute exactly; all c1 atom replays, source/artifact
hashes, metrics and selected-checkpoint validation pass. The 187,344-parameter
model selects epoch 20: state-MSE macro/pooled ratios 0.795291/0.780329, yet
pooled all-atom/CA-distance ratios to c1 are 1.014031/1.022424 (to c2:
1.522340/1.444591). State MSE improves 63/64 groups; only 16/64 improve both
structure metrics. This is a negative structural result, not a successful
cycle-saving model. Eighteen focused tests pass; reports/figure and full local
control/training/coordinate archive are reports/stage1b_pair_state_emulator_2026-09-18.*
and its directory. All jobs are complete, no live project jobs remain. Do not
extend this raw-MSE configuration or scale up. Next use training-only controls
to diagnose which state components affect the frozen decoder; decoder-related
supervision is a hypothesis, not a proven remedy. Original ESMC-600M/all-atom/
one-structure-evaluation objective remains unfinished. This supersedes older
submitted/running status below.

Current execution update: HPC3 export 630528_[0-3], cache QA 630549 and
twenty-epoch training 630554 completed 0:0. All 192 cache samples, 11.5 GB state
bytes, parent atoms and four longest exact replays pass. Selected epoch 20 has
validation macro/pooled state-MSE ratios 0.795291/0.780329; GPU checks and exact
checkpoint revalidation pass. Full 64-target decode 630570_[0-3] and independent
QA 630576 are submitted, with no coordinate-benefit claim yet. Separate roots
pair_state_cache_c1c4_128x64_v1, pair_state_emulator_128x64_v1 and
pair_state_decoded_64_v1 are under coordinate_refiner, with immutable
code_pair_state_{export,acceptance,training,decode,validation}_v1_20260918 snapshots.
Nested selection: 128 train (35–951 residues), 64 validation (45–770).
Local archive: reports/stage1b_pair_state_emulator_2026-09-18/.
This supersedes the older no-export/no-training status below.

Latest active direction (supersedes historical method-status paragraphs below):
the original objective is still efficient, MSA-free all-heavy-atom protein
prediction. Stage 0 routing and Stage 1A/1C diagnostics favor studying late-recycle
refinement emulation. The accepted 16,000-group c2/c4 teacher corpus, 14,400/1,600
exact-group split and ESMC-600M cache are frozen. Training runs on HPC3.
The initial CA refiner is an intermediate diagnostic, not the final model.
Its sequence-only 4,096/1,600 pilot improved CA error by 0.66%; explicit c2
geometry improved it by 3.01% but worsened pair-distance error by 3.65%, failing
the joint 5% gate. Pair-distance supervision at weights 0.5 and 2.0 is also
complete: CA/distance ratios are 0.979665/1.002997 and 0.985066/0.994245, both
failing the same gate. Per-protein diagnostics expose widespread contraction
and harm to already-close c2 structures. Stop expanding the loss-weight grid.
Indexed pair-geometry attention against the lambda-2.0 baseline is complete
(HPC3 job 629624): CA/distance
ratios 0.984755/0.996009 also fail, with no material gain over radial inputs.
The separate radial-plus-confidence ablation, HPC3 job 629633, is also complete:
CA/distance ratios 0.978622/0.996743 fail; confidence reduces already-close-group
distance degradation from 19.00% to 12.27% without eliminating harm. All 31
focused tests pass; both jobs and selected-checkpoint/source/example hashes
are fully verified. Do not restart these completed pilots or launch full training.
Read-only HPC3 audit 629639_[0-1] is complete and verified: training directional
fit is also weak, loss gradients mostly agree, and removing clipping changes
actual Adam updates materially. Continuation array 629642_[0-1] is complete:
clipping 10/100 through epoch 30 leaves the best checkpoint at epoch 9 and
worsens final validation beyond c2. Lineage/source/checkpoint/example hashes
and revalidation pass. Stop extending these runs; full training is not justified.
Source/config audit finds teacher MC-dropout defaults 0.4/0.4 and shard-level
seeding. Completed runtime audits 629659/629664 confirm recycle-dependent RNG
drift when MC dropout is active, and numerical repeat variation under default
settings. Deterministic algorithms/CUBLAS control yield identical all-atom c4
repeats for 8/8 short training examples. Median paired c2/c4 CA difference is
0.28081 A versus 0.56574 A for alternate c4 noise; this is not a population
noise floor or proof of every refiner failure. All traces/coordinate hashes pass.
The versioned 512-train/256-validation paired-teacher comparison is now complete.
HPC3 generation 629674_[0-3], acceptance 629682 and matched training 629683_[0-1]
all completed 0:0. All 768 pairs / 227,718 residues pass independent artifact,
trace, source, checkpoint, ESMC and actual training-read QA; four longest
targets (1009/1002/951/911 residues) repeat every atom exactly. Derived root
/data/user/shuang886/Folding/stage1b/teacher_pairs_paired_v2_pilot512x256 remains
separate from the original corpus. Immutable code snapshots are
code_paired_teacher_v2_20260918 and code_paired_comparison_v2_20260918.
Old/new training outputs are pilot_original_teacher_512x256_v2 and
pilot_paired_teacher_512x256_v2 under coordinate_refiner. Actual initialized
weights, ordered groups and all non-teacher run-contract fields match.
Original-protocol best epoch 9 gives CA/distance ratios 0.987727/0.994711;
paired-protocol best epoch 4 gives 1.000206/1.000051. Both fail the 0.95 reference.
Paired c2/c4 baseline CA disagreement falls 3.82983 -> 2.02620 A, but all ten
paired validation epochs are worse than identity c2. Direction cosine median
falls from 0.1021 to 0.0184; protocol changes do not rescue this CA refiner.
Twenty-one focused tests, selected-checkpoint revalidation, independent
best/last/source/history hashes and pooled per-protein metrics all pass.
Reports: stage1b_paired_teacher_pilot_2026-09-18.md and
stage1b_paired_teacher_comparison_2026-09-18.{json,png}; raw controls/reports are
in reports/stage1b_paired_teacher_512x256_2026-09-18/. Do not rerun these jobs.
Stop expanding coordinate-only training or loss grids. The teacher-state
diagnostic below guides a representation-level experiment. Post-hoc CA
information loss is a working hypothesis, not a demonstrated cause. No further
learned-student training has been launched.
Source inspection confirms pair-dependent decoder caches must be rebuilt after
state replacement. Teacher-state audit 629756 and independent QA 629768 completed
0:0 (4:36 / 0:12). All eight training-only c2/c4 replays reproduce every atom
exactly; all accepted input/trunk, shared RNG, cache, 24 state / 64 coordinate
hashes and recomputed metrics pass. Every prediction has two decoder NFE.
Median all-atom RMSD to c4: c1 1.06608 A, c2 0.43837 A, s2/z4 0.10495 A,
s4/z2 0.38737 A, halfway 0.22323 A. Pair-only improves 8/8; single-only 5/8
and worsens pooled error. These are target-aware teacher interventions, not
learned-student results or proof of the prior CA model's failure mechanism.
Snapshot code_teacher_states_v1_20260918 and output teacher_states_audit_v1_20260918
are under coordinate_refiner; local reports/coordinates are in
reports/stage1b_teacher_states_2026-09-18/ and report/figure
stage1b_teacher_state_boundary_2026-09-18.{md,png}. Do not rerun these jobs.
C1 follow-on 630486 and independent QA 630499 completed 0:0 (4:00 / 0:33).
All eight c1/c4 replays are atom-exact; parent/state/composition/cache/noise/
source hashes and 40 coordinate files/recomputed metrics pass. Cached conditions
use zero new trunk-stack calls and two decoder NFE. s1/z4 median/pooled all-atom
error is 0.13103/1.12361 A versus c1 1.06608/8.16026 A and c2 0.43837/3.74213 A:
8/8 improve over c1, 6/8 over c2. These target-aware controls are not learned
student results. Report/figure: stage1b_teacher_c1_states_2026-09-18.{md,png};
raw local audits/coordinates in reports/stage1b_teacher_c1_states_2026-09-18/.
Do not rerun completed jobs. Next implement the predeclared learned pair-state
pilot in docs/stage1b_pair_state_emulator_pilot_v1.md: nested 128/64 groups,
c1-only residual pair MLP, twenty epochs, identity selection candidate, and
mandatory frozen-decoder all-atom validation. No export/training job yet.
This remains a teacher-side Mini-ESM compatibility experiment; the primary
ESMC-600M conditioner and eventual one-cycle/one-structure-evaluation objective
are unchanged and unfulfilled.
The 256-group experiment does not replace the full 1,600-group gate, which
remains unpassed; raw teacher differences are not experimental-structure accuracy.
Preserve the original all-heavy-atom objective and temporal-test freeze.
The temporal test remains frozen. Preserve source and
checkpoint provenance, and keep this memory,
the decision log and `.summary.md` current as experiments advance.

The active project is now OneStepFold: a strict, open, MSA-off protein folding
experiment with a multi-chain-aware GT catalog and a monomer-first training
view. The model target remains one Pairformer cycle, one structure-module
network evaluation, and one output sample. The primary sequence conditioner is frozen
ESMC-600M with cached per-residue embeddings; ESMC-300M and ESMC-6B are scale
ablations. The folding core is randomly initialized and trained separately.
The official `protenix_mini_esm_v0.5.0` ESM2 path is a compatibility baseline,
not the active conditioner. Clean-Structure MeanFlow remains the proposed
method with native one-step/consistency baselines.

Current scientific boundaries:

- the catalog is multi-chain-aware, but the first training/evaluation view is a
  declared monomer pool; a future multimer view reuses the same GT schema;
  ligand/RNA entities are not model inputs in the first view;
- MSA disabled by experimental protocol, with ESMC used as the single-sequence
  conditioner;
- `N_cycle=1`, structure `N_step=1`, `N_sample=1` are the final target, not an
  assumed starting capability;
- structure-core NFE and end-to-end ESM latency are reported separately;
- a clean-structure MeanFlow loss requires a derived JVP target and geometry
  path validation; it is not a plain coordinate MSE label;
- ESMC is not a drop-in replacement for Protenix Mini-ESM: the cache, model
  revision, residue alignment, and dimensionality adapter are versioned
  artifacts, and the ESMC folding core is trained separately;
- ESM3 structure-track outputs are excluded from the main input contract; ESM3
  is sequence-hidden-state-only ablation because its multimodal generation can
  act as an unstated structure teacher;
- the primary training sample is structure-derived: the input sequence,
  residue numbering, and all-atom target come from the PDB mmCIF entity/chain;
  UniProt/SIFTS is retained for provenance and residue-level traceability only,
  not as the source of the model input sequence or target coordinates;
  AF/ESMFold/Atlas coordinates are excluded from the primary target set;
- the initial hpc2 raw snapshot uses SIFTS flatfiles dated 2026-09-08,
  yielding 244,406 chain-mapped PDB entries and 76,273 UniProt accessions;
  remote downloads are staged under `/hpc2hdd/home/shuang886/Folding/Dataset`
  with PDB mmCIF and mapped UniProt FASTA kept as separate raw layers;
- the first-version entry universe is deliberately fixed to the `244,406`
  SIFTS-linked PDB entries already staged on hpc2. This is not an all-
  experimental-PDB universe, and no unmapped entries will be added in the first
  version. SIFTS remains an entry-discovery/provenance layer only; the training
  sequence and coordinates are still extracted exclusively from PDB mmCIF;
- dataset de-duplication is restricted to exact (100% sequence identity)
  duplicates at the chain level. Near-identical proteins, construct variants,
  and small mutations remain eligible records; exact-sequence groups must still
  be kept together when making train/validation/test splits to prevent label
  leakage, while the multi-chain structure instance remains the training unit;
- a PDB time split does not establish that ESMC has not seen a held-out sequence;
  record the exact ESMC revision and audit sequence overlap when its pretraining
  corpus is available, otherwise report residual representation-contamination
  risk;
- the authoritative 100% SI calculator is Biopython
  `Bio.Align.PairwiseAligner` in global mode, with identity defined as matches
  divided by all global alignment columns including gaps. Exact sequence
  SHA256 is only a lossless candidate index; it does not replace pairwise
  verification or introduce near-identity clustering;
- CUDA-oriented Protenix kernels and unverified ROCm fallback make backend and
  kernel selection part of the benchmark record;
- existing `src/fastglycan` code is preserved as a legacy prototype and is not
  the active data contract.

GT handling constraints:

- the chain resolver must map `SIFTS CHAIN ->
  _entity_poly.pdbx_strand_id -> entity_id -> _struct_asym.id -> atom_site`;
- missing atoms are not repaired in the raw or primary GT branch. Coordinates
  and atom masks are emitted as observed, and the training loss decides which
  atom labels are valid;
- missing residues may have a separately versioned PDBFixer-derived branch,
  but imputed residues/atoms must carry an explicit `imputed_mask` and are not
  treated as experimental coordinates by default;
- the raw mmCIF layer is immutable; any PDBFixer output is a derived artifact
  with its own provenance and does not replace the observed structure.

Multi-chain GT constraints:

- the universal GT schema represents a selected PDB structure instance and can
  contain multiple jointly modeled protein chains; the first training view
  selects monomer instances from that catalog;
- the GT record stores one sequence/residue/atom/mask block per chain plus a
  stable `chain_index`, `entity_id`, and label asym ID; total-residue and
  chain-count limits are applied at the instance level;
- the builder must preserve inter-chain geometry and emit chain-pair metadata
  needed for interface/contact losses and evaluation;
- `_pdbx_struct_assembly` and `_pdbx_struct_assembly_gen` must be inspected
  before shard creation. Asymmetric-unit coordinates and biological-assembly
  coordinates are distinct derived views and must never be silently mixed.

The first implementation milestone was Stage A: a deterministic catalog scan
over the fixed entry universe. Stage 0 folding evaluation uses a declared
low-homology monomer view with a paired fixed-seed run and a five-seed variance
subset. Do not start training or make an accuracy claim until the catalog,
monomer filter, checkpoint, Protenix version, assembly policy, kernel, and
latency accounting are captured.

Stage A scanner hardening passed 3-entry, 1,000-entry, and 10,000-entry HPC
audits with zero parser errors and zero unresolved SIFTS rows. The complete
244,406-entry catalog is now accepted: all 256 deterministic shards finalized,
PDB IDs are unique, error files are empty, dates and assembly composition are
present, and no partial outputs remain. The catalog-only monomer selector
produced 84,232 `monomer_clean` candidates and 18,427 `monomer_apo_like`
eligible records. Numeric resolution and coordinate-completeness thresholds
remain deferred to Stage B materialization.

The exact 100% SI manifest has also been generated for the monomer candidates
using Biopython global `PairwiseAligner` verification within lossless SHA256
sequence buckets: 84,232 records form 41,592 exact sequence groups with
42,640 verified duplicate memberships. No train/validation/test partition has
been generated yet; Stage B coordinate QA remains the next gate, followed by
an atomic split over these exact groups.

Stage B's first 10,000-record pilot (8,000 stratified plus 2,000 stress cases)
has completed on hpc2. Gemmi materialization produced 64 tar shards with
10,000/10,000 successful records and zero shape, finite-coordinate, mask, or
member-pair validation errors. The pilot reports coverage and missingness
distributions, modified-residue strata, geometry screening counts, and exact-
sequence structural variance. This is the historical pilot milestone; the
numeric policy, final split, and ESMC cache are superseded by the accepted
full-corpus milestones below.

The monomer training view is now structurally frozen: choose a biological
assembly with exactly one generated protein chain instance, zero generated
nucleic-acid/other-polymer chain instances, a primary X-ray/EM/neutron method,
one coordinate model, and a 20--1024 residue protein construct. Water, ions,
and small molecules remain allowed in `monomer_clean`; zero-small-molecule
records are marked as the `monomer_apo_like` subset. The full Stage B audit
below now freezes the resolution and coordinate-completeness thresholds.

The full Stage B v1 materialization is now accepted: all 84,232 monomer-clean
records succeeded across 348 tar shards, with 168,464 expected members and zero
shape, mask, finite-coordinate, or materialization errors. Full-corpus median
frame and canonical-heavy-atom coverage are 0.967 and 0.963. The frozen
`gt_quality_v1` policy yields 78,259 Train-valid records, 45,815 HQ-Eval-valid
records, and 5,973 rejects. It retains modified residues with unmapped side
chains masked and records clash density without making it a hard v1 filter.

Quality filtering rebuilt 38,400 exact sequence groups. Initial-release time
split at 2021-09-30 contains 31,689 train-seen groups (59,959 records), 6,711
unseen temporal test groups (12,940 records), and 932 leakage-excluded
post-cutoff same-sequence groups (5,360 records). A Biopython PairwiseAligner
near-homology audit uses a separate high-gap-cost global scoring policy,
residue identity, shorter-sequence coverage >=0.70, and at least 50 aligned
residues. Strict identity <0.30 leaves 15 groups (18 records) as the additional
low-homology test subset; the temporal test remains primary. The split artifacts
are frozen under `/hpc2hdd/home/shuang886/Folding/splits_v1`; the validated ESMC
cache is now the sequence-conditioning artifact for Stage 0.

The ESMC cache contract is versioned in `docs/esmc_cache_v1.md`. The production
cache uses `biohub/ESMC-600M` at HF revision
`28aed46fcaf217dfa59f78a589bb449aa3ae5d98`, using Biohub/esm revision
`bf343ba264b650dff7a073643725f9aaa1fdbe8d`, with the final residue layer as
the feature variant. Cache keys include the sequence SHA256, model and both
revisions, feature variant, and dtype. An all-layer, 2,000-group probe remains
available as an auditable representation diagnostic. The production cache
contains all 38,400 quality-valid exact sequence groups and passed an
independent Slurm validator. ESMC special tokens are removed only after an
explicit `L+2` assertion, and residue features are stored as BF16 sharded
safetensors.

The ESMC-300M scale-ablation cache is also complete on the two Precision W7900
cards. It uses HF revision `f0d413606442e6b433d5e75e9aae3285ca9b137f`, the
same pinned Biohub/esm revision, final-layer BF16 features, and the same 38,400
groups / 11,615,845 residues. Its two deterministic partitions merge into 719
validated shards occupying 21 GB under
`/media/WDisk/Datasets/OneStepFold/esmc_300m_final_v1`. It is an ablation and
does not replace the primary ESMC-600M cache.

Stage 0A is frozen as a compatibility-only Protenix Mini-ESM experiment. Its
view is `stage0_v1`: 1,024 HQ-valid temporal dev groups, a nested 128-group
five-seed variance subset, 2,440 remaining HQ-valid frozen-test groups, and a
separate complete 15-group strict-low-homology exclusion list. The sweep is
the 3x3 `{1,2,4} cycles x {1,2,5} steps` factorial through length 1024. It
must run on a fixed declared backend, preferably `i64m1tga800ue`, with each
factorial point submitted as an independent one-A800 job before any
ESMC-conditioned model tuning uses the frozen test. The runtime package is
Protenix 1.1.0 while the selected model checkpoint remains Mini-ESM v0.5.0;
their hashes are recorded independently.

Stage 0B/0C scoring and profiling found that quality depends much more strongly
on recycle depth than on structure diffusion steps. The current method-selection
stage is Stage 0D: predictive, risk-aware recycling from cycle-1 information,
compared against fixed depth, an AlphaFold-style reactive convergence signal
available only after cycle 2, and an oracle compute-quality frontier. This does
not claim adaptive recycling or early stopping as a new concept. The specific
question is whether recycle demand can be predicted before paying for the next
recycle. Clean-Structure MeanFlow is therefore deprioritized until a structure-
step bottleneck is demonstrated.

The cycle-1 internal-state audit is complete on `temporal_dev_v1` (A800 job
`12759723`, 1,024 records, zero hook errors). Compact Pairformer single/pair
statistics provide only a small additional risk-routing signal: HGB mean cycles
at TM catastrophic risk <=1% improve 2.066 -> 2.031, while joint TM/all-atom
risk <=1% improves 3.177 -> 3.156. Treat this as a diagnostic result, not a
novelty claim; retain fixed `c2_s2` and post-cycle-2 reactive convergence as
baselines, and keep the frozen temporal test untouched.

Stage 0E is complete on `temporal_dev_v1`: an independent c2_s2 run (A800
job `12761522`) produced 1,024/1,024 two-cycle internal traces with no hook
errors. The joint c2-to-c4 hard label has 76 positives. At joint risk <=1%,
the oracle is 2.129 mean cycles, the best current grouped-OOF HGB route is
2.477, and the existing reactive distance baseline is 2.551. This closes only
a small oracle gap and uses OOF threshold sweeps, so it is a diagnostic result;
default to fixed c2_s2 and require nested calibration before frozen-test use.

Stage 1A residual characterization passed a clean single-target smoke. The
runtime hook normalizes Protenix's unbatched `[L,C]`/`[L,L,C]` Pairformer
outputs, preserves cycle state after diagnostic exceptions, and runs
SVD/eigendecomposition on detached CPU FP32 tensors for backend portability.
The full temporal-dev `c4_s2` characterization completed as A800 job
`12767871` under `/hpc2hdd/home/shuang886/Folding/stage1a/residual_c4s2_v1`;
it has 1,024 rows, all three transitions, and zero feature errors. The
length-controlled report is committed under
`reports/stage1a_residual_analysis_2026-09-17.{json,md}`. Pair residual means
remain moderately correlated with c2 all-atom degradation after controlling
for sequence length (about -0.40); the spatial rank-8 statistic is for the
nonnegative pair-magnitude envelope, not the signed tensor rank.

Stage 1A is a completed characterization gate. Stage 1B teacher data uses
one deterministic train-valid record per exact sequence group and is split
into 16 independent Protenix shards for `c2_s2` and `c4_s2`. Stage 1C adds an
opt-in signed pair sketch and adjacent residual-direction cosines; its
256-target diagnostic is separate and does not touch frozen temporal test
data.
