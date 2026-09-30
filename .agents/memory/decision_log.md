## 2026-09-30 — Archived joint tradeoff attribution completed; stop initialization tracing

Previous760c55ea was progress:14new global solves+14controls, qualityscreenFAIL but
lower objective12/14. This turn performed CPU read-only attribution of that SAME
archive; no model/solver/training/GT-dependent selection/independent32 access.
Five states raw/local/start/zero_final/warm_final xAA/CA independently normalized:
140 dense matrices,2100 additive partitions,1440 protein/overallcontrast rows all
verified;maxpartition6.66e-16,summary0,objectivesum6.82e-14. Source/member/report/
code hashes bound. New scripts analyze_joint_tradeoffs.py,verify_joint_tradeoffs.py;
protocol mini_joint_tradeoff_attribution_v1.md; findings mini_joint_tradeoff_findings_2026-09-30.md;
reports/mini_joint_tradeoff_attribution_2026-09-30. Local Python/NumPy/SciPy/Torch
versions+commands inruntime.json. All processes terminal, no remote compute launched.
Objective mean reduction-.042491:rawcoordinateanchor-.0466813,rotation-.0001006,
torsion+.0003957,connection+.0001660,meanrepulsion+.0037292,tail/budget0. Anchor/
angles/connection/budget recomputed;repulsionterms reuse prior independently audited
source explicitly. Additive accounting is notcausal mechanism.
CA-lDDT -.000361904 but continuousGT distanceMAE .487798640->.487514467 (BETTER),
rawdistanceMAE .098817545->.093827281.5/7proteins CA GTMAE improve vs2/7CA-lDDT.
Old FAIL retained; do notclaimglobalbone worsening or change gate toMAE. CAthreshold
contributions(.5/1/2/4):-.00009631/-.00008371/-.00019130/+.00000943. Notroundingproof.
Warm joint still improves its ownstart AA+.001224629,GTdistanceMAE-.001878194;
shrinking relativeadvantage also includeszero armcatch-up, notwholesale destruction.
Warm joint-start AAsep1/2–4/5+: +.00057129/+.00063739/+.00001594;
GT distance MAE:-.00239360/-.00374405/+.00425946. Far-sequence contacts can worsen
whileproximal improve. All assessedGT spatialdist<15A.
Warmfinal-rawAA -.008303557:BB-.000238521,BO-.004488662,OO-.003576374;
sep1+.000459496,2–4-.000471113,5+-.008291940. SupportsBB27.1%,BO49.7%,OO23.3%,
sep5+79.8%; no percentagecausalclaim. Rawdistance error improves7/7warmvszeroAA,
but2FC3/4B9P GTMAE worsen+.005890665/+.004562437A and AAdecrease;
5GU9/3D8LGTMAE improve-.013272465/-.014604507A. More rawpreservation != guaranteeGT.
DECISION: end read-only initialization attribution. Next one bounded METHOD contrast:
whole-ideal ZERO-start samejointbaseline vsadding explicit raw inter-residue distance
preservation term. Runtimepairselection/targets MUST raw+native topology only, NEVER
this GT-selected diagnosticpairlist. Freeze oneformula/weight/budget beforeexecution;
no weightgrid, no failedwarmstart mixture. Use same14developmentinputs andarchived
controls, originalgates unchanged;no newmodel callsneeded. This is hypothesis, not
promisedfix; if fails, stop incrementalraw-preservation patching and consider independently
GT-supervisedoutputmapping. Do notreopen FD/numerical investigations, CAdistancegate
rescue, ind32 retuning or GTchoice of perproteinarm. Full one-step differentiable
chemicallyvaliddesign goal remains ACTIVE, unfulfilled; no productionpromotion.

## 2026-09-30 — Saved sidechain-angle joint start closes with mixed quality, screen FAIL

Previous1ab2fb55 local screen was positive, sufficient to run this single bounded
GLOBAL endpoint comparison. Same7 supported development proteins x2 archived C4/S1
raw predictions;3CR6 unsupported4 comparison slots retained. Reused14 WHOLE-IDEAL
zero controls from c4_ideal_reference_v1_20260930 odd cases; candidate loaded saved
sidechain_repulsion_v1_20260930 case i full values into SAME originalraw chart.
Whole-ideal reference, originalraw anchor/angle regularization, calibrated objective,
all-pair mean/top16 repulsion, raw branches and3x60 joint budget fixed. No new local
fit/model/training/GT fitting/ind32/Y38/precision changes.14 new joint solves only.
Preflight all14 chart hashes equal control, raw/reference/GT identities equal,
start replay max1.78e-15A. Two geometry_start tests pass. Frozen new initialization
contract calibrated_c4_sidechain_repulsion_start_v1, arms zero/sidechain.
Final AA .816196847791 -> .816853576310 (+.000656728519); CA .900562705372 ->
.900200801549 (-.000361903823). Predeclared joint quality SCREEN FAIL. AA improved
4/7proteins,7/14predictions;CA2/7,4/14. Earlier localAA14/14 is not final advantage.
Both14/14 zero severe + strict checked CA/IT chirality + raw RMS; absolute geometry
subchecks pass14/14, OLD FULL joint0/14 dueconnections. Same4B9P raw/GT branch errors
persist2instances. Candidate still14/14 below rawAA .825157133307, gap.008303557.
Heavy rawRMS .491800846 -> .440819896; CA rawRMS .228294571 -> .222248481; max atom
4.692212 ->4.727113A; worst penetration1.809588 ->1.807493A. Closer raw != betterGT.
Offline same rho100 final objective mean .272351554 -> .229860484,12/14 lower;
this is fixed-objective improvement without jointquality improvement, not proof of
convergence/global optimality. Endpoint objectives retained; no GT best-arm choice.
DiamondHill2CPUFP64 workers1thread:13cases180iterations,1case178;214–244closures.
Mean23.64215median19.61325s,range12.006–37.733,maxRSS899596KiB. Archived warmfit
mean6.77996s so combined method cost30.42211s; baseline23.22114 is historical timing,
not equal totalcompute. Pipeline238949 terminal,245.13s exit0;controller238954finished.
28 independent pose/metric/objective audits14pairs pass: maxpose1.405e-10A,
metric6.66e-16,objective5.12e-13,idealbond1.40e-12. Both old wholeideal and oldfullpose
fitted-start shadow audits28 each pass.194member archive3,635,777bytes everySHA
verified;4runtime scripts+protocolexact local. No livejobs. Worktree unrelated
changes preserved; task graph staged riskMEDIUM, full worktreeHIGH includes oldwork.
Reports mini_sidechain_joint_start_2026-09-30, docs mini_sidechain_joint_start_findings_2026-09-30.md;
remote /media/PM982/onestepfold/sidechain_joint_start_v1_20260930.
DECISION: close this initialization variant, no moreiterations/restarts/threshold
change/default promotion. Keep localpositive and finalnegative; deployedoracle still
unfulfilled, persistent goal ACTIVE. Do not resume backward debugging or claim
solver input differentiability. Next useful progress is bounded offline attribution
of saved final objective/structure tradeoffs (especially AA-losing2FC3/4B9P vs AA-
gaining5GU9/3D8L) before a genuinely new output-objective intervention; no new
initialization matrix, no independent32 retuning, no GT-conditioned arm selection.

## 2026-09-30 — Coupled sidechain preservation/repulsion passes bounded LOCAL screen

Previous goal turn581d6d47 was progress: pure fixed-backbone fit AA positive but
collision tailfailed. This turn ran ONEpredeclared coupled local objective on same
14saved C4 predictions,7proteins x2noises;3CR6 two sourcefailure slots retained.
No model/training/GT-fitting/ind32/Y38 or global joint solve. Baseline original whole-
ideal local zero angles;notcontinuingpurefit. Same fixedposes,N/CA/C/O/OXT,legalSC
angles. Optional collision args preserve olddefault;case0purefit replay BITWISE
exact60iters63closures,2.88s;old14savedpurefits re-auditedsuccessfully.
New objective:sidechain rawMSE+frozenmeanrep(sumrelu(depth-1.5)^2/N/.25)+top16
mean(relu(depth-1.9)/.1)^2,weight1fixed,no schedule/sweep. Pair support is union of
allowed rotations separating endpoints after excluding axis endpoints/same rigid
side. Conservative potentialdistancechange,notnonzerolocalderivativeclaim.
Onlythissupportinoptimization;ALLoriginalpairsinmetrics. Excluded21initialsevere
distances invariantmax7.11e-15A;old20both-nominal-immobilecount was differentdefinition.
Local AA .811601496->.815628947,delta+.004027451,all14/all7positive.CA .900141834
exactunchanged,allbone/nonmobilebitwise. SCrawMSE.537428->.282367,heavyRMS.378153,
maxatom4.249824A. Strictcheckedchirality+rawRMSbudget14/14. RelativepurefitAA.815950,
trade−.000321312 forcollisionimprovement. Local AAstillbelowraw.825157.
Allpair severe37->22,zero-severe7->9,worst2.841236589->2.769911076A;localSCREENPASS.
Variable-support severe16->1;excluded21->21. Onevariable remainder3IE9/12345:C1–CG1
res5,distance.813200A,penetration2.586800. Per-case severe neverincreasesbutworst
penetration increases3IE9/12345 2.5426->2.5868and1J7B/54321 1.4424->1.5974;do not
claimpercasenonregression/fullchemistry. Alloldconnectionsstillfail/fixedbone.
Objectivecomponentsmean:rawMSE.53743->.28237,meanrep.01079->.00277,tail3.67251->
.38736,total4.22073->.67249. ReportMSEseparatecomposite,gradientnormcomposite.
2CPUFP64workersone thread,13fits60iters,4B9P/54321 51iters91closures(gradientnorm
.02769),others62–90closures. Configmax_eval90 isnot per-closure hardcut:installed
Torch2.12.0a0git78258b9 LBFGS sourcecounterpositions+hashsaved;actual91not hidden,
noadditionaloptimizerloop/noconvergenceclaim.Mean6.78median5.68s,range3.14–13.22,
RSS887148KiB,pipeline97.48s exit0. Pipeline236237/controllerterminalpsmissing.
IndependentNumPy14pose/metric/invariants/pairsupport/terms verified:maxpose5.33e-15,
metric4.44e-16,invariant4.44e-15,objective3.55e-15.7tests pass. Oldpure14shadowaudit
pass.146memberarchive1,548,199byteshashverified;6runtimefilesexact. Remote
/media/PM982/onestepfold/sidechain_repulsion_v1_20260930;reports/mini_sidechain_repulsion_2026-09-30;
docs/mini_sidechain_repulsion_findings_2026-09-30.md. No livejobs. MethodnowFROZEN.
NEXT:one bounded GLOBAL endpoint comparison on same14rawC4,wholeidealreference,
calibrated jointobjective/oldgates/rawcis-trans/3x60LBFGS. Control reuse archived
WHOLE-IDEAL ZERO joint endpoints in c4_ideal_reference_v1_20260930(cases2*i+1,
armideal_ref). Candidate loadTHISrun saved full angle vectors(casesi) into SAME
originalraw/idealchart;do not reconstruct chart/rawanchor/regularization aroundfit.
Use geometry_start helper semantics, verifyinitialcoordinates matchsavedlocalfit;
originalrawcoordinate anchor remainsoriginal.14new jointsolves+14reusedcontrols,
not more local fitting. Freeze newprotocol before run,paired AA/CA/chemistry/oldjoint
andcost.A localPASS supports test,NOTdefault/deployment/independentgeneralization/
differentiableoptimizer/designclaim. Full originalgoalactive/unfulfilled;ind32old
rejectionunchanged. Do not chase3IE9weights or prolonglocalbudget.

## 2026-09-30 — Fixed-backbone sidechain fit gains AA but fails collision nonregression

Previous turn f028e9f6 was progress: read-only additive loss partition. This turn
implemented/ran one bounded local sidechain fit, no new model inference/training,
GT fitting, independent32 access or joint solve. New fit_sidechain_projection wraps
unchanged PoseVariables; only bridge rotations whose moving set excludes N/CA/C/O/OXT
allowed. All translations/rotations/other angles forcedzero; output nonmobile atoms
exactinitial via where; full masked vectors saved. Input target RAW only, equal
nonbone/OXT atom MSE. One zero start LBFGS60/max_eval90,history20,strongwolfe,
tolgrad1e-8/change1e-12;final iterate no fallback/best/renaming. Ring-only/noDOF
P/G/A unchanged;raw input graph detached,not differentiable-through-optimizer.
Uses whole-ideal archive e034567a's14 C4 predictions,7proteins x seeds12345/54321;
3CR6 unsupported2local slots retained. DOF135–290/structure,1450unique/2900two-seed
instances;161unique/322two-seed no-mobile residues. Protocol mini_sidechain_fit_v1.md
locked code/source before run.2CPU FP64 workers one thread,900s ceiling.
All14 complete60iters61–66closures,mean2.78s(2.36–3.02),RSS809004KiB,pipeline48.75s.
AA ideal-local .811601496->fitted .815950260,delta+.004348763;all14pred/all7proteins
positive. CA .900141834 EXACTunchanged;N/CA/C/O/OXT bitwiseunchanged. SideMSE
.537428387->.265699538A²;heavyRMSvsraw .514152->.368529,maxatom4.70412->4.11328A.
Strict checkedCA/IT chirality and rawRMSbudget14/14. Still belowrawAA .825157.
COLLISION SCREENFAIL: severe37->41,zero-severe7->7,maxpenetration2.841236589->
3.032497078A (meanpercaseworst2.26882->2.24450,doesnotexcusetail).Severeincrease
3IE9/12345 7->12,4B9P/54321 3->5;2casesimprove10unchanged. Alloldconnectionmetrics
fail14/14unchanged by fixedbone. CSV initial_joint/final_joint are CONNECTION ONLY
flags,notfulljointacceptance;documentednaminglimitation,notusedscreen.
Posthoc frozen-coordinatepairidentity:removed8,new12,shared29;20finalpairsboth
immutable underthisrepresentationcannotberepairedhere.New12allactualmotionpairs.
Worstshared W127CZ2–Y129CE2 in4B9P/54321 distance .940046->.367503A,penetration
2.459954->3.032497A,atomdisplacements.7809/.05986A. Not a newpair. Nominal mobile
setdoesnotprovenonzerodistancegradient. No force-causality/backwardbug claim.
Independent NumPy pose replaymax4.44e-15A,metric4.44e-16,bond/angleinvariant4.22e-15;
forbiddenparamszero,chemicalmapping/masks/hasheschecked.5relatedtests pass.
Archive143members1,453,715bytes/hashverified;fourruntimecodecopiesexact;posthoc
collision script/result separatelysavedboundhashes. Reports/mini_sidechain_fit_2026-09-30,
docs/mini_sidechain_fit_findings_2026-09-30.md. Overall report updated.
DiamondHill /media/PM982/onestepfold/sidechain_fit_v1_20260930, pipeline233641 and
controllerterminal/psmissing,exit0,no livejobs. Current version CLOSED; noautomatic
joint continuation afterfailedlocalscreen,default/oldgatesunchanged.
Next methodifpursued: one bounded local objective coupling RAWsidechain preservation
with nonbonded constraints on eligible moving atoms,not morepureMSEiterations or
class-specifictemplates. Immutable20collisions stillrequirelaterresiduepose stage;
sidechain-onlycannotbecomefullgeometryrepairbybudget. Locknewprotocolfirst,report
allpairs includingimmutable,do nothidebadcases. No independent32/Y38/modeltraining
orclaim of one-step/differentiable solver/design. Original goalactive/unfulfilled.

## 2026-09-30 — Saved ideal-reference loss partition points to sidechain contact preservation

Previous goal turn e034567a was progress: completed real C4 whole-ideal intervention,
partial AA gain but failed predeclared two-metric screen. This turn did bounded
READ-ONLY analysis of its saved coordinates, no new inference/solver/training or
ind32 access. New src/fastglycan/lddt_attribution.py preserves exact original AA
metric: GT<15Å, exclude same residue, strict .5/1/2/4 thresholds, atom-average.
Pair weights=(1/n_i+1/n_j)/N_valid; atom/pair partitions sum to original score.
Protocol mini_ideal_reference_error_partition_v1.md fixed atom classes/AA/termini,
raw-active/mismatched-branch neighbourhoods, pair types/separation/thresholds.
Seven supported proteins x2 seeds x5 stages=70 vectors,3CR6 skipped slots retained.
Equal proteins after within-protein seed averaging; absent classes zero additive
contribution, not denominator deletion. No GT input changes or symmetry remapping.
Ideal final−raw AA−.008960286 partitions: backbone-backbone−.000293044(weight.271),
backbone-other−.004836198(.497),other-other−.003831043(.233). Backbone=N/CA/C/O;
other includes sidechains and OXT. Atom-centred sidechain−.006355500(weight.487),
OXT−.000023519;NCA CO combined−.0025813. CA-centred AA includes sidechain partners,
so its decline does not contradict CA-only lDDT improving vsraw. Not causal proof
that only sidechain motion caused loss. Both sidechain-involving pair classes
negative in all7 proteins; bonebone positive in3.
Sequence separation1 contribution+.000279393(weight.053),2–4−.000576993(.149),
>=5−.008662686(.798). Sequence distant, not spatially >15Å. Four threshold
contributions−.00389121/−.00258643/−.00169847/−.00078418. No numerical-error claim.
Ideal local−raw loss−.013555637, mostly sidechain pairs; joint adds+.004595351
(bonebone−.00012769,cross+.00270333,otherother+.00201971). Whole-ideal vsnativefinal
+.003499055 also mostly sidechain-involving. All20 AA final-vsraw contributions
negative. L/P/R largest weighted deficits but not frequency-normalized causal ranks;
F small negative vsnative, other19 positive. No residue-specific template selection.
Raw-active connection neighbourhood covers100% atoms: UNINFORMATIVE contrast,not
connection-causality evidence. Raw/GT branch-mismatch neighbourhood only4B9P,weight
.0035,contribution−.0000206,others−.0089397;cannot explain all loss by local centres,
but does not exclude nonlocal branch effects.3IE9 negative case retained.
Independent dense directed-matrix verifier70 vectors2670 partitionrows328 summaries;
maxatom5.55e-16,partition9.99e-16. Source archive/member/report hashes and original
scores bound. Shared chemistry/connection helper disclosed.2 focused tests pass,
py_compilepass.70vectorarchive474539bytes/hashverified;unpacked atoms retainedlocal
but onlyarchive tracked. Reports/mini_ideal_reference_errors_2026-09-30;findingsdoc
mini_ideal_reference_error_findings_2026-09-30.md;overall updated. No runningjobs.
Next single candidate: FIX ideal local N/CA/C/O and each residue global pose;
fit ONLY bridge torsions whose moving atoms exclude all backbone/OXT, against RAW
sidechain coordinates (notGT). Proper local chemistry/rings remain fixed; Pro/no
eligibleDOF unchanged. First bounded LOCAL screen, no joint extension until quality,
backbone invariance and geometry evidence supports it. Distinct from failed old
all-pose fitted initialization; no promise MSE fit improveslDDT. Must lock protocol
before solving. Do not alter whole-ideal failed gate/default, retune weights, reopen
ind32/Y38, or claim differentiable solver/deployment. Original goalactive/unfulfilled.

## 2026-09-30 — Whole ideal-reference C4 intervention closed with partial AA benefit

Previous turn e8de8479 established positive GT-oracle local representation evidence;
this turn implemented the prescribed bounded real-C4 output-only intervention.
New ideal_output_reference uses all20 frozen explicit CCD ideal templates for
interior residues, proper N/CA/C frame alignment, exact native CA/termini retention,
named inventory/adjacency checks and checked stereo signs. Keep native bond graph,
input features, scoring reference/radii, raw anchors/cis-trans, calibrated objective,
top16 penalty and zero pose start. No AA cherry-picking, symmetry renaming, GT branch
choice, fitted start, two-length combination, new model inference/training/ind32 use.
Preflight807 interior residues/879 checked centres;14 local CA/terminal replays exact,
no fallback; rigid equivariance7.11e-15A, idempotence3.11e-15A, bond1.56e-15A.
Seven supported proteins x two noises12345/54321. Preserve3CR6 unsupported4 slots.
14 new solves +14 archived hash-exact native-reference calibrated controls; CPU2
workers FP64 one thread,900s ceiling,3x60LBFGS.13 end at180 iterations,one176;
closures207–241,solver median19.61/mean23.22s,RSS929248KiB. Pipeline251.12s exit0.
Raw AA/CA=.825157133/.900141834. Old local AA=.802942482; ideal local=.811601496,
CA unchanged. Old final AA/CA=.812697793/.900591068; ideal=.816196848/.900562705.
Protein-mean AA delta+.003499055 (6/7 proteins,12/14 predictions); CA−.000028363
(4/7 proteins,4/14 predictions). Tiny CA mean decline is not a backbone collapse,
but predeclared BOTH-positive screen FAILS; do not rewrite threshold/noninferiority.
Both14/14 zero-severe+strict checked chirality+RMS and absolute checks. Old full
joint0/14 both: angleC fails10,angleN14,omega14,CN/carbonyl0.4B9P two rawcis/GTtrans
mismatches persist. Ideal maxpenetration1.80959,CA RMSmean.22829,heavy.49180,
maxatom displacement4.69221A. All14 ideal final AA below raw;mean gap.008960286.
Initial AA advantage+.008659015;final preserves40.4% of that difference;descriptive,
not causal objective attribution.Recovers28.1% of old raw-to-final AA gap on this dev
batch,not whole failure fixed. Ideal local still37 severe pairs,final0.
Independent NumPy reference alignment/saved-pose/metric/objective audit28 and14pairs;
max coord1.40e-10A,metric8.33e-16,objective5.12e-13,bondinvariance1.01e-12A.
Three shadow old C4/fitted/two-length audits each28 pass,no new old solves.
5 focused local tests pass.Archive183members3,285,184bytes,all hashes and six runtime
source copies verified. DiamondHill root c4_ideal_reference_v1_20260930,pipeline230295,
controller230302 both terminal,no jobs running. Reports/mini_c4_ideal_reference_2026-09-30;
docs/mini_c4_ideal_reference_findings_2026-09-30.md;overall updated up front.
This batch CLOSED; default native-reference calibrated baseline unchanged. Keep
partial AA benefit, no deployment/independent generalization/input-differentiable
solver/design-success claim. Original goal active/unfulfilled. Next justified step
is bounded READ-ONLY analysis of existing raw/local/final GT errors by backbone,
sidechain and connection neighbourhood; identify where remaining loss arises before
another intervention. No new weights/budget/template sweep or reopening ind32.
Latest asynchronous homomer authorization was already executed in independent32;
do not restart source hunt. The old untracked active_experiment_status.json is
historical2026-09-27 scratch state, not the current run authority.

## 2026-09-30 — Whole CCD ideal-template local oracle screen positive

Previous goal turn20d0825a was concrete progress: two-length interventionnegative
andclosed. This turnfollowedwithfull-referencecandidateaudit, NOTanotherjointsolve.
ActualsameDiamondHillcomponents.cif469MiB/RDKit136MiB;sourcehashesboundtosame
priorcache. Exportexplicitpdbx_model_Cartn_*_idealfields20canonicalAA,167heavy
nonleavingatoms;no guessingconformer0/1/noGT-basedconformerchoice. Nativeallrefid2.
Saved20literalCCDblocks,stereoannotations,metadata,sourcehashes. Idealmetadata
softwaredetailsnull;do notclaimverifiedCORINAforall. wwPDBdefinitionlinkedindocs.
All20templateconstructors passnative/idealselfreplaymax1.777e-15A/equiv3.553e-15A,
21CA/ILE/THRcentre signs matchnative. NotindependentCIPcertification/fullchemistry.
Reuse64lockedconnectionGT32cal/32held,no fitting. Internalres5589/5405;complete
sidechains5579/5392;10/13missingresretainednotimputed. Termini excluded. Existing
ArticulatedOutput appliedtoGTcoordinatesbyresidue: GT-ORACLE localdistortion,
NOTMiniquality orbestpossible representationfit. Fixedatomnames/nosymmetryor
residueoptimization. Glyexcludedsidechainmeanonly. Disulfidecontextnotfullgraphsupport.
Heldprotein-equalmeansofperresRMS:heavy.303859529->.177431773A(delta-.126427757,
CI[-.137663396,-.115750633]);bone.065172429->.045335976;side.435912549->.255691065.
Allthree32/32proteinsimprove. Calanalog.303620->.171649,.063526->.043857,
.438100->.248864,all32improve. ByAAheldheavyD.16808->.17015,G.04969->.05848,
T.08727->.11143worsen;keepall,nohybridtemplatecherrypick. Leu.95563->.18628,
largeandname/probe/symmetrysensitive;notclaimphysicalconformererrorthissize.
HeldbackbonescalarMAE native->ideal:NCA.016828->.013457,CAC.042014->.018166,
CO.034578->.025718A;NCAC3.2582->2.3964,CACO2.4209->1.1479deg. Worseindividual
scalarfitthanpreviousmedianparametersbutwholelocalshapeimproves;notheadtohead
constructormediancomparison. Primarypredeclaredheavy+bone+20checksPASS.
IndependentNumPyframe/atan2/Rodriguesreplay64sources10971res21942projections,
maxcoord2.842e-14,metric1.295e-14,bondinvariance2.820e-14;6projectionbootstraps
andmasks/rolesverified. Sharedgraph/probemetadatainverification,notindependent
chemicalparser. Idealcoordsre-readfromCIFfields,sourceGT/memberhashesverified.
4existingconstructor/geometrytests pass.64npzarchived5.45MB withmemberhashes;
rawcoordsretainedlocalbutonlyarchiveingit. Exportremoteccd_ideal_templates_v1_20260930,
allprocessescompleted/noGPU/model/trainingorreservedind32use.
Reports/mini_ccd_ideal_template_2026-09-30;docs/mini_ccd_ideal_template_findings_2026-09-30.md.
ThisauditCLOSEDpositive. NEXT:oneboundedWHOLE-idealoutput-referenceinterventionon
existingC4devinputs;nativeinput,rawCApose,objective,budget/gatesunchanged;termini
explicitretainnativeunlessseparatelysupported. Do notpickD/G/Toldtemplatesbasedon
heldresults orcombinewithfittedstart/otherweights. CompareinitialandfinalGTquality,
chemistry,shape;localGToraclebenefitdoesnotguaranteeforwardbenefit. Oldbaseline
remainsdefaultuntilactualtest. No deployment/differentiablesolver/designclaim;
originalgoalactive/unfulfilled andind32rejectionunchanged. No runningjobs.

## 2026-09-30 — Output-only CA-C/C-O reference intervention closed negative

Previous goal turn abe62a7d was progress: isolated scalar calibration. This turn
implemented and ran bounded output-reference intervention on same8devslots,
seeds12345/54321;no newmodel/GPU/training/ind32access/calibrationrefit. Onlyinterior
residueC/Oradialupdatesusingfrozencal32medians. NCA/angles/sidechains/rings/termini
unchanged;graphCA-CcutmustisolateC/O. Nativefeatures/scoringreference/topology,
rawanchor/branches/calibratedobjective/onsets/weights/3x60LBFGS unchanged.
Preflight7supported807resupdates879checkedstereocentres pass;nonCO/termini/ring
coordsbitwiseunchanged;CAprojectionzero;unchangedprojectedatomsmax1.599e-14A;
length4.45e-16A/equivariance1.78e-15A,no fallback.6focusedtests pass incllocalAD.
DiamondHill c4_output_reference_v1_20260930 pipeline225418/controller225425 terminal
pipelineexit0;batch/audit/report/oldC4regression/oldfitregression allexit0.14newsolves,
14hash-exactreusedcontrols,3CR6fourchemistry-skips,0scientificprocessfailures.
TwoCPUFP64workers900sceiling;allnew180iterations,215-240closures,median19.56mean23.24s,
peakRSS926540KiB;fullpipeline239.5s. Historicalcontroltimesnotmatchedbenchmark.
RawAA.825157133/CA.900141834; oldfinal.812697793/.900591068;new.812428349/.900788655.
PairedproteinmeanAA-.000269445,CA+.000197587;bounded_screenFALSE. AA2/7proteins,
3/14predictionspositive;CA4/7,7/14. Both14/14zerosevere+strictcheckedchirality+RMS,
oldjoint0/14both. OldangleCfails10->8;angleN/omega14both;CN/carbonyl0both.
4B9Ptwo rawcis/GTtrans remain. Penmax1.79503->1.80999;heavyRMS.52280->.52799,
CArms.22930->.23155A. Noabsolute_failuresbotharms. InitialAAgainonly+.000108450
(.802942482->.803050932),CAexactunchanged;major~.022initialAAlossnotresolved.
PriorGTspanmediancomparisonchangedCAC/NCA;thisinterventionCAC/CO+interioronly,
notidenticalexperiment. Moreaccuratelengthscalarsnotguaranteeoutputfoldquality.
28NumPypose/metrics/objectiveaudit max2.641e-10A/8.327e-16/5.116e-13;
newtargetlengths preservedlocal/final<=3.560e-12A. OldC4/fit28eachshadowauditpass.
180memberarchive+SHA localverified;executionsourcesmatchcurrentcommit.
Launcherfailures beforecontroller:missing sys, shellquoteSyntaxError(pid224484),
helperPYTHONPATHmissing(pid224995);preservedlauncher_failure/import_failurelogs.
Scientificcontrolleronlystartedonce225425afterimportpreflight;noresumere-run.
Reports/mini_c4_output_reference_2026-09-30;docs/mini_output_reference_lengths_findings_2026-09-30.md.
CurrenttwolengthversionCLOSED;retainnative-referencecalibrated-zero baseline.
Do notappendweights/iterationsortryfit+newlengthgridonpanel. Nextmethodneeds
whole-residueconsistentoutputchemistryandshape-preservationevidence;inspect
existingtrusted/idealchemicalreferenceoptionsbeforeblindlyassembling5medians.
No newbackwardbugorLoRAjustification. Goalactive/unfulfilled,oldind32rejection
unchanged;solverstilldetachedandnotone-stepdifferentiableoutput. No runningjobs.

## 2026-09-30 — Independent output-backbone reference scalar calibration

Previous goal turn bda69034 was concrete progress: fixedCA necessary-condition
rejection and native-reference provenance. This turn completed the next bounded
calibration, no solver/inference/training or reserved independent32 access.
Reuse frozen64source connection corpus32calibration/32heldout; all64mappedarchive
GT/source/memberhashes verified.11122residue rows, internal5589cal/5405held;
terminal rows retained but excludedfit.20AA*5metrics medians/q05/q95 fitcalonly,
written beforeheldmeasurement andhashfixed. Support>=30residues/8proteins;
all20supported(minC74res/23proteins). CCD20backbonepositionsfromsameDiamondHill
runtimecachehashaspreviousprovenance; originalinputfeatures/model unchanged.
Heldprotein-equalMAE native->fitted: NCA .016828->.009422A;CAC .042014->.009648A;
CO .034578->.008955A;NCAC3.25823->1.88194deg;CACO2.42086->.80657deg. Improved
32/32exceptNCA31/32(4Y2Mdelta+2.0098e-5A). Proteinbootstrap2000seed9302030:
CACdelta-.032367CI[-.034330,-.030184];CO-.025623CI[-.027636,-.023441].
ReferenceCACbias-.041572A,fit+.000248;CObias+.034021,fit+.000275.
HeldGTspan necessaryconditions oldwindows/GTbranch, frozenref vs calibration-only
CAC/NCA medians:1459/5437->134/5437; proteinswithviolations32->23;maxgap.139668
->.130850A.64terminaledges18->6 butexplicitinteriorestimateextrapolation.
ChangesbothCAC/NCA,notuniquetermattribution;GTbranchdescriptiveonly. No constructed
output, lDDTclaim, newchemicalgate/fullconformerorproofglobalfeasibility. Quantiles
notphysicaltruth; experimentalrefinementbias/measurementerror/sourcefilterremain.
7focusedtests pass; independentno-primary-module auditor64/11122residues,300fit
quantiles,5bootstrapmetrics,173984Cartesiancorners;geommax2.842e-14,span1.333e-15.
Primary/fitted/input/outputhashes verified. Files reports/mini_backbone_reference_2026-09-30,
findingsdocs/mini_backbone_reference_findings_2026-09-30.md;overallfrontupdated.
No remotejobsactive;CPUreferenceexportfinished/noGPUconsumed. This calibration
batchCLOSED. Nextboundedmethod:separateOUTPUTchemistryfromnativeINPUTreference,
firstisolatedCAC/COlengthinterventionusingfrozencalconstants;verifychirality,
Proring,terminalhandlingandraw-preservinginitializationbeforeolddevC4comparison.
Do notblindlyassembleall5mediansintofullresidueorchangefit/branch/weightsjointly.
No pertargetGTlengths,noheldoutretuning,nonewind32runs. No repeatbackwarddebugging.
Originalone-stepdifferentiableoracle/designgoalactiveandunfulfilled;deployment
stillrejected. Keepoldthresholdsandind32negativeevidenceunchanged.

## 2026-09-30 — Fixed-CA necessary feasibility and reference-length provenance audit

Continued mainline after3181703b failed fitted initialization; no new solver/model/
training/independent32 access. Late user source approval already fulfilled: fullHPC3
search and homomer additions3VSV/5JVL/3F6B/6P63 locked32, completed independent gate;
do not rerun selection or validation on receipt of this duplicated async answer.
Read-only14C4 archive inputs7proteins2seeds plus7uniqueGT;3CR6two source skips retained.
Analytic CA-span bounds with invariantCA-C/N-CA lengths and old acceptance boxes:
raw746/1628 outside selected branch,735 outside both;all14instances. Maximumgap
selected2.169747A/both1.073412A;disjointedge CArms lowerboundmax.238106/.110547A.
11alternative-only span cases allalreadyGTbranchmatched;distance-only flipunsafe.
Calibratedzero raw818/813; notacceptance andboxesnotnested. Zero-final oldspan0,
butoldjoint0/14:necessarynot sufficient. Fittedstart871/857,final1/1gap.003832A.
GToldmodel-lengthspan176/814 acrossall7;posthoc replaceonlyintraresidue lengthswith
GTown values->4/814(4A02three,1J7Bone);noGTfedtomodel. ModelCA-Cmeans1.478-1.482A,
GT1.516-1.524A. CounterfactualchangesbothCA-C/N-CA,notuniqueCA-Ccausalattribution.
RuntimeProtenixget_ccd_ref_info readsRDKitcachemol.ref_conf_id;nativefeaturizeradds
rigidrefaugmentation. Savednative.ptref_pos==mapping.reference bitwise;cached/native
lengthmaxdiff2.575e-7A;native/local1.777e-15A. Constructor preservesinputreference
lengths. Concernisourhardchemicaluseofauxiliaryinputconformer,notProtenixbackwardbug.
Code/CCD/native/mappinghashesandperresiduelengthsarchived. DoesnotauditeveryCCD
constructionfallbackorproveallqualitylosscausedbylengths. OldbondRMSEreference-based.
5focusedtests pass;formula max1.333e-15A;constructedlengthinvariance2.104e-12A.
IndependentCartesian6512boxes/520960distances maxcorner8.882e-16A;analyticderivative
signchecks pass;FP64numericnotformaloutwardroundedproof;1e-6Aclassificationmargin.
Primarylock/reportunchanged;posthoccounterfactual/provenance separate. Reports root
reports/mini_ca_span_feasibility_2026-09-30;findingsdocs/mini_ca_span_feasibility_findings_2026-09-30.md.
RejectuniversalexactCAanchoring. Nextboundedwork:auditableoutputchemicalreference
separatefrominputfeatures,usingexistingindependentcalibrationassetsforbond/angle
checks;prelockanymethodchange,noGTper-targetreplacement/nogatechange/nobudgetgrid.
No new valid output,deployment stillrejected,goalactive. No remoteexperimentrunning
ornewGPUuse thisturn. Do not restartcompletedfitted/C4/ind32 batches.

## 2026-09-30 — Fitted initialization under calibrated C4 objective: bounded screen failed

Previous goal turn bbbd3eea was progress: actualC4 confirmation of calibrated onsets.
This turn tested next authorized initialization-only combination; concrete negative
result changes next action. Retain8development source slots/seeds12345,54321 and
3CR6unsupportedchemistryskip4. Reused14audited calibrated-zero controls with exact
coordinate/parameter hashes, NO14duplicate solves/replay claims.14new equal-atom
localfits(max_iter60/max_eval90)+frozen calibratedjointsolves(3x60).28outputs audited,
14paired,4sourcefailure slots retained. CPUFP64two workers900s/noGPU/newinference/
training/independent32. SourceGT onlyscoring. Originalraw chart/objective/regularizer
origins/branches/chemistry/onsets/buffers retained;fittedparameterscopiedinto samechart.
DiamondHill /media/PM982/onestepfold/c4_fitted_start_v1_20260930 pipeline217787,
controller217795 terminal;pipelineexit0,0processfailures. Do not restart.
Raw/zero-final/fitted-final AA .825157/.812698/.814901;CA .900142/.900591/.898754.
Fitted-zeroAA+.002203184;CA-.001836645 ->predeclaredscreenFALSE. AA improves11/14
predictions,5/7proteins;CAonly2/14,1/7(3D8L). NewvsrawAA-.010256,CA-.001387.
Bothfinalarms14/14zeroseverepairs,strictcheckedCA+ILE/THRchirality,RMSbudgets;
oldjoint0/14both. Oldconnectionfailsboth CN0,angleC10,angleN14,omega14,carbonyl0.
Absolute_failuresempty14/14both;maxpen1.79503->1.75487. Raw/GTbranchmismatches2
4B9PP122-P123 bothnoises unchangedfinal. NoGTbranchreplacement.
FittedstartAA.819113/CA.898821 vslocalzero.802942/.900142. InitialAAadvantage.016171
shrinksfinal.002203(~13.6%descriptive retention);CAdeclinealreadyatfitstart-.001321,
thenadditional-.000067throughjoint. Notuniqueenergy-termcausalattribution.
FitmeanrawMSE .351191->.075093A²;all14improvefittingloss. FinalheavyRMS.52280->.43749A,
CArms.22930->.26267A,maxatom4.61868->3.53564A. BetterallatomrawMSEdoesnotguarantee
bone/GTquality. Do notautotunefitweights/iterationsonthispanel orpromotefitteddefault.
Alllocalfits60iterations/63-65closures;mean2.78s. Joint13*180,one179;closures208-233.
Newjointmedian18.18/mean22.02s;fit+jointmedian21.16/mean24.81s. Historicalcontrol
median19.71/mean23.16s notconcurrenttiming;noequal-total-computeorspeedclaim.
PeaknewRSS~.87GiB. Nooptimizerconvergenceclaim,solverinputgradientsstilldetached.
28NumPypose/metrics/objectiveaudit max2.15e-10A/8.33e-16/5.69e-13;14samechart/objective
pairs. OldC4read-onlyaudit28pass+601existing summaryleavesexact;oldC1audit28pass.
88archivefiles+archiveSHAverifiedlocally. Reports/mini_c4_fitted_start_2026-09-30,
findingsdocs/mini_c4_fitted_start_findings_2026-09-30.md;overallfrontupdated;PNG/PDF.
CurrentcombinationCLOSED,notwholeproject. KeepcalibratedZEROstartasdevelopment
reference. Nextmethodrequiresclearbackbone-preservation/allowedlocaldegreesof
freedomandseparatebranchuncertaintydefinition;noautomaticsweeporrewritingoldgates.
Originalgoal remainsactive/unfulfilled,independent32rejectionunchanged. No new
numericalbackwardbugevidence;don'trestartFDdebuggingortrainthisfailedcombo.

## 2026-09-30 — Frozen calibrated objective confirms partial quality recovery on C4/S1

Previous goal turn was no progress toward method development: it rechecked the
already completed independent32 source extension. This turn made concrete progress:
implemented/ran/audited bounded C4/S1 confirmation of9f1393cd, no new tuning/training.
Same8 development sources/two seeds12345,54321;3CR6 covalent chemistry skip retained.
7 MI250 GCDs generated14 native ESM2/Mini FP32 C4/S1 outputs, no MC dropout,
identity-key noise,identity augmentation,stableEuler,[2560,0],gamma0=0,lambda=eta1.
Four conditioning cycles shared perprotein;two1-NFEpredictions plusoneexactreplay.
7/7 replaysbitwise,counts4/3,weightSHA before/afterunchanged.7workers55-56s each
including~49s load;peak11.3GiB. Notpurelatencybenchmark or independentfullmodelreplay.
DiamondHill /media/PM982/onestepfold/c4_connection_confirmation_v1_20260930:
pipeline211226/rawcontroller211230/CPUcontroller212025 all terminal;pipelineexit0,
28successful repairs,4sourceskips,0processfailures. Do not restart these handles.
Same chemistry,calibrationq95,rawselectedbranches,zerochart,2CPUFP64workers,3x60LBFGS,
900s ceiling. All28runsto180limit,notconvergence. NoGTmodel/objectiveinputs.
Raw/original/calibratedAA .825157/.802069/.812698;CA .900142/.896529/.900591.
PairedAA+.010629,CA+.004062;14/14predictions and7/7proteinmeans bothpositive.
NewAAstillraw-.012459;newCAraw+.000449. Botharms14/14zeroseverepairs,strictchecked
CA+ILE/THRchirality,RMSbudget;raw28severepairs,9/14strictchirality. Oldjoint14/14
->0/14;newoldconnectionfails CN0,angleC10,angleN14,omega14,carbonyl0. Empirical
onsetsnotnewgates. Bothnew/oldabsolute_failures empty. Maxpen1.86482->1.79503.
Rawbranchmismatches2both4B9Pindex121(P122-P123)persist inbotharms;posthocread
confirmsraw/finalcis-like(+1),GTtrans-like(-1). NoGTbranchreplacement. LocalinitAA.802942;
calibratedrecoverspartofinitloss. MeanCArms.28252->.22930A,heavy.62511->.52280A;
maxatom4.71073->4.61868A. Median solve17.65/19.71s,means20.56/23.16;
closures194-211/218-232;equaliterationsnotequalcompute. PeakRSS~.88/.85GiB.
28NumPypose/metric/objectiveaudits pass(max2.72e-10A/8.33e-16/5.12e-13),14paired.
Updatedaudit also passes old28archive innewshadowdir,oldreportsuntouched. C4hasno
historicalrepairbaseline:explicitNonecontract;do notcount0replaysasfailedchecks.
Boundeddevelopmentscreentrue,NOTdeployment,independentgeneralization,differentiable
solverorjointacceptance. Originalindependent32rejection staysfrozen;notreused/tuned.
Findings docs/mini_c4_connection_findings_2026-09-30.md;overallfrontupdated;
reports/mini_c4_connection_confirmation_2026-09-30 includesfullreport,audit,locks,
summary,pairedCSV,PNG/PDF andplotcode. Raw/parameterarchive118members3004024bytes
createdremotely,thenSSHtemporarilytimedout(directandHPC3jump);SCPsession69089
terminal255 connectionreset. Connectionrecovered,singleSSHtartransfercollectedall
remainingfiles. Archiveoverall+118memberSHAsverifiedlocally;collectioncomplete.
Noexperimentrestart. collection_status.json recordsresolvedtransfer.
Post-exit auxiliarypssubstring scanner matcheditsownshell andoverwrote remote
launch.json/pipeline.pid with214965/214966;localcollectedlaunch retainsverified
211226/211230,CPU212025. Noneareliveexperiments;neverrestart214965. See
launcher_note.json;badremotemetadata preserved andverifiedterminalIDsrestored.
Next boundmethoddecision: preserveaccuratelocal
fit withfrozencalibratedobjective,whilebranchselectionremainsseparateproblem. Do not
expandtargetsortrainsolverdistillationyet; no newFD/backwarddebugging. Goalactive.

## 2026-09-30 — Calibrated connection onset intervention completed: partial quality recovery

Previous goal turn64ccaf4b was progress: independent64 experimental calibration.
Current locked trial mini_connection_window_trial_v1 compared original and
calibrated trans dead zones with old denominators/curvature, unchanged raw-selected
branches, chemistry, tailtop16, regularization, zero pose start and3x60LBFGS budget.
Cis-selected edges retainalloldonsets. Usespooledq95fromcalibration32only,no per-case
GTsolverinputs. No new inference/training/GPU/independent32reuse/acceptancechange.
Historical8sources,twoC1/S1noises each:3CR6cov-link skip4slots retained;28solves
successful,0processfailures. DiamondHill /media/PM982/onestepfold/
connection_window_trial_v1_20260930 controller205790 terminal;batch/audit/report exit0.
Two singlethreadCPUworkersFP64,900s ceilings; no livejobs fromthisbatch.
AA raw .773584 ->originalfinal .753066 ->calibratedfinal .760832(delta+.007766).
CA raw .848037 ->original .846704 ->calibrated .849866(delta+.003162).
14/14 predictions and7/7 proteinmeans improvebothqualitymetrics; recovery37.85%
ofoldraw-relativeAAdrop is descriptive,notallerrorcausalapportionment.
CalibratedAAstill.012752belowraw. Originaljoint13/14 ->calibrated0/14,oldgatesretained.
Newoldwindowfails:CN0,angleC12,angleN14,omega14,carbonyl0. Empiricalonsetsnotnewgates.
Botharms14/14zeroseverepairs,strictcheckedchirality,globalRMSbudgets. Calibrated
oldabsolute_failures empty14/14;maxpenetration1.90007 vs2.21670old,maxbondRMSE.00480,
maxpeptideMAE.01194. Notcompletephysicalchemistrycertification.
Rawciswrong2remain (4A02/12345label34->35,3D8L/54321label32->33). Old3D8L/12345
introducedanotherbrancherror;newavoidsit,ending3->2errorsbutnotfixingrawcis.
CA RMSmean.334->.304A,heavy.761->.695A;maxatom9.000->11.045A(3D8L/12345label3NZ).
Allnew180iterations,old13at180andone39;notconvergence. Medianseconds17.37/18.29,
mean20.52/22.53;newclosures208-230. PeakRSS~.88GiB,equalcapsnotequalFLOPs.
14baselineoutputsbitwisehistorical;28NumPypose/metric/cross-objectiveauditpass
max1.43e-10A/1.67e-15/2.73e-12,14pairedinput/bufferchecks.2local+remoteobjectivetests
pass.88filecasearchivehashverified. Findings docs/mini_connection_window_findings_2026-09-30.md;
reports/mini_connection_window_trial_2026-09-30 includesJSON,pairedCSV,PNG/PDF,archive.
Predeclaredboundedconfirmationscreentrue(bothqualitymeansup,safety-countnotdown),
NOTdeploymentoroldjointpass. Freezeonsets;nextpriorityboundedC4/S1inputconfirmation,
notq/weight/iterationsweep. Initializationinteraction,cis/transuncertainty,and
short/differentiablecorrectionremainseparatework. Originalindependent32rejection
unchanged,originalgoalstillactive/unfulfilled. Do not reopenbackwarddebugging.

## 2026-09-30 — Independent experimental connection calibration completed (64 sources)

Previous goal turn3b10f921 was progress: seven-source GT constraint/branch audit.
This turn completed outcome-blind source selection, raw-catalog extension and
calibration/held-out measurement onDiamondHill CPU. No optimizer/model/GPU/training.
Original TRAIN search379 eligible ->43 selected (11<=1.5A,32at1.5-2A).
Full256shard HPC3 catalog mirror:3001 eligible groups ->first1024hashranked;
391sequence-isolated ->46sourcepreflightpass ->21added.345sourcefailures retained.
64final sources:32perresolution stratum,alternating32calibration/32held_out.
44monomer/20homomer chain sources;length56-451,resolution.92-2A. Full-source
extension release<=2021-09-30,no temporaltest. Historical21070+reserved32+recent8
PDB/accession/BLAST isolation and panel HSP exclusions checked. Source context
is confounded with resolution; not an assembly effect comparison or pretraining
exclusion. Calibration64 now reserved for distribution work,not fresh repair validation.
Remote roots /media/PM982/onestepfold/connection_calibration_v1_20260930,
connection_calibration_extension_v1_20260930,connection_calibration_measure_v1_20260930.
All processes terminalexit0.64/64 measured,11058connections;mappingmax8.81e-6A,
Gemmi phase9.16e-16. Calibration5621edges:4102active1882oldgatefail;held5437:
4198active1678oldgatefail,all32chains eachrolefailoldwindow. Missing sidechains/
disulfides allowed for backbone calibration only; no native chemistry support claim.
Fit commontrans absolute q95/q99 oncalibrationonly beforeheld evaluation. NonPro
omega q95/q99 chord.197406/.284436 =11.329/16.352deg;heldq99coverage99.0015%.
Oldomega onset2.865/gate5.732. Otherterms differ:nonProCNq99.027352 held98.10%;
ProCNq99.028873 held96.24%. Protein-weighted vsedge-weighted sparseProtails differ.
Do not turn empirical quantiles directly intochemicalgates or claim99%guarantee.
37cis-likeGTedges (cal21,held16),5nonPro includes2highB1LMI and3nearideal phases
1QB7/1H6L/1RMG; rarecisdescriptive only, no all-nonPro-trans rule.
Proteinbootstrap2000draws seed9302026;zero-variation100%CI notcoverageguarantee.
Local4tests pass,remote3statistical tests pass. Offlineaudit165archivedfiles,
64GTidentityhashes,26264HSPs,40window/coveragechecks passes.15.2MB sourcearchive
includesallselectedGT,sourceevidence,HSPs;per-edgeCSV/report/plots saved locally.
Findings docs/mini_connection_calibration_findings_2026-09-30.md;overall updated.
Next: bounded continuous-connection-scale intervention usingindependentcalibration,
separatecis/trans uncertainty; keepoldgate reporting andquality/clash/chirality.
No intervention yet, no quality recovery or deploymentclaim. Independent32 rejection
unchanged. Mainline objective remainsactive/unfulfilled; no livejobs fromthisbatch.

## 2026-09-30 — Experimental connection audit closed: constraint calibration and branch selection

Previous progress adcc7c1a: joint warm-start did not retain local-fit quality gain.
Read-only DiamondHill audit now completed at
/media/PM982/onestepfold/connection_gt_audit_v1_20260930 (exit0; no active job).
Same locked 8 development sources, 7 supported; 3CR6 covalent-link exclusion retained.
7 unique experimental GT,14 historical native C1/S1 predictions,28 prior joint outputs:
49/49 independent geometry checks pass;814 unique GT edges,5698 total CSV rows.
No new solves, GPU forward, training, changed thresholds or independent32 access.
GT source identity/altloc mapping verified from original mmCIF; proper rigid alignment
max5.47e-6A. NumPy vs frozen production residual max6.11e-16 onGT,9.26e-9 overall;
Gemmi phase max8.96e-16.3 focused tests pass locally and onDiamondHill.
GT677/814(83.17%) edges activate current penalty;321/814(39.43%) exceed old gate.
All7 GT fail full-chain connection gate, including high-resolution4A02(.95A;82/165).
Omega phase onset2.865deg/gate5.732deg;452active/228rejectedGTedges.
Omega62.66% of pooled scaled connection penalty is NOT contribution to lDDT loss.
Pinned official AF2 constants/violation implementation documented as scale reference,
not adopted gate and not complete AF2 evaluation. GT is not error-free physical truth.
Two raw branch mismatches in1628 prediction edges:4A02/12345 label34->35(I),
3D8L/54321 label32->33(E): GTtrans,rawcis-like, both initialization arms endcis.
All4 final structures pass old joint gate because branch was fixed fromraw.
GT also has2 cis-like Pro connections; do not force alltrans.2/1628 not prevalence
or explanation of allqualityloss. No atom mapping/phase sign bug found.
Report docs/mini_connection_gt_findings_2026-09-30.md;protocol,lock,fullJSON,
per-edgeCSV,summary,PNG/PDF,external reference hashes and artifactmanifest retained.
Next meaningful method task: independent geometry calibration and handling uncertain
cis/trans branches under a new locked protocol; no more initialization tuning or
loosening old gates post hoc. Keep independent32 rejection and genuine clash/chirality
failures. No backward debugging reopened; mainline goal active/unfulfilled.

## 2026-09-30 — Joint warm-start comparison closed: initialization benefit not retained

Previous goal turn was progress: experimental-GT local fit completed/pushed953b40fe.
Current turn tested only initialization, on the same8 locked historical C1/S1
sources (7 supported,3CR6 covalent-link exclusion retained),2 cached noises.
Protocol mini_projection_joint_start_v1.md. DiamondHill
/media/PM982/onestepfold/joint_start_dev_v1_20260930 controller194335 finished,
batch/audit/report exit0:28 successful solves,4 source-skipped slots,32 planned.
Original raw PoseVariables and TailObjective anchors/regularizers preserved;
fitted arm copies saved q, not a rechart.14/14 input/buffer pairing verified.
No frozen solver/chemical constructor edits, no GPU/model inference/training/32 access.
FP64CPU,2singlethread workers, same3x60 joint iteration caps, extra60 localfit
iterations counted for warm arm.2 focused tests pass locally and onDiamondHill.
AA lDDT raw .773584,zero-start final .753066,warm final .753510:delta+.000444.
Warm start .767987 -> final .753510 loses most of prior initialization gain.
CA finalzero .846704,warm .843219 (delta-.003485).Jointpass13/14 ->12/14;
both-noise proteins6/7 ->6/7.1pair gains,2pairs lose. All28 finalzero severe
pairs,checkedchirality andRMSbudgets pass; warm4B9P bothnoises fail penetration
2.0746/2.0731A despite distances>=1A. Old3D8L/12345 failsconnection/penetration,
warm repairs it.7protein AAmeans5improve/2decline,CA6decline/1improve.
28independent NumPy pose/metric audits pass(max1.77e-10A/4.45e-16).
Old13cases180jointiterations,one3D8L39(30/7/2 stages),not convergence;warmall180.
Median jointseconds17.34old/16.62warm,extra recordedlocalfitmean2.80s.
Predeclared bounded-C4-candidate screen FALSE: jointpass decreased. Close this
initialization version; no extra iterations,weight search,automatic C4 rollout,
LoRA or mutation search. Original independent32 rejection unchanged.
Findings docs/mini_projection_joint_start_findings_2026-09-30.md; report/audit,
pairedCSV,qualityPNG/PDF and hash-verified archive saved. Goalstillactive/unfulfilled.
Next meaningful inquiry: audit joint chemical/connection constraints against
experimental GT and the quality tradeoff; not assume initialization is solecause.
Previous7rawGT already failed strict ideal connection gate; keep thresholds and
oldresults unchanged while diagnosing. Do not claim global infeasibility or a
backward bug. No new experiment beyond this closed batch is running.

## 2026-09-30 — Experimental-GT local fitting development completed

Previous goal turn was no progress (data/status restatement). This turn executed a
new bounded source-locked GT comparison under the standing mainline instruction.
Protocol docs/mini_local_projection_gt_development_v1.md; findings in
mini_local_projection_gt_findings_2026-09-30.md. DiamondHill root:
/media/PM982/onestepfold/local_fit_gt_source_v1_20260930 (terminal, batch/audit exit0).
Historical native ESM2 Mini C1/S1, NOT C4; seeds12345/54321, lambda1.003; no new
model inference/GPU/training. native_reference means prediction, never GT.
640 historical sources ->55 eligible ->first8 unique PDB/accession by group hash.
Reserved32/PDB/accession and calibrated BLAST isolation passed; no warning/HSP
exclusion hit. 7 complete native/experimental heavy-atom mappings passed chemistry;
3CR6 rejected for Lys132 NZ–nonprotein CAF covalent link. Do not replace it.
21 fits completed out of24 planned inputs,3 source-skipped retained. All60 iterations,
62–66 closures, same frozen representation and equal-atom raw MSE objective.
GT self AA-lDDT:1 ->.968419(old) ->.996713(fit).
14 cached predictions AA:.773584(raw) ->.754925(old) ->.767987(fit), about70% of
projection loss recovered. All14 improve vs old, all14 still below raw.
CA:.848037 ->.848037 ->.846234. Backbone-to-raw MSE worsens; sidechain improves.
Checked chirality21/21 and local chemistry preserved; connection0/21; native
severe pairs raw/old/fit58/61/68. Even rawGT connection0/7 under the strict ideal
connection thresholds; do not call this proof of erroneous experimental GT.
21 independent saved-pose and metric audits pass (max1.77e-10 A/4.45e-16).
Data/chemistry/fit artifacts backed up in2.5MB archive,172 files roundtrip hashed.
Independent32 rejection unchanged, set not rerun. No solver-input gradients/design
utility shown. No further fits launched. Next bounded question: compare old vs
fitted initialization for joint solver on SAME original raw PoseVariables chart
and SAME JointObjective/regularizer anchors; account for extra60 fit iterations.
Do not rebuild zero variables around fitted coordinates, change weights, tune on32,
or claim cachedC1 results validate C4. Needs own execution lock before running.
Goal remains active/unfulfilled; current turn is progress (new empirical GT evidence).

## 2026-09-30 — Old-six CPU local fitting completed, no GT recovery claim

Prior goal turn was progress(prepared code+3synthetic tests). Continued recommended
bounded diagnosis under standing mainline task; unanswered optional preference was
not treated as explicit user approval. Protocol mini_local_projection_fit_execution_v1.
DiamondHill local_fit_dev_v1_20260930: controller186778 now terminal, exit0;6/6cases.
Same old parent194res, controlledS1/nativeS5 three seeds each. No new model forward,
GPU, training, experimentalGT, independent32 access or joint-solver integration.
Same chemical manifold/frozen constructor; one60iter FP64CPU fit with2singlethread
workers. Raw-coordinate MSE falls80.56–85.67%,all194residue totalMSE improves ineach
case. Local bonds/angle cosines within7.4e-15; allchecked chirality preserved.
BUT backbone-to-raw RMS increases inall6; sidechain fit supplies totalgain. Joint
geometry0/6, chain/clashes notresolved; raw closer != GTaccuracy recovered.
6/6independentNumPy replay/metric audit(max3.55e-15/4.44e-16); 3runtime tests pass.
All use60iterationcap,63–64closures,~3.3s recordedcase time; no optimality/convergence
claim. Outputs/values/report locallycollected and hashchecked.
Report docs/mini_local_projection_fit_findings_2026-09-30.md, overallreportupdated.
Next meaningful question is experimentally scored development comparison including
GTself-projection and native-prediction projection, excludingreserved32andnearsets.
Needs bounded source/mask protocol; do not reflexively rerun32oraddweights/budget.
If integrating later, warmstart originalPoseVariables with fittedq and keeporiginal
objectiveanchors; rebuildingchart around fittedcoords changesregularizer too.
Batchclosed; do notpoll/restart186778. Goalactive/unfulfilled,currentturnprogress.

## 2026-09-30 — Local projection fitting draft and synthetic implementation prepared

Previous goal turn was progress: completed independent32 negative validation, localized
AA quality loss to initialization, published faf6e469. No old job should be restarted.
Current turn adds standalone local_projection_fit.py, reusing unchanged PoseVariables
and chemical constructor. One fixed-start60iteration/90max-eval LBFGS raw-coordinate
fit; final-only, no best/fallback, no input gradient or chain/clash enforcement claim.
3focused CPU synthetic tests pass (stationary feasible input, distorted-anchor fitting
with invariant chemistry/proper equivariance, invalid-input rejection). Synthetic THR
fixture MSE .147043 -> .022858 in16iterations/18closures; NOT a realprotein result.
Draft docs/mini_local_projection_fit_draft_v1.md defines old6case CPU diagnostic only,
independent32/near sequences untouched. No source/model/solver changes, no real-protein
batch, no GPU/new prediction/training. The user preference question (minimal localfit
versus discuss other representations) is pending. Prepare only until direction clear;
do not claim draft execution or experimental precision recovery. Next implementation
would need locked old6 inputs/driver/report; then separately defined GT development
source before any accuracy claim. This goal turn is progress(code/tests/reviewable
protocol), not blocked; overall differentiable design objective remains unfulfilled.

## 2026-09-30 — Independent32 finished; continuation rejected, loss localized to initialization

Authoritative batch/audit/score exit0, analysis exit0; all known processes terminal.
96raw/192repairs complete,64/64independent CPUaudit,96/96input/initial pairing audit;
612frozen file hashes match. Main pipeline52.3min. No missing GTscore/supplement error.
Raw/Mean/Tail jointpass0/62/80of96;all3protein0/18/23of32. Tail misses24protein gate.
AA-lDDT raw .771294, mean .749082, tail .748187; tail delta-.023107,bootstrap95
[-.026423,-.019406],24/32delta<-.02. Both geometry and quality screens fail.
Rawjointpass0 means good-input retention N/A, not100%. Tailchirality96/96,no new
checked flips,RMSbudget96/96; local backbone/sidechain moves reach13.51/17.14A.
Remaining16tailfails allconnection;9severe cases are4FMA/1N81/6N9Y across3noises.
Read-only posthoc saved-initialization scoring all96: initialAA .749192,CA unchanged.
Initial-raw -.022102; tail-initial -.001005 (CIcrosszero). Main quality cost precedes
joint optimization. Atom-centre additive decomposition verified; no new GPU outputs.
Full reportdocs/mini_independent32_findings_2026-09-30.md; overall front updated.
Metadata archives+perresidue tables hashes/roundtrip verified, PNG/PDF inspected.
This batch is CLOSED, no tuning/retries/automatic distillation on32. Suggested next
question: lower-distortion proper/chirality-preserving local fitting on development
cases, keeping32and near sequences excluded; specific method/protocol still to discuss.
No new GPU batch, no reliable differentiable output/design utility established.
Goal staysactive; this turn is progress(final results+scientific localization+report),
not blocked and not full-goal completion. Do not poll/restart ended PIDs169720/169722/
174093/183809. Results remain in independent32_v2_20260930 and
independent32_analysis_v1_20260930 under/media/PM982/onestepfold onDiamondHill.

## 2026-09-30 — Raw96 artifact audit complete; paired repairs still running

Verified live DiamondHill pipeline169720/controller169722 and analysis waiter174093
at03:27HK;96/96raw,96/96mean,93/96tail computational outputs. No restart or tuning.
Independent artifact audit96/96: native atom identity/order, finite FP32 coordinates,
sequence, locked model/config, four conditioning cycles shared across seeds, one
structure evaluation per seed, identity-key noise/augmentation, fixed ODE settings.
This checks artifacts/traces, not independent model replay or geometry/GT acceptance.
Added exact mean/tail input+initial-coordinate audit: first90/96pairs pass; remaining
protein reports not yet complete. Run again after all repairs. Analysis copy only;
original frozen runtime untouched. Overall report front now reflects32 and livebatch.
New plotting script prepared but not yet run; do not cite a figure as completed.
Next: wait for original exit.json; inspect CPUaudit+GTreport, run final pairing audit,
collect supplement, export/inspect plot, report frozen screen and source/length tails.
Batchroot/media/PM982/onestepfold/independent32_v2_20260930;
analysisroot/media/PM982/onestepfold/independent32_analysis_v1_20260930.
Goal remains active; current turn made progress and has verified running handles.

## 2026-09-30 — Independent32 live; read-only reporting supplement queued

Revalidated live pipeline169720/controller169722 on DiamondHill, no restart.
72/96raw and134/192repairs completed at latest check; no worker errors observed.
Added separate reporting supplement: full permitted-pair penetration distributions,
per-residue movements/local observed lDDT changes/new checked chiral flips,
raw-pass retention vsraw-fail repair, per-protein triplet means/bootstrap, length
and source subgroups, actual closure/time/memory costs. Original runtime/code and
continuation gate untouched.4focused tests pass locally and in runtime.
Queued CPU-only independent32_analysis_v1_20260930 PID174093 waiting for original
pipeline terminal artifact; verified live. No new GPU trials/tuning/training.
Original batch and final quality conclusions remain unfinished. Protocol
 docs/mini_independent32_analysis_supplement_v1.md; do not mark goal complete.

## 2026-09-30 — Full-source search completes32;8-GCD validation launched

HPC3 full244406-entry catalog available, raw83GB;256 catalog shards byte-identical
with DiamondHill. Monomer alternatives891 groups/1336records yield0 supported new
long chains. Full catalog census478groups/3789chains→154isolatedgroups/766records→
125source-supportedgroups/591records, all contextual.47supportedhomooligomer groups;
predeclared first8 pairwise-isolated native chemistry8/8pass. User explicitly allows
homooligomer-derived complete chains. Add3VSV-A638,5JVL-A874,3F6B-A525,6P63-C595;
retain28exact, now8/8/8/8. Scope label28monomer+4homooligomer; no relaxed isolation,
chemistry, masks or temporal cutoff. No autonomous-monomer/pretraining exclusion claim.
DiamondHill independent32_v2_20260930 data/runtime locks, frozen2aa geometry bytes.
8GCD launched PID169720/controller169722:96C4S1 raw+192mean/tail repairs, autoCPUaudit
and experimental scoring. First8 raw triplets complete; no final quality conclusion.
Missing old solver scripts restored beforeGPU with preliminary manifest preserved.
Isolatedtmtools0.3.0 officialwheel SHA verified; runtime3tests pass/local10pass+1skip
covered remotely. Reportdocs/mini_full_source_search_findings_2026-09-30.md.

## 2026-09-30 — User-authorized source extension retains28;32 lock incomplete

User explicitly chose extend sources to32 before validation. StageB complete TRAIN
extension148 candidates→15 isolated→10 source-supported medium proteins; fixed1F06
320aa adds to original27, strata8/8/8/4. Raw pre-cutoff monomer representative universe
841 long groups checked in frozen256 then remaining585 batches:158 isolation-eligible,
156 incomplete experimental backbone, remaining1DAB/3KTT recorded chain breaks.
No new qualified long chain; preserve28, no silent trimming/imputation/relaxed gates.
No Mini/ESM/GPU inference, repair or training. All batches complete. This exhausts
chosen representative universe, not all PDB variants/all possible sources. First
StageB runtime import failure preserved; corrected isolated package v1_1 succeeds.
Report docs/mini_validation_source_extension_findings_2026-09-30.md. Need additional
source policy or explicit dataset-contract decision before32x3 can start.

## 2026-09-30 — Sequence isolation calibrated;27 chemistry-qualified candidates

Geometry frozen2aa87043. New predeclared BLAST2.17 rule adds significance to
30%identity/70%shortcoverage/50aligned residues plusstrong-domain exclusion.
32exact/crop/mutation20/natural controls allrecover intendedparents;mutation60
also32/32descriptive;320shuffles0hits. Originalv1zero-selection untouched.
Firstbuild rejected64charIDs beforesearch; newv2_1 reversible32charaliases,
verifiedofficialdownload/binaryhashes.217pool→175excluded→42homologyeligible.
All42CPUchemistrypreflight,39supported;1BJ4/1C75cofactorcovalent,6WI6cyclic excluded.
Greedystrata final27(8/8/7/4),length69–634,no modelqualityselection. Immutable
provisional list/masks/nativeinput hashes ready; original32protocolnotmet,noGPU.
480calibration decisions,candidateexclusions,panelisolation independentlyrecomputed.
User preference question offered28 beforechemistry;latestqualifiednumber27supersedes.
Next decide27x3 boundedvalidation vsnewsourceextension for32;noautomaticthreshold
relaxation/training. Reportdocs/mini_isolation_calibration_findings_2026-09-30.md.

## 2026-09-29 — Independent geometry validation selection v1 stops before inference

User approved freezing 2aa87043 and independent32x3 raw/mean/tail validation.
Front-page overall report now distinguishes positive6/6 pose solver from old99
force-field baseline. Protocol locks isolation, length strata, noises, budgets,
GT metrics and continuation screen before outputs. DiamondHill source-only screen
used192single-thread CPU workers,21070excluded sequences plusPDB/SIFTS exclusions.
217source-eligible candidates all rejected by existing30% aligned-residue identity/
70% shorter-coverage rule. Posthoc one-shuffle control stillhits74/217; suggests
specificity limitation, not proof alloriginalhits false or no independentdata.
No thresholds relaxed, no predictions/solver/training started;32panel notformed.
Stopv1, preserveartifacts; nextcalibrate isolation innewversion, keepgeometryfrozen.
Report:docs/mini_anchored_independent_screen_2026-09-29.md.7focusedtests pass.

## 2026-09-29 — Worst-pair contrast passes six fixed geometry cases

User authorized mainline continuation; permission interruption occurred before jobs.
Added independent TailObjective (top16 excess penetration over1.9A,scale.1A) to old
mean objective; base/pose/scoring unchanged. Same six raw inputs/initial states,
3x60 iteration caps, fresh initialization. All6 workers finish0 on DiamondHill.
All6 jointpass,0 severe pairs, all checked chirality and connection limits pass;
S1 old6/2/3 severe ->0/0/0. S1 CA RMS.368–.430A/heavy.934–1.019A. Maxatom11.24A,
maxrotationvector1.327rad remain caveats.33–35s/case,189–200closures,not equal FLOPs.
Independent audit6/6, NumPy pose replay1.33e-10A; initial arrays exactly matched.
5tests pass. No solver-input derivative, design utility, independent-target or
convergence claim. No new training/search. Next gate is independent protein panel
before short-map learning; not started. Report:docs/mini_anchored_tail_findings_2026-09-29.md.

## 2026-09-29 — Anchored joint geometry feasibility and data inventory

User approved per-residue global anchors with joint connection/repulsion. Implemented
PoseVariables + bounded LBFGS diagnostic; no sequence search/training/Mini forwards.
Six DiamondHill GCD workers finished normally (~29–31s each incl init), all stages
hit60 iterations. All6 retain RMS budget, CA/ILE/THR handedness and added connection
limits. NativeS5 all3 jointpass/0 severe; S1 residual severe6/2/3,maxpenetration>2A.
Independent NumPy/SciPy output replay max1.33e-10A, CPU jointaudit3/6. No convergence,
through-solver derivative, design utility or independent-protein claim. Max atom
movement up11.57A/max rotation vector1.19rad retained as important limitations.
Batch finished; no auto-retune. docs/mini_anchored_geometry_findings_2026-09-29.md.
User also requested downloaded sequence locations. Live HPC3 audit verifies76273
unique/nonempty UniProt mapped FASTA records in1526batches and244406PDB filenames,
exact manifests, no partials. NOT fullUniProt. HPC2 rawroot also exists. DiamondHill
29769TRAIN+128DEV acceptance and ESMC547shard multi-layer cache confirmed. Locations:
docs/protein_data_locations_2026-09-29.md; no new data download or split changes.

## 2026-09-29 — Connected output prototype implemented; direct rebuild stopped

User authorized starting the next output method. Added fixed-graph ConnectedOutput:
proper local CCD reconstruction + raw phi/psi + ideal links + trans omega + carbonyl
plane. No training, new sequences or folding forward. Six parent control S1/native S5
archives on DiamondHill CPU; 14.85s execution. Initial constructor rejected terminal
OXT before outputs; preserved lock/log, new v1.1 supports terminal-only OXT.
All six CA and checked ILE/THR handedness correct, chain constraints exact; but aligned
CA RMSD12.54–18.13A, clashes54–187, all preservation/geometry gates fail. NumPy phase,
geometry/hash audit six cases passes; local AD/FD passes. No phase-sign bug found.
Stop direct whole-chain torsion rebuild; next design must retain global residue pose
anchors and jointly handle connectivity. No additional methods launched. These are
same-parent regression examples, no quality/generalization claim. Findings/protocol:
docs/mini_connected_output_findings_2026-09-29.md; docs/mini_connected_output_v1.md.

## 2026-09-29 — Close raw-gradient plus generic repair version

User review accepted: current frozen Mini + soft local ranking + hard mutation +
restrained force-field repair has no established joint design utility. Numerical
AD evidence remains positive; do not reopen backward debugging or infer Mini/one-step
impossibility. Stop old candidates/repair tuning/LoRA; next method must first define
chemically constrained output with matching gradients and preserved pretrained prior.
Old99 outputs are regression cases, not clean teachers or independent validation.
Clarify future audit fields: vector/component force RMS separately, no termination
claim. Reader accepts old archived names; original locks/results remain unchanged.
No new experiment or remote mutation. Overall report section9 records closure.

## 2026-09-29 — Final collision/repair batch collected; overall report

User requested current status plus overall Markdown report and push. No new model
runs, training, repair, or protocol changes. All99 repairs and finalanalysis complete;
controllers exit0 and no remaining related process.99CPUrecomputations exact.
Read-only archive check verifies99cases/360files:rawinputs/atommapping/fullprojection
exact, finiteoutputs, source/forcefield/report hashes bound.
All99 zero severeclashes and preservationpass;49absolute/jointgeometrypass,50fail
CAchirality.68structures have newflips;134new,38corrected,30persistent CAinstances.
MeanCA/heavyRMS.615/.827A;maxsingleatom6.880A.80/99 meet recordedforce diagnostic;
no claim allminimizationsconverged. Bothgradient/random repairedutility0/16 andfull0/16.
Y38T loses benefit vsrepairedparent:confirmtaskdelta+.00054835/+.00102310.
C4S5 remainscompleted:nativepasses2/3,onehas3severepairs;not S1-exclusivefailure.
Overallreport:docs/onestepfold_overall_report_2026-09-29.md;finalcompactartifacts:
reports/mini_geometry_repair_2026-09-29/final/. Ninefocusedtests pass.
Batchclosed; reliableone-stepdesign/geometrypreservation notachieved. No nextjobs.

## 2026-09-29 — Existing repair batch live; automatic outcome analysis attached

No new experiments or parameter changes. Verified live controller39918 plusfour
CPUworkers. Partial analysis6/99: all6 finite,zero severeclashes,preservationpass;
absolute/jointgeometry3/6,other3failchirality.3structures have7newCA flips total,
3old flips corrected. This is a completion-order subset,notprevalence.
New offlineanalysis computes CA-centre new/corrected/persistent transitions,
namedpair overlap,geometryfailure reasons and finalcandidate distributions;
originallocked pipelineunchanged. Ninefocusedtests pass. Separate collector
finish_repair_analysis.py waitsfororiginalfinalreport, runsanalysisonce thenstops;
8hcollectiondeadline doesnotkillrepair. No automaticretry/restart/nextmethod.
RootDiamondHill:/media/PM982/onestepfold/geometry_repair_v1_20260929.
Expectedfinal:outcome_analysis.json/.md alongsideoriginalreport.json.
Goalremainsactive/incomplete pendingfinalbatch; respectuser's boundedtonightscope.

## 2026-09-29 — C4/S5 collision control COMPLETE; repair first positive

User requested original C4/S5 and bounded stopping tonight (no endless debugging).
Same parent3seeds: exact archived controlledS1 replay; controlledS5 severe19/8/10
→5/1/0, still maxpenetration2.88/2.06/2.16 fails. Native runner C4S5 severe0/0/3,
absolutegeometry passes2/3; seed200009 has128O–129C .714A,128O–129O .678A,
132O–159OH .808A. NativeMCdropout true only200009: not causal evidence.
9CPUreplays exact. No newmutations, no next ablations tonight.
Repair case0(parent211) finished398s:19→0 severe,maxpen3.228→.490,bond.237→.041,
peptide.128→.00594;CArawRMS.581/heavy.792 passespreservation,maxatomshift4.19A.
Case002(parent200009) also0clashes butchirality.988827 fails: H41/L163 newly
flip, K194 corrected. CA.613/heavy.754 passpreservation. BothcasesCPUauditexact.
Two-case evidence only; rest99batch running4CPUworkers, autoauditandstop.
No new methods/parameters tonight; user prefers discussing unresolved issues tomorrow.
Rawanatomy shows backbone–backbone clashes, notonlysidechainpacking.
Report:docs/mini_collision_localization_2026-09-29.md. S5 rootDiamondHill:
/media/PM982/onestepfold/c4s5_collision_v1_20260929. No further GPU jobs needed.
Overallgoalactive: remaining repair evidence pending; no deployeddesign claim.

## 2026-09-29 — Restrained geometry repair v1 authorized and locked

User approved advancing beyond the closed mutation batch. New development-only
intervention uniformly repairs all99 archived hard structures (33 sequences/3noises),
no new predictions/substitutions/training. Independent Amber ff14SB+GBn2 OpenMM
CPU minimization, original-heavy harmonic k1000kJ/mol/nm2,2000 iterations,tol10;
no task loss in repair. Original topology/identity preserved; OXT/H auxiliary only.
Old geometry/utility gates unchanged; new raw-frame CA<=1A/heavy<=2A preservation
limits locked before outcomes. Compare repaired candidate against repaired parent,
both confirmation noises; failures retained, no tuning/reranking. Full batch CPU4
workers/2threads, isolated OpenMM8.6.1/PDBFixer1.12.0 dependencies.8tests pass.
Protocol:docs/mini_geometry_repair_v1.md. DiamondHill root:
/media/PM982/onestepfold/geometry_repair_v1_20260929. Initial case executing;
scientific outcomes pending. This is not a differentiable one-step deployment.

## 2026-09-28 — Existing hard-batch reanalysis COMPLETE (CPU only)

No new predictions/candidates/training/gate changes. All33 native CCD topology
rebuilds exact; atom mapping/radii/193peptide bonds verified; independent<=3bond
exclusion sets match. All99 maximum/severe collision metrics reproduced.
Parent/Y38T maxpairs DIFFER for all3noises; sharedsevere pairs1/1/0. Y38T
confirmmaxpairsM171:CE-Q191:N(.335A),V21:C-Y22:CG(.419A),graphdist63/4.
Y38T seriouscount10→13 under200009 stillwithinpresetnonregressiontolerance.
No evidence found for checked scoring/topology mapping error; coordinates overlap.
Selected15Y38 scoring vs hardtotal Spearman:-.568dev,-.600/-.496confirm,
-.657confirmationmean (task-.711). Lower/lower shouldpositive: selected-range
hardranking mismatch, not backward defect or fullspace inference. KeepY38Tweak
localutility, no generaladvantage/accepteddesign. Stopbatch unchanged.
Report:docs/mini_hard_mutation_reanalysis_2026-09-28.md; namedpair/rankingTSVs
andhashedJSON inreports/mini_hard_mutation_utility_2026-09-28/reanalysis/.
6focusedtests passed. No ESM/PF/diffusion runs in reanalysis.

## 2026-09-28 — Hard mutation utility COMPLETE, stop batch

Recovered afterhostreboot; all4workers exit0,99hardpredictions andCPUauditdone.
Frozen16gradient+16random,controlonly,noadditionalcandidate/seed. BOTHconfirm
noises utility(taskimprovement+geometrynonregression):gradient1/16,random0/16.
Fullhardaccept0/16botharms. Gradientmean taskdelta+0.00053495 vsrandom+0.00278479;
bothmeans worsen, medians-0.00016116 vs+0.00096734. OnlyutilitycandidateY38T:
confirmdeltas-.000181095/-.001326579,stillfailsabsolute maxpenetration.
Small descriptive localsignal,not generaladvantage orvaliddesign;15gradient
proposalsatY38. Nativehardgeometry remainsblocker;deploymentrejected.
99CPUcoordinatechecks maxerror2.38419e-7. Recoveredbatch136.625s inclloading;
proposal8.393s excludesfailedpreflights/setup. ALLJOBSFINISHED,doNOTrestart.
Report:docs/mini_hard_mutation_utility_findings_2026-09-28.md.
Remoteartifactrootunchanged.Noextraexperimentswithoutnewdecision.

## 2026-09-28 — Hard mutation evaluation RECOVERED after reboot

DiamondHill reconnected with uptime~1min. Old workers absent; all4 reports at
load with0 results and0 coordinatefiles. Preserved interrupted run under
attempts/reboot_interrupted. Candidate hash unchanged; no gradient/proposal
rerun. Detached recovery controller restarts only99hardpredictions onGCD2–5,
20s stagger, then automatically CPUscore if allworkers succeed. Firstworker
entered sequence0; laterworkers loading. Root and protocol unchanged.
Recovery script:scripts/recover_mutation_evaluation.py. No new candidate/seed.

## 2026-09-28 — Hard mutation utility batch SUBMITTED, outcomes pending

One control alpha.001/C4S1,16gradient+16random(RNG6271), zero overlap,
33native sequences × noises211/200003/200009 =99 hard forwards. Candidate
manifest hash b08f6bb6eaf3fc62d43b757853ac4f352f9ae077f3c718541dce155f4e1fcdfb.
15gradient candidates concentrate onY38; oneR45P. Do not diversify/rerank.
Preproposal hand-FP32 softmax chain check failed; independent nativepullback
exact and FP64formula within conservative FP32roundoffbound. Preservefailure;
actualgp used directly, nearhardcoordinates archiveexact. InterveningROCm
launchfailure archived. Frozenmanifest submitted to4GCD(2–5),PIDs1855646–9.
Latestretrievedstatus loading; subsequentSSHstalled. Do NOT resubmit unknownjobs.
RootDiamondHill:/media/PM982/onestepfold/mini_hard_mutation_utility_v1_20260928.
Next collectexit/workerreports, runscore_hard_mutation_utility.py CPUaudit,
reportseparate task+nonregression vsfullaccept onBOTHconfirmationnoises.
Stopafterbatch, no extra seeds/candidates/training/thresholdchanges.
Docs:docs/mini_hard_mutation_utility_status_2026-09-28.md.

## 2026-09-28 — Recycle1 and original-q composition COMPLETE

User-approved bounded follow-up reused archived endpoints (no reselection).
Recycle1(MSA1+PF16) now has positive local precision consistency evidence:
all15 rows forward-secant precision dominated; maxAD32/64relative1.68174e-5;
FP64JVP/VJPmax5.21e-15. Full VJP offline relativeL2: ESM25–36 5.68e-6,
initialization4.61e-7,recycle1 2.44e-6; explicit identity subtraction also reported.
Original3logits directions propagated by true JVP through liveESM/fullERC,
init,C4: all18 boundary primals exact and projected responses consistent.
Native diffusion efficient SDPA lacks forward AD, retained as unsupported.
Bounded local math-SDPA suffix comparison supports complete true-tangent
composition: max original-q JVP/nativeVJP relative discrepancy0.00158519;
math/native diffusion fullVJPrelativeL2=5.87e-6. Not fullnativeforwardAD orFP64.
Native full forward/reversegradient exactly replayed archives. No remaining
boundary discrepancy above locked criterion at this point; end mechanicalFD
segment searches. Softdistortion/graphswitch/hardgeometry/designutility remain
separate; deployment rejected, noLoRA/training/productionprecision changes.
15focusedtests pass;CPUrecomputed30localrows+21boundaryprojections+3suffixrows.
AllGPUjobs finished successfully; do notrestart. Report:
docs/mini_recycle1_composite_findings_2026-09-28.md.
Large tensors:DiamondHill:/media/PM982/onestepfold/mini_recycle1_composite_v1_20260928/.
Next research decision is bounded hard-mutation utility under fixed local chart
and hard geometry acceptance, not more numerical repair without new evidence.

# Decision log

## 2026-09-27 — User requested192 single-thread structure workers

DiamondHill256logical CPUs/128physicalcores,~1TiB RAM. Original16workers each
~98%CPU despite4auxthreads (~3.2GiB RSS). Userauthorizes192workers ifnointernal
threadpool multiplication. Migratedwithoutchangingselection/labels: terminateonly
controller1617246 andits16knownworkers; leaveoldrsync1617257 alive. Retain2677
completepackets, quarantine16interruptedfolders in scale192/incomplete; theyare
reprocessed. Immutablecode_v1 andoldlogs retained; code_v2 onlyadds torchinterop1
and192-wayacceptance. Retainedpreparedhashes boundtooriginalsource inmanifest.

NewcontrollerPID1618918,192children recordedin scale192/launch.json. PyTorch
intra/inter-op1;OMP/MKL/OpenBLAS/BLIS/NumExpr/Rayon1. Eachworkerandits existing
threads pinnedtoone logicalCPU;192live/single-core affinities confirmed. CPU
runtimeinitialization resetone earlyaffinity, soallthreads reboundafterstartup;
record scale192/affinity_check.json. NoGPUtraining. Startuphealth:166workers had
progress,sum3545 includingretained, noTracebacks;RAMused555GiB/available452GiB,
swap~1MiB. SMTandI/O canlimit speedup; no12xpromise.

Remote /media/PM982/onestepfold/scratch_structure_data_v1_20260927/scale192.
Newcontroller waits192workers thenwaitsoldrsync, runsidempotentrsynctoensure
complete8320reusedpackets, thenv2full29897acceptance. Inspect scale192/exit.json,
pipeline_exit.json androotacceptance.json; oldruncontroller isNOTlive. Snapshot
reports/scratch_structure_data_v1_20260927/scale192. Afterpreparationaccepted,
analyseformerHPC3cycleandpresentnextplanhere, noautomaticnewtraining.


## 2026-09-27 — Requested follow-up AFTER structure preparation acceptance

User explicitly requests this order: (1) finish andaccept currentDiamondHill
structurepacket preparation; (2) analyse theformer-cycle HPC3 task results;
(3) present thenext-cycle plan inthisconversation. Do NOT automaticallylaunch
thenexttrainingcycle. Thisupdates theearlierstructure-onlyscope ONLYto permit
post-preparation resultanalysis/planning, notnewtraining.

Latestchecked preparation:16CPUworkers haveprogress,1397/21577newpackets,
noTraceback inworkerlogs; acceptance.json absent. Waitfor actualcompleteacceptance,
not justworkerprogress. TheninspectHPC3 lockedcontinuation655518/655519 andaudits/
scores/report655520–655524 plusfixed-tail655531, preserving original4096primary
and16384extension meanings. Include othercompleted scratch diagnostics onlywith
clear labels; do notmix pretrained-adaptation results withscratch capacity claims.
Reviewtrainingfit,DEV AA/CA/TM means,fixedhardtargets/rerankedtails,chemistry,
equalupdates/equalexposures/cost, andindependentacceptance status. Finallypropose
onebounded nextcycle consistentwithscratchprimary/final-only/oldsmoothweight10,
full29769TRAIN andDiamondHill preference; present uncertainties andactualreadiness.
Reporthere beforeany nextcycletraining launch.


## 2026-09-27 — User restricted this turn to STRUCTURE PREPARATION ONLY

Do not startTRAIN32 oranymodeltraining underthisrequest. Previouslyprepared
scratch_train32_rocm entry andscratch_primary batching/LRhelpers remainunfinished
trainingwork;6batch/schedule tests and1GPU smooth test passed, tmtoolsdependency
installed inisolatedscratchprimary/deps, butNO TRAIN32launch occurred.

Started CPU-only structurepipeline onDiamondHill:
/media/PM982/onestepfold/scratch_structure_data_v1_20260927.
ControllerPID1617246, reuse-rsyncPID1617257; launch.json authoritative.
Fullselection29769TRAIN+128DEV; reuse8320acceptedHPC3packets (~180GiB) viaDH->HPC3
pull; prepare21577newTRAIN locally. AllnewrawmmCIF/shardpaths present.
FrozenfullselectionSHA2ba7f5771dc7f9f1042930aa14e840f523f7b29dd6435018bfc041cdd1726198;
newSHA b1b8a66b677989be644e48cf65217fa38fd1ac863ccaa8d519dce395253489a1.
Sixpacket smoke20/257/321/427/1022/1024 passed bothCPUworkers exit0.
Controller nextchecks178finalESMCshardhashes, launches16CPUworkers, waitsforreuse
transfer, thenfullfile/metadataacceptance. Acceptance.json onlyafterall29897pass.
ROCR/HIP/CUDA visibilityempty; noGPUfolding execution oroptimizer.
Newpackagesinclude smoothlabels; oldacceptedpackagesnotmodified. LargerDEV-primary
andoldsmoothsidecars stillpending, do notclaimfullmaintrainingreadiness.
Docs/scratch_structure_preparation_v1.md and reports/scratch_structure_data_v1_20260927
carrycontroller/selection details. Do notduplicatejobs oroverwritepartiallyprepared
folders; inspectreportsfirst onresume. Failuresmustnotcause silenttargetdrops.


## 2026-09-27 — User-provided DiamondHill feature dataset accepted; main plan reconciled

User identifies /media/PM982/onestepfold/data/esmc_29769_layers_12_24_36_v1_20260927
as the dataset. All three transfers and destination verifier exited 0. Read
transfer_acceptance.json: 29,769 groups, 547 shards, 8,830,652 residues;
all shard hashes and tensor shape/dtype/finite checks passed. Merged manifest SHA256:
ecbaf57b6b89d6a6fe85ee1684ace62d4f3c4c3e243dbb09f299d6b0792b275d.
Cross-hardware numerical compatibility and structure training packets remain unaccepted.
Fixed Biohub HF source confirms hidden_states[36] and last_hidden_state both
use post-norm norm_x; extraction removes padding/BOS/EOS identically. New layer_36
is a final-only candidate without re-extraction or extra LayerNorm, subject to
numerical compatibility checks; TRAIN coverage does not establish DEV coverage.
Updated primary plan: prioritize DH 8 GCD x micro1 x accum2, compare same-host
4 GCD x accum4 at global16; retain HPC3 fallback. Reuse prior 4 GCD short-chain
pretrained DDP evidence, but separately validate scratch/smooth/1024/accumulation/
tail/true process restart. Budget names now distinguish GCD-hours from H100-hours.
This handoff updates documents and archives acceptance only; no training launched.

## 2026-09-27 — DiamondHill selected for scratch-main feasibility preflight

User asks whether scratch main can run onDiamondHill. Livecheck8GCD idle, each
~64GiB, disk~2.8TiB free. Existingfold torch2.12dev/HIP7.14 andprior128/256
coreforward/backward checkavailable. Candidate8GCD micro1 accum2 keepsglobal16;
9-real-example tail scalesloss8/9, same1861updates/epoch and50epochLR trajectory.
NoGPUmemorypooling assumption or8-card speedup claim. Updated mainplan placement.
Finalcache exists25GiB/178shards butneedsfullhashQA; oldGTtransfer hasonly605
entries andno data_acceptance.json. Mainlinefinal-only isindependentofMLCtransfer.
Mustpassscratch+smooth TRAIN32,full-lengthmemory,8rankaccumulation/tail/resume
andfullpacketacceptance beforeformalmainlaunch. Thisturnchecks/plans placement;
no newscratchjob submitted yet. ExistingHPC3lockedjobs remainunchanged.


## 2026-09-27 — Draft of full scratch primary training

User asks to implement overallprimarytraining iffeasible and FIRST draftaplan.
Draft delivered in docs/scratch_primary_training_v1.md; thisturn performed
read-only readinesschecks andplanning, no data merge ornew training job.
FullTRAIN29769 finalcacheexists, butonly8192TRAIN+128DEV packetsaccepted;
21577newTRAIN packetsremain (5373<=256aa,16204>256aa). MLC547shards complete
andmetadata-accepted, notfulltensor/cross-host-accepted; final-onlymainline
neednot waitforMLC. Preserve allrunninglockedcontinuationjobs.

Proposedmain: randomcore/projection seed101, frozenESMC600M final1152,
16Pairformer/8structure rawXYZ, c1/s1/K1, oldloss+10smoothlddt. OneTRAIN32
candidate fitcheck plusfullpacketprep/newtrainer inparallel, thenfull-length
20–1024/largeatom/pair GPUcheck andbounded200update DDP/resumepreflight.
Main startsfresh, notfrommemorized4/32 weights. TRAIN32 islearnabilitygate,
notnewproof ofrelative superiority; matchingbaseline requiredforsuchclaim.

Defaultcandidate4H100/acd_u, micro1*accum4 =>global16.29769 means1860full
batches+9realexamples intail =>1861updates/epoch; DDP real-sample scalingW/N,
no drop_last orfakeexposurepadding. ExistingpretrainedDDP andscratch4 runners
cannot supportthisviaflagsalone; implementationneeded. Preservefull-length,
validategradient-equivalent memory optimizations ratherthansilentlycrop/drop.

Candidate50epoch researchceiling=93050updates/1488450samples. Firstexecution
segment atmost5epochs or24h optimization, actualhoursestimatedonlyaftermixed
lengthpreflight; thisdraftisnotalaunchedjob orconvergenceclaim. Predetermined
warmup1000/cosine50epoch schedule, uniformscratchlr1e-4,wd1e-4,clip10,dropout0.
DEV128 remains historical; define largerDEV-primary fromreserveddevpool and
prepareitslabels/features beforemain. No frozen-test access. Tail-awareselection
andper-proteinchemistryreported; finalmean.89–.90/P1>=.7remaingoals, notpromises.

## 2026-09-27 — User authorized rsync of extracted ESMC features to DiamondHill

Target /media/PM982/onestepfold/data/esmc_29769_layers_12_24_36_v1_20260927,
~58GiB across547 shards,29769 sequences. Hostonline,disk2.9TiB available.
Threeconcurrentrsync transfers started; X570part000 direct, Precisionpart001/002
DIRECTto pc@10.120.16.9, noX570relay. Controller unifiedsession15137, childPIDs
871414/871415/871416. Exactcommands in
reports/esmc_29769_extraction_2026-09-27/diamondhill/transfer_jobs.json.
Code, lock, sequencegroups andselectionreport alreadycopied. Partial files retained;
no source/deletion operation. Never startduplicates withoutchecking these processes.

Controller waits forsuccessfulall3 then runs destinationCPUverification: everyshard
SHA256, BF16/shape/finite values, residueoffsets andexactdisjoint29769coverage;
createsmergedrelative-path manifest andtransfer_acceptance.json onlyafterchecks.
Local transfer_exit.json andverification_exit.json distinguishsuccess fromfailure.
Atthisentrytransfer is RUNNING, not complete. Cross-device numericalcompatibility
andlongchainstructurepacketQA stillpending. No training authorized/launched by
thistransfer handoff. See diamondhill/README.md for recovery andreadiness rules.


## 2026-09-27 13:36 HKT — User-requested progress check only

All3 ESMC12/24/36 extraction partitions complete: R9700 9887 groups in856.8s;
Precision GPU0 9957 in2492.3s, GPU1 9925 in2558.9s.547 shards total.
Downloaded completion metadata/manifests; verified each manifestSHA, exactunique
29769-group union, disjoint hash partitions, sequence hashes/lengths andthree layer
names. See reports/esmc_29769_extraction_2026-09-27/completion/status.json.
NOT full tensor checksum/finite-value acceptance orcross-device compatibility;
longchain training packets also not accepted. No new jobs started onthisstatuscheck.
HPC3 acd_u jobs655518/655519 running, cumulative13072/12560 of16384 at~13:35;
remainingtraining estimate~52/64min atobservedaverage, scheduler-dependent audit/
CPUscore/report stillpending. No new quality conclusion fromunscored checkpoints.
Previousbackup c1fac23f isnow syncedto origin/main. User's earlierstopboundary
remains: statuscheck does not authorize autonomousnext-stage training.


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

## 2026-09-19 — Close the bounded Stage0 confirmation with accepted results

All 1536 repeats and 768 locked new-target predictions completed, scored and
passed independent execution QA (repeat634067, confirm634068). The three
prespecified directional intervals exclude zero: c4_s2−c4_s5 lDDT+.00776;
c2_s2−c4_s2 lDDT−.00724; mean log warmtime ratio−.53606 (ratio.585).
TM-style losses >.05 for c2_s2 vs c4_s2 occur in13/256; no equivalence claim.
Four repeat seeds all rank c4_s2 first in mean TM/lDDT. No best-of-seed,
post-test tuning, configuration expansion or extra target selection.

Final lock634028 preceded frozen metadata access; selected256 disjoint from
all1024dev, seed127. Those256 coordinates now used for scoring; remaining2184
coordinates unused here. Deterministic numerical policy, original MC=.4/.4,
per-target seed reset and fixed sequence-only packets disclosed; not exact
replay of old A800 sequential RNG. Preflight failure/diagnostic retained.

Each phase used16 shards, confirmation maximum8 simultaneous H100s under the
16GPU user quota alongside8 scaling jobs. Total1.612GPU-hours including prep,
failed preflight and diagnostics; first prep to final QA36.1min. All Stage0 jobs
terminal; no more runs required by this protocol. Final report and figure:
reports/stage0_confirmation_2026-09-19.{md,png,pdf}. Protocol/progress and current
memory updated. Scratch scaling remains a separate ongoing experiment, and
the overall one-step folding research goal remains open.

## 2026-09-19 — Execute minimal confirmation; increase target parallelism

User said continue to completion and then explicitly requested more GPUs to
reduce wall time. Same 1536 repeat predictions partitioned over 16 GPU workers
(four seeds × four target shards), with all three settings paired on each
target's same GPU. Planned 768 confirmation predictions also use 16 target
shards. No setting/seed/target or best-of-K expansion.

Root HPC3 /data/user/shuang886/Folding/stage0_confirmation_v1_20260919.
Preparation633989 created all128 sequence-only packets but failed hook/plain
coordinate tolerance. Diagnostic633997 demonstrated nondeterminism even for
plain/plain replay with original deterministic=False (c2_s2 max difference
about1.03A on the shortest development target), so the discrepancy cannot be
attributed solely to timing hooks. Original artifacts preserved. No relaxation
of tolerance: v2 preflight633999 uses deterministic numerical kernels and
requires atom-exact plain/plain and hook/plain replay. Sampling settings and
MC dropout remain original (gamma0=0, eta=1, lambda=1.003, MC=.4/.4).
This numerical-policy change and per-target seed reset must be disclosed;
the new paired protocol is not exact replay of the old sequential RNG stream.

Inference source code_v2 immutable; code_v1/preparation inputs retained.
Repeat jobs634001..634016 submitted afterok633999; CPU scoring634017 depends
on all16. All job IDs recorded reports/stage0_confirmation_2026-09-19/jobs.json.
Frozen-test files still unread at submission. Do not unlock until repeat
scoring and final execution lock are complete. Do not duplicate active jobs.

## 2026-09-19 — Narrow Stage 0 to a minimal K=1 confirmation

User explicitly restricts the next Protenix-Mini round to existing nine-cell
reanalysis, independent c4_s5/c4_s2/c2_s2 repeats, matched timing and locked
new-target confirmation. No method-tree expansion or R×S×K sweep. This is the
Stage 0 inference line, not a change of the active scratch model architecture;
existing scaling jobs are not cancelled by this instruction.

Protocol: docs/stage0_minimal_confirmation_v1.md. Reanalysis completed on all
9216 original scores; reports/stage0_confirmation_2026-09-19 contains source
hashes, dual-reference statistics, per-target compensation and repeat_lock.json.
Repeat targets reuse the original metadata-stratified 128 before score selection;
new seeds 103/107/109/113, K=1, exactly three configs (1536 inference budget).
Old joint-tail/control counts are 6/122, 9/119, 9/119 for the three core pairs.
Report all seed distributions, never best-of-seed. Original TM is Kabsch
TM-style; original all-atom lDDT includes intraresidue pairs, unlike scaling.

Actual resolved sampler/sigma schedule/solver/step scale/extra noise, hardware
and cache protocol must be captured before repeats. They are not yet captured
in an immutable execution lock; no new GPU inference was submitted this turn.
Frozen-test files remain unread. Only after execution protocol lock, select
256 new targets by metadata strata/hash seed211 and run three configs, seed127,
K=1 (768 inferences); no test-based configuration selection. Prespecified
directional confirmation and multiplicity handling are in the protocol.
No recurrence/depth/decoder/sampler branch follows automatically.

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

## 2026-09-19 — Accept requested gradient-transmission/root-cause report

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

## 2026-09-18 — User requests detailed gradient/root-cause report

Protocol docs/esmc_articulated_gradient_trace_v1.md fixes a read-only diagnosis:
all128 saved initial/selected coordinate cases, four weighted loss gradients,
translation/orientation/internal chain-rule decomposition, raw geometric scales,
same-output retracted-Jacobian counterfactual and independent NumPy finite
differences. Follow with selected checkpoint TRAIN35/166 actual model gradients
(one bounded HPC3 GPU audit), no optimizer updates. Differentiate coordinate
mechanisms, parameter gradients and untested AdamW/convergence hypotheses.
Two focused factor-additivity/translation/Gram tests and lint pass. No GitNexus
tool/index is available; direct accepted-source tracing is used. No training
weights/settings/data masks or accepted execution sources are changed.

## 2026-09-18 — Accept completed articulated training and pose/shape diagnosis

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

## 2026-09-18 — Epoch 75 comparison: C–N becomes the limiting joint gate

HPC3 job 632192 remains RUNNING (scheduler verified at 35:47 on ACD1-23).
Latest archived training/evaluation: epoch 75, 2,400 updates; provisional selected
checkpoint: epoch 75. Both seeds give atom RMSD 5.578644/5.582286 A,
CA-distance RMSE 3.692503/3.685236 A, and consecutive C–N RMSE
1.695238/1.686307 A. N–CA/CA–C/C–O remain 0.021327/0.046526/0.039083 A;
eligible handedness is 100%, and training fallback counts remain zero.
Both runs currently select epoch 75: Cartesian control 631937 has worst-seed
atom RMSD 4.180549 A and C–N RMSE 1.141953 A, versus 5.582286 A and
1.695238 A here. Articulated joint score 5.650795 is now limited by C–N error
normalized to its 0.3 A threshold. This identifies the limiting gate metric, not
a proven causal optimization bottleneck. Keep predeclared joint selection/stopping
rules; no quality pass or reason to expand training has been established.
This is provisional training-set evidence only. Same live job/observer verified
through epochs 64–75; no extra training, final QA or shape diagnosis was run.

Do not select a later checkpoint merely for lower atom RMSD if its joint score
worsens. Final independent QA and prepared residue pose/shape diagnosis remain
pending until the fixed training/stopping protocol completes. Original complete
ESMC/all-heavy-atom/confidence/held-out/end-to-end-cost objective remains open.

## 2026-09-18 — Review epoch 25 and prepare post-acceptance pose/shape diagnosis

Further verified wait at scheduler elapsed 17:54: same 632192 RUNNING, epoch
36/1,152 updates archived, latest evaluation/selected epoch 35. Atom RMSD improves
to worst-seed 10.766910 A but C–N worsens to 2.105510 A (epoch 30: 1.701900 A).
Matched control epoch 35: atom 8.157627 A, C–N 1.734079 A. Joint score 11.175349;
preserve joint selection, no atom-only checkpoint substitution or added GPU jobs.
No new diagnostic run; accepted-final-artifact dependency still applies.

Follow-up verified wait: scheduler confirms the same job running at 15:24;
archived epoch 31/992 updates and epoch 30 evaluation. Worst-seed atom RMSD
11.575682 A versus matched control 9.023892 A, joint score 13.022030; no gate
pass or change to training. Observer 39881 remains the only completion observer.
Prepared diagnostic now also emits a readable Markdown table for both seeds and
AA types, linked to full JSON/source hashes. Verified report schema, all 32 input
provenance matches, lint/format and CLI import. Final diagnostic remains unexecuted
until accepted final artifacts exist. This continuation made reporting progress
and verified the live wait; it introduced no additional GPU/fit computation.

HPC3 job 632192 remains RUNNING (last scheduler observation 12:43 on ACD1-23).
Latest archived training/evaluation: epoch 25, 800 updates; provisional selected
checkpoint: epoch 25. Both evaluation seeds give atom RMSD 12.273390/12.259913 A,
CA-distance RMSE 14.204255/14.225541 A, and consecutive C–N RMSE
1.713501/1.693818 A. N–CA/CA–C/C–O errors are 0.021327/0.046526/0.039083 A,
with 100% eligible handedness agreement; all training fallback counts remain zero.
At the same epoch, Cartesian control 631937 has worst-seed atom RMSD 10.276167 A
and joint score 10.550682, versus 12.273390 A and 14.225541 here. Local geometry
is constrained, but a global-coordinate gain has not been demonstrated. Keep the
predeclared training/stopping rules unchanged; no extra GPU experiment.

Observer exec session 39881 is still live for this same job and will perform final
heavy CPU QA and archive/report generation once. Do not duplicate it. Refreshed
provisional curves: reports/esmc_articulated_capacity_2026-09-18.{md,png,json}.

Prepared docs/esmc_articulated_shape_diagnostic_v1.md and
scripts/diagnose_esmc_articulated_coordinates.py for execution only AFTER final
training and heavy QA acceptance. The saved-coordinate CPU diagnosis compares
global error with error remaining after independently fitting a proper pose for
each predicted residue; internal shapes remain fixed. It uses only observed GT,
checks prediction/inventory/label hashes and records diagnostic artifacts/source.
GT-dependent pose correction is not inference or an orthogonal physical energy
decomposition. Reuse accepted reference floor 1.046758 A and numerical articulated
attained fit 0.150398 A; do not rerun either accepted fit. Lint/CLI checks and all
32 provenance matches pass; the new diagnosis has NOT run. Parallel work is limited
to necessary independent preparation/CPU checks, with no speculative GPU grid.
Original full quality, confidence/calibration, held-out and ESMC-inclusive cost
objective remains unfinished.

## 2026-09-18 — Accept initial64 control and begin articulated-output optimization

Initial control forLIVE632192 PASSED beforeoptimization:64raw predictions bit-exact toaccepted631937 and64 adaptedinitial predictionswithinCPU/GPUFP32 maxabs2.47955322265625e-5 A<=5e-5;zero allfallbacks. Independentlocal64array/hash/inventory comparisonalso passes, saved reports/esmc_articulated_capacity_2026-09-18/initial_control_local.json. ActualcontractSHA8f0173cb26c6ba73b40d83fd927fc631db48e5b417334bbb6ac88ddd78c88177 andcontrolfields/acceptedsharedsources verified independently. Traininghasenteredparameterupdates; no trainedqualityconclusionyet. Samejob632192/observer39881 remainsactive, no duplicatejob/observer/finalQA. Report/curves reports/esmc_articulated_capacity_2026-09-18.* areprovisional. Preservefixedsettings andoriginalfullquality/confidence/heldout/fullcost objective.

## 2026-09-18 — Launch the single articulated-output training comparison

LIVE HPC3 training632192, oneH100/8CPU96G/2hhard, code_esmc_articulated_capacity_v1_20260918 -> esmc_articulated_capacity_v1_20260918. The single declared controlled experiment trains fresh through audited parameter-free articulated output with unchanged loss/data/init/optimizer/seeds/budget/gates.93source hashes/actualacceptedsource-control contract preflight/18focusedtests/lint/shellsyntax/CLIimports pass. Initial64rawexact+64adaptedCPUcomparison is enforced beforeupdates; not yet independently observed complete at submission. Do not resubmit.

Completion observer exec session39881 is LIVE for632192 (scripts/finish_esmc_articulated_capacity.py). It only polls existingjob, then runs finalheavyCPUQA once andarchives/reports; no submit/restart behavior. Immutablevalidationcode is samecode_esmc_articulated_capacity_v1_20260918. Localarchive reports/esmc_articulated_capacity_2026-09-18 includes execution93filesource snapshot andcompletion_workflow.json. Inspectsamejob/session and initialcontrol next; do not duplicateobserver/finalQA. No otherGPUexperiment. Keeporiginal fullquality/confidence/heldout/fullcost objectiveunfinished.

## 2026-09-18 — Implement the single controlled articulated-output capacity experiment

Isolated trainer/control/independent finalQA/reporter/observer/Slurm now implemented for docs/esmc_articulated_capacity_v1.md. Only changevsaccepted631937 is audited parameter-free raw->articulated output before existing losses/metrics; samefreshinit/32TRAIN/masks/names/features/optimizer/seeds/precision/fourlossweights/budget/gates/stop. All64 rawinitial exact matches and64 adaptedCPUinitial maxabs<=5e-5 A are enforced before updates. Save raw+adapted coordinates in each initial/selectedNPZ; raw+adapted64 selectedreloadreplays exact, fixedadapterbuffer hashes verified. Log3fallbackcounts and includeadapterforwardcost. Contract bindsacceptedCPU/GPU audits andchemicalgraph; fixedsharedsources/actualacceptedcontract invariants verified locally.

Independent NumPy validation now supportsdeclaredcollapsed/collinearfallbacks as wellasnormal inputs; focused normal/collapsed/collinear comparisonpasses. FinalQA checksraw->adapted128 artifacts, originalheavychemicalrefs/GT/featurehashes, observedfourlosses/geometry/gates/stopping andfrozenheads.18focusedtests/lint/shellsyntax/CLIpreflights pass. Immutable93filesnapshot code_esmc_articulated_capacity_v1_20260918 prepared/hashverified; outputesmc_articulated_capacity_v1_20260918. No newlossparameter/warmstart/parallelGPUgrid. SubmitoneHPC3H1008CPU96G andobserveinitialcontrolbeforeinterpretingtraining. Original fullobjective remainsunfinished.


## 2026-09-18 — Accept GT-free actual-core gradients; fix one controlled training comparison

GT-free articulated output interface and actual-core CUDA audit632148 COMPLETE0:0 in1:21; independentCPUQA passed. No live jobs or optimizer updates. Source/output code_esmc_articulated_output_v1_20260918 / esmc_articulated_output_gpu_v1_20260918. Fresh unchangedcore hashbaad41,35/951 TRAIN inputs, actual1trunk/1structure/0confidence, exacttrain/eval +35rawinitial replay, unchangedweights/features/adapterbuffers. ESMCgradientnorm15.87618/3.08475, finalprojection19870.01/19608.74, rawgradient55.60486/12.59380;413nonzeroparametertensors each. Longestpeak47.156825GiB (short1.100345), fallbackcounts0. Adaptertimings0.21846/0.06132s are singlecold/warm audit measurements, not a latency benchmark or fullESMCcost. Confidence remains frozen/disabled; eventualhead must consume finaladaptedcoords.

IndependentCPU observed-label/mask/source/hash/scalar/NumPyoutput/FP64 raw-gradient QA passes: outputmaxabs1.18e-5 A, projectedgradientmaxrelative2.87e-7, rawgradientmaxrelative1.74e-7, NumPycentralFDmaxrelative4.94e-10. Projectedlossgradientszero outsideobservations; raw gradients can legitimately reach unobserved predicted probe atoms, though these2caseshave0. No missingGTlabels introduced. InitialCPUvalidator stopped on Tensor/NumPy subtraction beforeacceptance; corrected explicitNumPy conversion, same unchangedGPUartifacts/tolerances, noGPUrerun. ReportSHAa91dea42d8b96a606cfcf6fa0a30a8f97c83e8f3006e64daa42f3c836f482995; QAsha8c52bdd57b6b19e52f69e31cca1640a5024c0dd2e7ca0c47d7c0556114384c48 uploaded/remoteverified. reports/esmc_articulated_output_gpu_2026-09-18.md and directory includes actualexecution/QA source,2caseschemicalrefs/GT/labels/raw+adaptedcoords+gradients,log/accounting/hashes/completedworkflow. Do not repeat accepted audit/QA.

CPU interface report07d2b5f5ebdca0c2d4b9193ca989adc49cc16ff6a6fa557d8accbf271a85e8e2: reports/esmc_articulated_output_2026-09-18.md and directory/source/128projectedpredictions, copiedHPC3 esmc_articulated_output_cpu_v1_20260918. All32chemicalinputs/3,979residues/36variants generatedreconstruction FP64max1.64e-14 A/FP32max7.15e-6; idempotence/geometrystable; saved35/166coordinateFD<8.1e-10relative;zero128fallbacks. Parameter-free grouped ArticulatedOutput in src/fastglycan/articulated_output.py uses onlychemicalreferences/inventory/sequence/pinnedCCD andpredictedNCA/Cpose+fixedprobedihedrals, noGTfittedangles/poses/targets/masks. Explicitworldbasisfallforcollapsedframes is finitebutnotrotation-equivariantatdegeneracy. Six focused builder/fit/outputtests andlint/shellsyntaxpass. Do not alteracceptedcore/model/loss sources.

Deterministic postprocessing selected631937 makesworstatom4.18055->4.66058 A andseed12345CN1.14195->1.93888 A, despiteNCA/CAC/CO .021/.047/.039 A and100%CAhand. CApositionsandCAmetricsunchanged. This is not a trainedgain, checkpointpromotion orgatepass. Needlearnthroughinterface.

Next controlledtraining is declared docs/esmc_articulated_capacity_v1.md, NOT yet implemented/submitted: addonlyauditedparameter-free outputadapter to accepted631937 fresh32TRAIN training; sameinit/inputs/labels/loss atom+.1F+R+10D/optimizer/seeds/precision/budget/dualseedjointgates/stop. Require64rawinitial exactbaseline matches and64adaptedinitial CPU maxabs<=5e-5 A; save raw+adaptedinitial/selected coordinates, exactselectedreplays, unchangedinputs/frozenheads/adapters and finalheavyindependentCPUQA. Adaptergeometry largely fixes3distancecategories but coefficientskeptunchangedtoisolateinterface. Logfallbackswithoutchanginggates; finalvalidator must supportdeclaredfallbacks ifencountered (currentauditNumPyhelpercoversnondegeneratecasesonly). No warmstart/grid/extraepochs. Next action implement isolatedtrainer/control/validator/report/observer/Slurm andlaunchsingleHPC3H100 aftercontrolchecks; no permissionneeded. Full originalfrozenESMC/noMSA/all-heavy-atom/onecycle/onestructure/confidence/calibration/formalheldout/fullend-to-endcostobjective remainsunfinished.

## 2026-09-18 — GT-free output CPU checks pass; declare actual-core gradient audit

Implemented parameter-free ArticulatedOutput using only chemical refs/fixed inventory/sequence/pinned CCD graph variants and predicted coordinates. Canonical N/CA/C frame, proper predicted pose, fixed chemical dihedral probes and distal Rodrigues rotations; FP32/64 grouped execution preserves atom order. Fully collapsed/collinear guards provide finite geometry/backward with explicit fallback counts; world-basis fallback is not rotation-equivariant at degeneracy. Six focused builder/fit/output tests and lint/shellsyntax pass.

CPU check on all32 chemical inputs/3,979 residues: generated reconstruction maxFP64 1.64313e-14 A,FP32 7.15256e-6; saved128 predictions zero fallback and maxreferencegeometryerror8.92236e-6. Two saved35/166 coordinate-directional derivatives agree <8.1e-10relative. Labels/masks/atom names unchanged, no fitting/teacher inputs in interface. Postprocessing selected631937 worsens worst atom4.18055->4.66058 A and seed12345CN1.14195->1.93888 A despite localNCA/CAC/CO~.021/.047/.039 A and100%CAhand. CA positions/CA metrics unchanged. Not a trained improvement or promotion; needs training through adapter. CPU reportSHA07d2b5f5ebdca0c2d4b9193ca989adc49cc16ff6a6fa557d8accbf271a85e8e2; reports/esmc_articulated_output_2026-09-18.md and directory/source/128outputs; copiedHPC3 esmc_articulated_output_cpu_v1_20260918.

Before GPU execution declare docs/esmc_articulated_gradient_audit_v1.md: fresh unchangedESMCcore/hashbaad41, accepted35/951 TRAIN inputs, one trunk/one structure thenadapter, actual atom+.1F+R+10D backward; finiteESMC/final-head/raw/projected gradients, exacttrain/eval +35rawinitial replays, unchangedweights/features/adapters, actualmemory/timing/fallbacks. Nooptimizer or pretrained folding weights. Raw gradients may reach unobserved predicted probe atoms; targets/lossmaskremainobserved-only. Confidence disabled/frozen; eventual confidence must use final adaptedcoordinates. OneHPC3H100/8CPU96GB/20min bounded audit, independentCPU label/scalar/FP64derivative/sourceQA requiredbeforedeclaringtraining.73source snapshot code_esmc_articulated_output_v1_20260918 prepared. Original full objective remains open; no speculative grids.


## 2026-09-18 — Accept articulated representability; move to GT-free output interface

Articulated observed-GT inverse fit632103 COMPLETE0:0 in56s onHPC3 debug, actual4CPU/12GB/noGPU. Initial acd_u CPU-only submission was rejected because that queue requires GPUs; explicit debug partition override succeeded, no change to solver/data/budget. Worker used4 independent protein processes and96,262 objective evaluations under declared2-start/80iteration/200hardfunctionevaluation limits; one unsuccessful start retained with best actual evaluation, no retries. No network forward/weight update/heldout read.

Independent NumPy saved-angle/pose/geometry/mask/identity/hash/spectral-pose QA PASSED on32 TRAIN groups/3,809 observed residues/30,437 observed atoms. Pooled attainable all-atomRMSD0.150397917 A versus rigidfloor1.046757701 A; macro0.149195575 A;32/32 proteins<=1 A. Maximum coordinate replay2.84217e-14 A, reference geometry preservation3.48610e-14. Local NCA/CAC/CO RMSE0.021327/0.046526/0.039083 A; consecutiveCN0.093335 A. Eligible CA3579/3579,ILE_CB198/198,THR_CB219/219 hand agreement. Original target masks/names fixed; no missing target fitted/imputed. Independent residue poses are permissive and do not enforce chain connectivity/clashes; low CN residual here is diagnostic only. Numerical attained errors are upper bounds on representation minima, not proven lower bounds or trained quality.

Four focused builder/fit tests plus lint/shellsyntax pass. Source/output code_esmc_articulated_fit_v1_20260918 / esmc_articulated_fit_v1_20260918. ReportSHA8f3c5bb84e265641eb3649a1828b0f753d8f3173c9ffb13e06d0ba7b8ef640e8; QAsha41a9bc4907186708dd7a3b4943d27755c36330f11b82bc624a6074b69efb1af4 uploaded and remoteverified. Local reports/esmc_articulated_fit_2026-09-18.{md,png} and directory includes all32observed coordinate/angle/pose artifacts, accepted reference hashes, actual execution/QA sources, workerlog,Slurmaccounting and completedworkflow. ActualQA source archived; subsequent line-wrap-only formatting in working script does not change its accepted archivedsource. No live jobs or duplicate QA; do not rerun the completed fit.

Next: implement and test a GT-free articulated output interface using only chemical references/inventories and predicted pose/internal-angle information, before more model training. Candidate bridge from current Cartesian decoder: derive residue pose from predicted N/CA/C and internal rotations from fixed-name predicted dihedrals; reconstruct constrained reference coordinates. First verify exact reconstruction on generated admissible coordinates, proper-motion equivariance, missing-label independence, degeneracy handling and usable gradients. This extraction choice is a proposed interface candidate, not an accepted learned architecture or a declared training experiment. The GT-aware inverse-fit solver/angles/poses must never be inference inputs. If CPU interface checks pass, perform a bounded actual one-trunk/one-structure CUDA gradient/memory/replay audit onHPC3 before a single controlled training comparison. Preserve original frozenESMC/noMSA/all-heavy-atom/confidence/calibration/formalheldout/fullend-to-end cost objective, still unfinished. Parallelize only necessary independent work; no speculative loss/model grid.

## 2026-09-18 — Declare bounded articulated observed-GT inverse fit

Protocol docs/esmc_articulated_fit_v1.md is fixed before execution: same32 accepted TRAIN reference/CCD inventories, independent proper per-residue poses, internal bridge angles only. Two starts(zero and observed-dihedral initialization where valid), L-BFGS-B80iterations/200hard function evaluations/start/maxls20/ftol1e-12/gtol1e-8; retain best actual evaluation including zero baseline. No retries/additional multistarts. Four CPU workers,12GB/20min onHPC3, noGPU. Input-dependent GT angles/poses are diagnostic only; no inference conditioning/label imputation/name swaps. Four focused reconstruction/gradient/known-conformation/masked-coordinate tests pass, lint/shellsyntax pass. Snapshot code_esmc_articulated_fit_v1_20260918 prepared; import preflight before submission. Independent saved-variable NumPy replay/geometry/mask/hash/aggregation QA required after completion. Pooled<=1 A demonstrates only attainability under permissive independent poses, not learned quality or peptide connectivity; attained error is not a global lower bound. Original objective remains unfinished.


## 2026-09-18 — Verify fixed-graph differentiable internal rotations before inverse fitting

Fixed-graph articulated-reference prerequisite completed on saved32 TRAIN references, without GPU or GT fitting. Native CCD20 blocks streamed/pinned on HPC3; fullassetSHA bb31ae5cf6c8bc669924313077cb4231ee5ffefd3a20118cd14f3ec89f8bb6a5, subsetSHA fef99e421ab902dde026627fefe32138f006f49a3f9e3711d24a31b1ff87a73e, manifestSHA734d07bf5cba4e931f13e17b0bd7ec767ce3a02967e8ae7f42f4e2b0583d3cf2. Installed ccd.py/configs_data.py and actual extraction source archived; full pickle not loaded. Extraction used stdlib bounded streaming on HPC3; local compact-reference checks used1CPU/noGPU.

Implemented src/fastglycan/articulated_reference.py: deterministic single-bond bridges oriented away fromCA, excluding N-CA and empty distal branches, proper Rodrigues rotations of full distal components in root-to-leaf order. Rings are uncut; carbonylCA-C and sidechain rotations allowed, branches rotate together, no renaming/reference-as-GT. It is a geometry representation, not an energy model; amide single-bond bridges are not assigned torsional barriers. Independent residue poses still do not enforce peptide connectivity. Two focused branched/ring/chirality/equivariance/gradient/invalid-input tests and lint pass.

All3,979 chemical residue inventories (36variants/20AA) map with matching names/elements, connected CCD-induced graphs and fully valid references. Earlier3,809 count was residues with observedGT; no target-mask expansion. Zeroangles exact identity; bond-length/cosine/rigidcomponentdistance errors<3e-15FP64; maxcentralFDgradienterror5.73e-9 on all36variants. Eligible reference/GT handedness matches CA3579/3579,ILE_CB198/198,THR_CB219/219; rotations preserve signed volumes. All32 saved-reference hashes and archived/current execution source hashes checked. Diagnostic reportSHA82b1a7f10bc32f46fe33e11ae0df5e2a5df18c9a2045e1d653d567e862ac960d; reports/esmc_articulation_2026-09-18.md and directory, uploadedHPC3 esmc_articulation_v1_20260918. Graph archive reports/esmc_ccd_graphs_2026-09-18 / remoteesmc_ccd_graphs_v1_20260918. Protocol docs/esmc_articulated_reference_v1.md. No new model, GT inverse fit or GPU training has run.

Next declare a bounded numerical observed-GT inverse-fit solver/budget before executing it, using these pinned graphs and original masks. Attained fit error is an upper bound on the representation's minimum, not a proven lower bound. Only after adequate representability/geometry/derivative evidence consider integrating a constrained output into the fresh ESMC core. Do not rerun accepted diagnostics or launch speculative parallel training. Parallelize independent necessary CPU fits/checks when worthwhile; prefer HPC3. The full original ESMC/all-heavy-atom/confidence/heldout/one-evaluation/end-to-end cost objective remains unfinished; no live jobs.

## 2026-09-18 — Accept distance-supervised negative gate; investigate structural constraints next

HPC3 distance-supervised run631937 COMPLETE0:0 in38:19;95epochs/3040updates, declared plateau20 stop, selected75. Independent heavy CPU QA and local execution/QA/history/all128 prediction hashes pass. Jointscore4.180549>1: seeds12345/54321 atom4.180019/4.180549 A, CA3.017095/3.015147 A, CA-distance3.438506/3.444098 A;0/32atom<=2 A. NCA0.241248/0.238837,CAC0.273451/0.270179,CO0.246484/0.247216,CN1.141953/1.139095 A; hand79.60/79.80%. Same-residue MSE5.455444/5.432639 A², unweighted distanceMSE0.367587/0.365370 A². No extension/promotion/scale-up or automatic loss-weight grid. This rejects this candidate/budget, not every Cartesian architecture.

All64initial matched and64best replays exact; actual1trunk/1structure/0confidence, unchanged inputs/frozen heads;peak2,962,043,904B (~2.759GiB) on shortsubset. QA maxcoordinate2.71315e-6 A,frame0.000239914,same-residue0.000102223,distance0.0000630593 A². Observer83638 finished0/completion_workflow.complete; no live project jobs. No duplicate final QA/observer. Sourcecode_esmc_distance_capacity_v1_20260918/outputesmc_distance_capacity_v1_20260918. ReportSHA8ff68aef2e56d801ce64b1736ab50c4525ff03451090bcd179de1ab5bfe500ab; QAsha43fbe1747e490b4939a6c59237fbaa80294dc96148c64cd1d695bcaf16bcecc9; bestSHA07ffe81827dc063b92075af87483e6dd098ecbb703cb42bd5d8ba96c780e0a36; lastSHA55c573e5af9d8c1e5cb78e2defca7498597ff2f04c1dcc238fe05030eb92848d. Reports/curves/archive reports/esmc_distance_capacity_2026-09-18.* and directory; current actual reporting source archived separately from immutable execution.

Latest-common-epoch reporting corrected to retain an equal-update comparison even when selected epochs differ beyond baseline duration. At shared55, previous631737 versus distance631937: atom3.590827->4.877475 A, CN3.763924->1.388851 A, hand87.3149%->91.5060%, jointscore12.546414->4.877475. Selected35 versus75 is not faster coordinate fitting. Last95 atom3.508625 A but jointscore7.136072, so preserve selected75. Reporting-only change, live/training/QA sources unchanged.

Post-QA independent CPU shape and B-versus10D diagnostics completed concurrently using saved selected64 coordinates, no extra GPU forwards. Residue radii1.153833/1.152367 A versus GT2.196170; centroid3.382608/3.383475 A, centeredinternal2.455712/2.455421 A, ~34.5%SSEinternal. Two-seed disagreement0.303489 A does not establish correctness. B=actual atom+0.1globalframe+same-residue,10D uses actual distance coefficient. MacroB41.4582/41.3692 and10D3.67587/3.65370 A²; median coordinate normratio10D/B0.275084/0.279323,cosines0.124584/0.103722. Negative combined coordinate gradient locally lowers both in64/64 cases; no parameter-gradient/AdamW claim. No coincident distance pairs; analytic distance-gradient error1.49e-16/additivity1.07e-16. ShapeJSONsha9fc91cbd2e09a6a167dcfc62ad853dabc22b21f429b306c7706a12ef545a82a1; balanceJSONsha c1ecd92d45969217baf92a5c4c0f25760ae17fe7c1c587408cb52cefaf068d95. Both uploadedHPC3 and remoteSHAverified. Balance report/source reports/esmc_distance_balance_2026-09-18.*. Old frame-only attribution now refuses distance-weighted contracts; never omit D from the recorded objective.

SpareCPU reference diagnostic631937.0 accepted separately:1CPU/20s/noGPU, all32TRAIN30,437 observed atoms. Exact cached conformers under independently optimal proper per-residue poses have pooledfloor1.046757701 A,30/32protein floors>1 A. Independent saved-reference QA matches8.49e-15 A; reportSHA40909d6dee6f23e5b8f2e0abb542922dafa97e3ff1068324c888e05c54f597e4,QAshab12b023b79cb15771dacbfeb432fe2190be6d5482ec1235e243ed590836264ba uploaded+verified. Reports/source/32ref+GTmask+observedfit artifacts: reports/esmc_reference_shape_2026-09-18.* and directory. Original input/feature/GT/label hashes checked byworker; localQA doesnotreloadheavyfeatures. It is a GT-dependent lower bound without chain-connectivity constraints, not folding inference. Do not train a head restricted only to rigid transforms of these exact cached residue conformers. Internally flexible/torsion heads are not ruled out. Two focused tests/lint pass; six installed runtime source files archived.

Next research action: inspect/pin the fixed CCD residue connectivity and test an articulated reference-coordinate builder with internal bond-axis rotations, proper poses, preserved rings/atom identities/missing masks and explicit handedness checks, before allocating another model-training job. First establish whether that representation can fit the fixed observed GT accurately and has usable derivatives; do not substitute reference coordinates for GT or claim numerical inverse fits are global lower bounds. This is a proposed feasibility direction, not an implemented/newly accepted architecture or a new GPU training protocol. Current failure and persistent internal shrinkage justify testing structural constraints; they do not prove the existing model can never learn them. No new job submitted. Original frozenESMC/MSA-free/all-heavy-atom/one-cycle/one-structure/confidence/calibration/formalheldout/fullcost objective remains active and unfinished.

## 2026-09-18 — Rule out a cached rigid-residue shortcut using spare CPU

Spare-CPU reference-shape diagnostic COMPLETE: HPC3 step631937.0,1CPU,20s,0:0,CUDAempty/no model construction or GPU forward. Reused accepted631737 original cached inputs/GT; original input/feature/GT/label mapping hashes verified, all30,437 observed atoms have valid reference coordinates. Proper independent residue fits give pooledfloor1.046757701 A, macro1.043341771,maxprotein1.111669335;30/32 protein floors>1 A,3,809 observed residues. Independent local saved-reference/mask/identity/artifact/proper-fit QA agrees to8.49e-15 A. Two focused rigid/mask/reflection tests and lint pass. This GT-dependent per-residue optimum does not enforce connectivity and is not a model prediction. It rules out attaining the existing pooled1 A gate using only rigid transforms of these exact cached residue conformers; it does not rule out internally flexible/torsion heads, other references or the current Cartesian model. Do not train that rigid-only shortcut. No new architecture selected or live settings changed.

Protocol docs/esmc_reference_shape_diagnostic_v1.md; sourcecode_esmc_reference_shape_v1_20260918, outputesmc_reference_shape_v1_20260918; local reports/esmc_reference_shape_2026-09-18.{md,png} and directory. ReportSHA40909d6dee6f23e5b8f2e0abb542922dafa97e3ff1068324c888e05c54f597e4;QA uploadedHPC3. Source/saved32 reference+observedfit artifacts andQA hashchecked. Six installed sourcefiles/hashes archived: CCD reference/per-residue pose augmentation; unconstrained linear3D atomdecoder and diffusion combination; frame projection/gather andchi/frame atom indices. Inspected runtime has useful ingredients but no complete constrained reconstruction head. Current631937 training remains the sole GPU experiment; wait its final gate before an architecture decision.

LIVE631937 verified running; archived training/evaluationepoch45/1440updates, current selected45. Jointscore6.077401, worstatom6.077401 A, worsthand92.0369%,worstCN1.625098 A. Local-distance/hand improvements still fail joint quality gate. Curve/report refreshed; same fixed settings/job631937/observer83638, no new GPU variant.

## 2026-09-18 — Track distance/handedness tradeoff and prepare full-objective CPU diagnosis

LIVE631937 verified running; archived trainingepoch17/544updates, evaluationepoch15. Jointscore14.428346, worstatom12.460926 A, worsthand80.6370%; local NCA/CAC/CO/CN=0.3484/0.4178/0.4215/1.1169 A. Compared sameepoch15 baseline, local distances improve; hand recovers to~80.6% after~52% at5, but global/joint gate still fails. Provisional evidence only; keep fixed settings, same631937 and observer83638.

Prepare only post-acceptance CPU analysis while631937 trains: docs/esmc_distance_balance_diagnostic_v1.md / scripts/diagnose_esmc_distance_balance.py measure actual B versus10D on final selected64 saved predictions after heavy QA. B includes atom+0.1global+same-residue terms. Rebuild observed distance labels from atom37, verify scalars/analytic derivatives/additivity/zero excluded gradients and hashes; no GPU forwards or coefficient choice. Reuses accepted independent FP64 audit graph. Old diagnose_esmc_frame_attribution.py now rejects nonzero distance_weight because its frame-only sum would omit part of this objective; old accepted snapshots unchanged. New CLI/import/lint pass; final full diagnostic execution awaits completion/QA. After accepted final result run this concurrently with existing diagnose_esmc_geometry_coordinates.py, then interpret all gates before any next experiment. Live execution/loss/model/QA sources remain unchanged.

## 2026-09-18 — Accept initial64 control and begin distance-supervised optimization

Initial64 control for live631937 PASSED before optimization; independent local64 array/hash/summary comparisons and initial distance-scalar checks also pass. Four-term training log composition verified through archivedepoch3/96updates, latest evaluationepoch0. ContractSHA7f08a4183cb3874eab63839780c841a77723774e48e10f9aee4bc2d594d82314. Provisional reports/curves generated; no trained-quality conclusion yet. Observer83638 remains live for same631937 final heavyQA/archive; no duplicate job/observer.

## 2026-09-18 — Launch the single observed-distance control

LIVE HPC3 training631937: add10*observed-distance MSE to accepted631737 atom+0.1globalframe+same-residue loss; fresh matched32TRAIN/init/noise/optimizer/budget/precision/gates. One H100/8CPU/96G, no GPU grid. Immutable source code_esmc_distance_capacity_v1_20260918; output esmc_distance_capacity_v1_20260918.14focused tests/lint/shellsyntax/78source SHA manifest and actualmatchedcontract checks pass. Initial64 prediction matching is enforced before optimization; not yet independently observed complete at launch. Observer exec83638 (scripts/finish_esmc_distance_capacity.py) is LIVE, polls631937 and will run independent final heavy CPU/four-scalar/geometry/selection QA once, then compact archive/report. No duplicate observer/job/QA. Local prefix/archive reports/esmc_distance_capacity_2026-09-18. Original end-state still unfinished.

## 2026-09-18 — Accept distance gradients and fix one controlled training experiment

Distance audit631888 COMPLETE0:0 in1:40, actual73.951s, no updates. All4cases exact saved/train-eval replay, unchanged model/features,1trunk/1structure/0confidence, peak2.320608GiB. Independent CPU label/scalar/FP64gradient/moment/module/source/artifact QA passes; maxcoordinategradient relativeerror7.60276e-7. Initial35/166 andbest35/166 D/B parameter ratios0.403610/0.427366/0.171419/0.084900; cosines+0.864597/+0.949296/+0.210103/-0.037071. Negative actual unitprobe gradient locally decreases both losses in4/4cases; no AdamW/quality claim. Reconstruction0.0078–0.5481%; no coincident distance pairs. ReportSHA3428d1af5978de4b132ee8a01e0bc6cba4adbfa6a1bc8485f8aad36450a24587; QAsha95183056d6162beedb4ef63f5305f6dcdeb104427111fa5c0157e8e48ccb5ec6 uploaded and remotely verified. Full report/heatmap/4case/source/QA archive reports/esmc_distance_gradients_2026-09-18.* and directory. No live audit/duplicate QA.

Next controlled training declared docs/esmc_distance_capacity_v1.md and implemented: add10*D to accepted631737 loss, all other controls unchanged. Coefficient10 chosen once from saved TRAIN parameter scales (trained ratios1.714/0.849 after arithmetic rescaling; initial4.04/4.27 with positive cosines), not a measured weight10 backward or quality optimum. Samefresh32/init/sampler/optimizer/precision/budget/dualseed gates/stop; require64initialmatches and final independent heavy/four-scalar/geometry/selection QA. No grid/warmstart/scale-up. Four-component logging does not alter selection summaries.14focused tests/lint/shellsyntax pass; actualmatchedcontract and pinned distance-loss source verified. Immutable code_esmc_distance_capacity_v1_20260918 prepared with execution/validation/reporting/observer; outputesmc_distance_capacity_v1_20260918 not yet submitted. Original goal remains open.

## 2026-09-18 — Declare and implement explicit-distance derivative audit

Distance-gradient audit631888 submitted on HPC3, one H100/8CPU/96G/20min cap, code_esmc_distance_gradients_v1_20260918 -> esmc_distance_gradients_v1_20260918. Source70-file SHA manifest and CPU preflight verify remotely. Preserve this job; inspect terminal state then archive and run independent CPU QA once. No additional GPU job or observer is running.

Explicit-distance gradient audit declared in docs/esmc_distance_gradient_audit_v1.md after accepted631737: B=actual atom+0.1globalframe+same-residue loss; D=equal-category mean observed NCA/CAC/CO/consecutiveCN distance MSE; P=B+D unit derivative probe, no updates. Existing moment schema local denotes D. Four initial/best35 x35/166 TRAIN cases, seed12345, one HPC3 H100/20min cap. Actual GT distances only, fixed masks/inventory, no ideal constants or certified-bond claim. Five focused tests pass; all64 selected predictions' CPU preflight exactly matches gate pair sets/counts/scalars (max8.88e-16 A²) and independent analytic distance derivatives (maxrelative1.71e-16). New loss preserves gap/missing masks and finite zero subgradient at coincident endpoints. Frozen source code_esmc_distance_gradients_v1_20260918 includes execution/CPU-QA/reporting and all importable source. Independent final QA checks atom37 labels, scalars/FP64 coordinate derivatives, tensor moments/module aggregation and unchanged replay. No training coefficient/budget is selected yet; no parallel GPU grid. Original research goal remains open.

## 2026-09-18 — Accept same-residue negative gate and parallel CPU diagnosis

HPC3 same-residue capacity run **631737 complete 0:0 in20:18**; independent heavy CPU QA and local execution/QA/history/all128 prediction hashes pass. Stopped55epochs/1760updates by declared plateau rule; selected35. Jointscore9.232090>1, both seeds fail: atom7.725098/7.710630 A, CA-distance7.330022/7.302640 A; NCA0.7686/0.7706, CAC0.8620/0.8636, CO0.6714/0.6718, consecutiveCN2.7479/2.7696 A. Handedness88.71/87.93%,0/32 atom<=2 A. Compared with accepted631592 at the same selected epoch35, handedness improves from~51%, but worst atom error worsens7.1880->7.7251 A. Do not extend/promote/scale up this configuration.

All64 initial controls and64 selected replays exact; inputs/frozenheads unchanged,1trunk/1structure/0confidence; peak2.759GiB for shortsubset. QA metric/frame/same-residue maximum discrepancies2.713e-6 A/0.000239914 A²/0.000102223 A². Observer59184 finished0; no live631737 job or duplicate QA. ReportSHAeb1ee70815f0b6c009879a1db6ea0f6f07c6c4d27b6549ca6928c7b81f746cbb; bestSHA0dd13b6c2b0171636ece7d7edbfc3d701f6227d7abc27c55ea49fbdc6207101a; lastSHAeda28c5f555206c62ee66d6173545a8a5fe1085c7b4dda72167c68ae30a2d2ed. Source/output code_esmc_local_capacity_v1_20260918 / esmc_local_capacity_v1_20260918. Report/curves/archive reports/esmc_local_capacity_2026-09-18.* and directory.

Independent saved-coordinate shape and recorded-weight frame attribution ran concurrently on CPU after final QA, without GPU forwards. Residue radii1.1771/1.1779 A versus GT2.1962 A (accepted631592~1.47 A), centroiderror7.3134/7.2979 A, centeredinternalerror2.4883/2.4888 A; seed disagreement0.652556 A. Same-residue contribution is22.55/22.58% of actual geometry scalar and median same/cross coordinategradient ratio0.7178/0.7622. Direct FP64 weighted-gradient reconstruction relativeerror2.56e-15; NumPy scalar8.53e-14; no frame anchors hit norm floor. This is coordinate-gradient evidence, not parameter/optimizer attribution. Saved reports/esmc_frame_attribution_local_2026-09-18.* include actual diagnostic source. Do not repeat accepted diagnostics.

GT-only observed-distance sanity on same32TRAIN targets:3774 consecutiveCN pairs mean1.330538 A,std0.009775 A,range1.255854–1.402533 A. This narrow target distribution does not explain several-A predicted CN error; no broader chemical-quality claim. JSON/source in reports/esmc_local_capacity_2026-09-18/gt_distance_diagnostic*. No new labels/masks/gates.

Decision: local supervision improved handedness but did not recover correct local distances or global structure; actual geometry contribution is no longer negligible. A further coefficient grid is not justified by these diagnostics. Next research step must distinguish missing explicit distance constraints from limitations of the unconstrained Cartesian output, with a bounded predeclared diagnostic before more training. No next GPU run is yet declared/submitted. Original ESMC/all-heavy-atom/one-evaluation/confidence/heldout/full-cost goal remains open. Parallelize only independent necessary checks or experiments, reuse accepted artifacts, and prefer HPC3 for GPU work.

## 2026-09-18 — Prepare attribution for the actual recorded geometry objective

While631737 remains live, extend only its planned post-acceptance CPU diagnostic:
docs/esmc_frame_attribution_v1.md now records the actual geometry objective
w_global*F+w_same*R separately from the original unweighted F partition. New
src/fastglycan/weighted_frame_attribution.py scales same contribution by
w_global+w_same/pair_fraction and cross by w_global, then checks scalar conservation;
script independently verifies the weighted gradient against direct FP64 backward.
Geometry-only attribution excludes aligned atom loss and selects no new weights.
Three focused tests/lint pass; live training and all shared loss/model sources are
unchanged. Do not rerun prior accepted diagnostics; preserve their archived source.
After final631737 CPU QA, run existing residue-shape diagnosis and this extended
frame attribution on final selected64 predictions, without new GPU work.

## 2026-09-18 — Observe early local-geometry response without changing live controls

Live631737: latest archived training epoch23/736updates, evaluation epoch20, jointscore11.144906, worst-seed atom11.033898 A. Handedness85.2752%/85.2752%; still fails joint gate. Preliminary hand gains do not establish final success. Observer59184 remains live; preserve samejob/controls and wait for final QA.
Early TRAIN hand agreement improves versus accepted631592 but fluctuates; local
bond-distance/global accuracy gates still fail. No new training/coefficients or
threshold changes. Refresh provisional curves and preserve final CPU acceptance
before any follow-up. This is monitoring evidence, not a promoted model.


## 2026-09-18 — Initial64 control passes; same-residue optimization begins

Initial64 control for live631737 PASSED before optimization, then independently
array-compared locally against accepted631592 coordinates/inventories (all64exact,
bothsets prediction SHA verified). Actual immutable execution source hashes and
all shared controls match. ContractSHAece62f9f92c57ec84886930691ec551e240e575ece8d20212008ded47f7da7e2.
Latest archived progress epoch2/64updates, finite meanatom197.835573/globalframe
124.485958/same-residue12.123742/total222.407911. No post-initial evaluation yet in
this snapshot. Localreport/curves generated successfully and inspected; initial
selected0 metrics do not establish trained quality. Continue samejob631737 and
observer59184, no resubmission or duplicate finalQA.

## 2026-09-18 — Launch one controlled same-residue capacity experiment

Controlled same-residue training implemented and LIVE on HPC3 job631737,
one H100/8CPU/96G. Immutable snapshotcode_esmc_local_capacity_v1_20260918,
outputesmc_local_capacity_v1_20260918. Add only unit same-residue frame MSE to
existing atom+0.1globalframe; same fresh initialization/data/noise/optimizer/
precision/budget/joint gates as631592.13focused control/frame/gate tests and lint/
shellsyntax pass. Actual shared model/global-loss/gate source hashes match accepted
631592 and loss implementation matches derivative audit631704. Initial64 exact
prediction and summary matching is enforced before optimization; pending completion
of initialization at submission. Old execution snapshots/results untouched.

Independent validator now recomputes all3loss components, same-residue pair counts/
hashes and selected/initial scalars, as well as previous heavy artifact/FP64geometry/
seed/order/selection/stopping checks; binds accepted631592 and631704 QA/provenance.
Additional local scalar is logged separately and does not alter joint selection.
Observer exec59184 is live, polls only631737 and will run final CPU QA/archive once.
Use scripts/finish_esmc_local_capacity.py, not the older geometry observer. Same
code snapshot contains immutable execution and validation sources. Localarchive/
report prefix reports/esmc_local_capacity_2026-09-18; actualexecution andreporting/
observer sources copied already. No duplicate job or observer. Preserve original
trained ESMC/allatom/confidence/formalheldout/fullcost goal; no success claim yet.

## 2026-09-18 — Local parameter gradients verified; one controlled capacity loss declared

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

## 2026-09-18 — Local-supervision network-gradient audit launched

Local-supervision gradient audit implemented and RUNNING as HPC3 job631704,
code_esmc_local_gradients_v1_20260918/outputesmc_local_gradients_v1_20260918.
No optimizer/update;4fixed initial/best35 x35/166 cases. Separate B(existingloss),
R(same-residue own-denominator),P=B+R backwards on unchanged graph, explicit
base/local/probe moment keys.12focused tests/lint/shellsyntax pass. Four actual
saved-coordinate CPU preflights match independent FP64 coordinate derivatives
with maxrelativeL2 error4.16e-6<declared1e-3. No new training objective selected.
Archive reports/esmc_local_gradients_2026-09-18 with preflight and actualexecution/
validator source; after terminal0:0 run independent CPU QA once. Do not duplicate.

## 2026-09-18 — Controlled coefficient0.1 gate fails; local supervision audit next

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
Implementation/launch pending. Original trained ESMC/allatom/confidence/heldout/full
cost goal active; preserve all labels/masks and one-cycle/one-structure objective.

## 2026-09-18 — CPU frame-pair attribution while controlled training runs

CPU frame-pair attribution on accepted0.001 run631506 is complete. Protocol
`docs/esmc_frame_attribution_v1.md` was declared while0.1 training remained live;
no GPU/model forward/update. All32 selected predictions x2 evaluation seeds, exact
GT/mask/supervision rebuild and artifact hashes, NumPy scalar checks, scalar/gradient
additivity and shortest-example partition finite differences pass. Five focused
frame/attribution tests pass, lint passes; archived source hashes verified.
Same-residue pairs are2.1144% macro of existing frame neighborhoods. Their macro
contributions0.270015/0.271588 out of232.510959/232.344307 A² are~0.116% of the
frame scalar. Median same/cross coordinate-gradient norm ratios0.00144949/0.00134589;
cosines-0.04967/-0.00346. Zero anchors hit the1e-4 A norm floor; minimum projected
N-CA length0.016136/0.009094 A. Cross-residue terms also differentiate local anchors;
this does not causally separate chemistry from folding or establish network
parameter/optimizer behavior. No new coefficient selected from this evidence.
Reports and actual source: reports/esmc_frame_attribution_0001_2026-09-18.{json,md}
and directory. Run the same CPU attribution on0.1 only after final accepted QA.

## 2026-09-18 — Launch controlled0.1 run; initial64 control passes

Controlled coefficient0.1 training is LIVE on HPC3 job631592 (one H100), immutable
code_esmc_geometry_weight01_v1_20260918/outputesmc_geometry_capacity_weight01_v1_20260918.
All64 initial predictions exactly match accepted0.001 run631506 before optimization;
matched_initial_validation.complete=True, contractSHA
c9a634d10f23cd71e39a46e416602ab417c6ebc69372fbffb88ca615b095552b.
Latest archived progress epoch24/768updates; evaluated epoch20 jointscore11.316776,
worst-seed atom11.316776 A. Early curves show lower consecutive C-N error but worse
atom error than0.001; handedness remains near50%. These are provisional TRAIN32
results, not an accepted quality gain. Keep the predeclared stopping/selection rules.
Observer exec76770 remains active and will perform final CPU heavy QA and archive
once; do not duplicate training/observer/audit. QA snapshot
code_esmc_geometry_weight01_validation_v1_20260918; local archive/report/curves
reports/esmc_geometry_capacity_weight01_2026-09-18, with _comparison.png showing
both coefficients. Parallel work is CPU verification/reporting only; no speculative
GPU grid. Original trained ESMC core/confidence/formal-heldout/full-cost goal active.

## 2026-09-18 — Wire the controlled0.1 geometry coefficient

Weight0.1 implementation ready: existing geometry-capacity trainer now accepts
only declared0.001/0.1 presets, with0.1 requiring accepted631506 and631551 QA.
Importable capacity_weight_control verifies same inputs/init/config/RNG/optimizer/
precision/runtime and exact unchanged model/loss/gate source hashes. New run must
match all64 previous initial coordinates and summaries before any optimizer step.
Independent validator checks those controls and the actual weight in training logs.
Thirteen focused control/gate/frame/initialization tests pass; lint/shell syntax
pass. No mathematical model/loss/gate source changes. Previous immutable execution
snapshots/results untouched. One new HPC3 job will run the fixed coefficient.


## 2026-09-18 — Parameter-gradient balance verified; one controlled weight correction

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
beforetraining. No warmstart, no grid/automaticextension. Implementation/launch
pending; original trained core/confidence/formalheldout/end-to-endcost goal active.


## 2026-09-18 — Implement actual loss-component parameter-gradient audit

Implement predeclared parameter-gradient audit: separate backward passes reuse
one unchanged graph per case, with finite coordinate gradients and parameter
moments, module/global norm ratios/cosines and actual-vs-reconstructed combined
gradient discrepancy. No parameter mutation/optimizer. Ten focused gradient/frame/
label tests pass plus lint/shell syntax. Existing best25/last40 checkpoints and
35/166 inputs only; no new data,951forward,trialcoefficient or training epochs.
Independent CPU moment/scalar/provenance QA will follow one HPC3 GPU job.


## 2026-09-18 — Geometry/noise capacity gate independently verified negative

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

Next predeclared docs/esmc_loss_gradient_balance_v1.md: ONE HPC3 diagnostic job,
existing35/166 TRAIN inputs x own best25/last40 checkpoints, fixedseed12345,
no optimizer or new epochs. Measure separate aligned/frame and actual0.001-weighted
parameter-gradient norms/directions globally and by disjoint modules, with exact
replay/unchangedweights and independentCPU scalar/moment/source QA. Coordinate-
gradient scaling did not establish actual network-gradient balance. No new
coefficient grid, no951repeat (memoryalreadyverified), no architecture/loss change
yet. Audit script not implemented/submitted. Original trained ESMC/all-heavy-atom/
confidence/one-NFE/formalheldout/end-to-endcost goal remains unfinished and active.


## 2026-09-18 — Diagnose seed agreement without extra GPU work

While631506 remains live, predeclared docs/esmc_geometry_diagnostics_v1.md
adds CPU-only final-coordinate analysis, not training/selection changes: observed
residue-centroid/internal error split and within-residue radius, direct proper-
aligned two-seed atom/CA/distance disagreement. Needed because similar GT RMSDs
can mask two similarly wrong/collapsed predictions. New reusable module
src/fastglycan/coordinate_diagnostics.py and focused pose/mask/collapse test pass.
Baseline-only CPU preflight reproduces accepted old shape diagnosis and measures
old trained seed disagreement: pooledatom8.632539,CA8.682719,dist8.020517 A.
Artifact baseline_coordinate_diagnostics.json and exact source archive are under
reports/esmc_geometry_capacity_2026-09-18/. No extra model forward or GPU job.
After observer1691 accepts final631506 QA, run scripts/diagnose_esmc_geometry_coordinates.py
--baseline-root reports/esmc_capacity_2026-09-18
--root reports/esmc_geometry_capacity_2026-09-18 (without --baseline-only).
It requires accepted reports/GT/prediction hashes; do not run final diagnostics
against intermediate checkpoints. The existing observer remains unchanged/live.

Latest archived progress34/1088updates; eval30 dual-seed pooledatom7.917667/
7.919979 A, CAdistance6.302073/6.303552 A, handedness50.49/51.63%. Jointscore
11.714756 is worse than selectedepoch25 score10.586732 because consecutiveC-N
geometry worsens. Do not replace the predeclared joint score with atom RMSD.
No gate pass; continue existing automatic plateau/time rules, no new GPU grid.


## 2026-09-18 — Predeclare one scaled-geometry and varied-sampler capacity run

Training631506 verified RUNNING; latest archived progress epoch18/576updates,
last evaluation15. Seed12345/54321 pooledatom11.391536/11.397902 A and CAdistance
12.089112/12.106597 A; handedness50.66/50.52%. Joint score12.106597>1; no pass.
Initial32 seed12345 predictions exactly match baseline random initialization.
CPU validator preflight on64 initial predictions passes (max local-geometry
scalar discrepancy5.8208e-11); this is not final QA. Eleven focused tests/lint pass.
Current report/curves reports/esmc_geometry_capacity_2026-09-18.{md,png,json},
compact archive in same directory. Execution sources archived and hashes fixed.
Completion observer exec session1691 is live: polls only631506 every30s, retries
observation failures without restart; after COMPLETED0:0 performs independent
CPU heavy-artifact/FP64/geometry/selection/stopping QA, compact archive and plots.
QA snapshot code_esmc_geometry_validation_v1_20260918. Do not duplicate observer,
resubmit training or run final QA while training remains live. Next inspect
same job/session and accepted final artifacts; preserve all original goals.

HPC3 training631506 submitted; immutable code_esmc_geometry_capacity_v1_20260918, output esmc_geometry_capacity_32_v1_20260918. One H100 only. Eleven focused gate/frame/initialization/label tests and lint pass. Independent final QA/report preparation runs concurrently on CPU; no second GPU experiment.

Predeclared docs/esmc_geometry_capacity_v1.md: one fresh-init TRAIN32 run, same
accepted inputs/topology/optimizer/budget100epochs3200steps as prior capacity,
L=aligned_atom_MSE +0.001*local_frame_MSE, fixed coefficient based on measured
TRAIN coordinate-gradient median654 (weighted0.654), not a search. Vary sampler
by group/epoch, evaluate both12345/54321 every5epochs. Joint checkpoint score is
maximum normalized coordinate/local-distance/handedness/29-of32 criterion across
both seeds. Gates: pooledatom<=1A,CAdistance<=1A,29/32atom<=2A, eachNCA/CAC/CO
RMSE<=0.15A,consecutiveCN<=0.30A,handedness>=95%. This is a small-set capacity
gate, not a formal held-out result or full stereochemical validation. SameHPC3
oneH1008CPU96G,75minsoft/2hhard;futility20,20epoch1%-plateaufrom30. Confidence
heads frozen. Reuse already verified labels/ESMC rather than rebuilding datasets.
Joint remedy does not identify independent effects of loss/noise changes. No grid,
no new training weights from old trained model, no test data or teacher states.
Implementation and focused tests prepared; submission follows passing checks.


## 2026-09-18 — Local-frame derivative path accepted; scale before training

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
Equal audit coefficients are not production weights. Next predeclare ONE bounded
scaled-geometry + varied-sampler training run with explicit multi-seed capacity
and geometry criteria. Do not launch a speculative parallel hyperparameter grid.
Original trained core/confidence/formal held-out/end-to-end cost remain open.


## 2026-09-18 — Verify local-frame supervision before another training run

HPC3 derivative audit submitted as631479, immutable code_esmc_frame_audit_v1_20260918; output esmc_frame_audit_v1_20260918. One H100,8CPU,96G,1h hard limit. CPU QA preparation proceeds concurrently without a second GPU.

Local-frame supervision CPU audit complete: all32 proteins x3 existing predictions
match independent NumPy FP64 (max4.5475e-13 A²); shortest trained directional
relative derivative error1.6007e-6; all observed-coordinate gradients finite/nonzero,
masked gradients zero.3,200 stateless group/epoch sampler seeds are distinct.
Protocol docs/esmc_frame_supervision_audit_v1.md defines loss-only observed N/CA/C
frames and nearby observed atoms, proper-pose invariance and handedness sensitivity.
Next is one HPC3 GPU derivative/memory audit on existing TRAIN35/166/951 inputs,
using accepted failed checkpoint diagnostically, no optimizer/epochs. Equal loss
coefficients are derivative-probe coefficients only, not production loss weights.
CPU sources/results archived reports/esmc_frame_supervision_2026-09-18/.
Do not duplicate CPU audit. New training protocol follows accepted GPU/CPU QA.


## 2026-09-18 — Capacity experiment verified negative; diagnose atom collapse and RNG sensitivity

Task631201 completed0:0 in35:00,100epochs/3,200updates, best epoch85. Selected
pooled atom/CA/distance2.542979/1.809505/1.513566 A,0/32 atom<=2 A; gateFalse.
Seed54321 gives9.066434/8.783899/8.179035 A. Exact best reload/all32 replay,
one trunk/one structure call, unchanged input/frozen-head hashes. Confidence
remains untrained. Short32-protein peak2.758616GiB, not a full-length benchmark.

Independent CPU heavy-artifact/source/checkpoint/FP64 QA passes; max metric
error2.713151e-6 A. Observer44172 exited0, no live project jobs. Compact archive
reports/esmc_capacity_2026-09-18/ contains96 predictions,32 GT/inventories,
histories, QA, actual source, and final local geometry; report/curve same prefix.
Heavy weights/features remain HPC3. Best SHA
4d861a1e6037e84a7d5796ffee6280e096b822d463305f799b74dae55f54aced.

Selected local errors: N-CA1.0604,CA-C1.1331,C-O0.8518,consecutive C-N3.5202 A;
handedness agreement1755/3579=49.04%. Post-hoc residue-centered analysis
recomputes all32/three conditions exactly: predicted within-residue RMS radius
0.552642 versus GT2.196170 A;71.7973% of aligned SSE lies in residue-centered
coordinate error (includes orientation). Centroid error1.350481 A for fixed RNG
versus8.797516 A for second seed. This supports within-residue atom collapse and
sampler-RNG overfitting. It is a diagnostic, not a replacement success criterion.

Close this configuration: no epoch extension, promotion or full-data training.
Next verify a geometry-aware objective and varying sampler RNG under a new
bounded contract before another training run. No loss coefficients/budget chosen
yet; no broad grid. Original trained all-heavy-atom/ESMC/confidence/one-NFE,
formal held-out validation and complete inference-cost requirements remain open.

## 2026-09-18 — Audit confidence supervision before enabling it

Read-only installed source and actual short capacity input on one spare CPU
reveal inference resolution=-1 despite experimental metadata1.0 A. Native
ProtenixLoss gates all confidence losses to resolution[0.1,4.0]; blindly passing
this packet would zero confidence gradients. Runtime alpha_pae=0 also disables
PAE supervision by default. Current capacity task freezes/does not call the
confidence head, so this audit does not invalidate its coordinate training.

Native pLDDT target is observed atom-to-polymer-representative bespoke lDDT,
not the Stage0 all-atom pair summary. PDE/PAE representative/frame inputs exist;
PAE masks missing frame atoms. Resolved labels need an explicit eligibility
policy for GT-masked modified sidechains, not blanket false=unresolved.
Future confidence protocol must specify true-metadata resolution eligibility,
weights/targets/masks and held-out calibration. Do not change active model or
training, invent missing labels, or claim calibration from finite logits.
Report/archive reports/esmc_confidence_interface_2026-09-18.md and directory,
including actual source files/hashes; no new GPU allocation.

## 2026-09-18 — Lossless feature storage feasibility on spare allocated CPU

While capacity task631201 remains live, audit accepted951-residue interface
inputs on one spare CPU (step631201.1 completed0:0 in6s). All-zero int64
bond_mask[7665,7665] is470,017,800bytes of a535,739,097-byte packet. Source reads
are confined to upstream bond-loss code, not the custom core/sampler/confidence
path. Preserve all fields; do not alter running inputs or the chemical graph.

A second CPU step repacks existing PyTorch ZIP members with ZIP_DEFLATED level1
into a new isolated probe file. Native torch.load(weights_only=True,CPU) restores
all fields/labels with identical recursive tensor hash; source file hash matches
accepted interface provenance. File4,433,548bytes,99.17% smaller for this example.
Compression1.770s, single warm original/compressed reads0.060/0.141s; these are
not benchmark claims and decompressed RAM/GPU memory is unchanged. Future larger
training can use lossless compressed packets with lazy loading after an explicit
input-cache protocol; no current model, training or source snapshot changed.
Report reports/esmc_feature_storage_2026-09-18.md and two compact audit JSONs;
probe feature_storage_probe_v1_20260918 remains HPC3, no extra GPU allocated.

## 2026-09-18 — Add CPU local-geometry diagnostics and finalization observer

While task631201 continues under its original stopping criteria, declare
supplement docs/esmc_capacity_diagnostics_v1.md before final best/second-seed
predictions exist. Add importable experimental_geometry.compare_local_geometry:
observed N-CA/CA-C/C-O distance errors, separately consecutive observed C-N,
and CA signed-volume agreement to actual GT. Explicit missing/degenerate masks,
no new training/selection criterion or model inference. Five focused tests pass,
including proper-rigid/reflection distinction, distortion and missing/degenerate
handling; lint passes. This is partial local QA, not full stereochemistry.

Initial-only CPU analysis archived as geometry_initial.json:3809 pairs for each
intraresidue type,3774 consecutive C-N,3579 evaluable CA handedness sites. Initial
N-CA/CA-C/C-O/C-N RMSE18.999896/19.876609/17.189182/37.639064 A; handedness
agreement58.3962%. These characterize the untrained starting model only.
Source/protocol snapshots preserved in the capacity archive source/geometry/.
Final selected/second-seed diagnostics require accepted final metric QA.

Launch local scripts/finish_esmc_capacity.py observer for existing job631201
(exec session44172). It polls the same sacct job every30seconds, retries transient
observation failures without restarting, and after COMPLETED0:0 performs bounded
CPU final artifact/checkpoint/FP64 metric QA on HPC3 without allocating a GPU.
It then archives compact outputs and actual validator source, runs CPU geometry
analysis, and updates curves/report. It never submits/cancels/resumes training.
Status: reports/esmc_capacity_2026-09-18/completion_workflow.json. Inspect the
live process/session plus Slurm; do not start a duplicate observer. Final workflow
success still does not complete original trained-model/confidence/held-out/cost
goals. Next review all final evidence and decide from actual capacity/noise/local
geometry results before any new training configuration.

## 2026-09-18 — Corrected capacity job running; parallel input QA passes

HPC3 task631201 passed full-RNG initialization,32 raw-GT rebuilds and exact
initial train/eval outputs. Epoch5/160updates reduces pooled train-set eval
all-atom RMSD29.916716 ->13.001799 A and CA-distance RMSE24.476017 ->13.724543 A.
Latest local progress epoch7/224updates. This is initial optimization progress,
not capacity success, validation generalization or confidence quality.

Use the user's parallelism preference for an independent CPU artifact/cache/label
audit inside the live allocation: step631201.0 COMPLETED0:0 in13s, one CPU,
CUDA hidden using env after srun, no extra GPU. All32 actual cached ESMC inputs,
source/initial-weight hashes and observed-label mappings pass:30,437 observed
atoms and1,496 masked generated atoms. Snapshot
code_esmc_capacity_input_validation_v1_20260918; output input_validation.json.

Compact GT/inventories/initial predictions/provenance/history, actual source and
initialization/input audits are locally archived/hash-verified in
reports/esmc_capacity_2026-09-18/. Provisional curves/report same prefix; figure
inspected. Eighteen focused tests and lint pass. Final metric/checkpoint QA and
result interpretation remain pending; respect100epochs/3,200updates and early
stopping, no blind additional submissions or teacher-loss grid.

## 2026-09-18 — Correct SciPy/NumPy initializer reproducibility before training

Capacity task631181 failed the initial tensor-hash assertion in51seconds, before
any inputs/GPU forwards/optimizer updates. Read-only CPU comparison shows both
default and capacity constructors differ from the prior interface initial state
in571 tensors. Source cause: Protenix triangular.layers.trunc_normal_init_ calls
scipy.stats.truncnorm.rvs using the unseeded NumPy RNG. Existing ESMCFoldCore
forked/seeded only PyTorch. The old interface checkpoint and its exact saved-state
replays remain valid; fresh seed101 alone was not a fully reproducible initializer.

Correct constructor to seed and restore Python/NumPy alongside PyTorch. Preserve
original execution snapshots and failed task; pin a new full-RNG initialization
hash before retraining, rather than pretending it matches the old random state.
No loss/model/data/grid change.18 focused tests now pass, including RNG-stream
isolation and reproducibility after unrelated draws. Full-model CPU cross-config
repeat check passes: default and dropout-zero capacity configurations produce
identical tensor hash baad41b475327b40f3b458d04e7ee85696639776096a12699b661b2b87b908ea
after unrelated intervening random draws, using zero GPU allocation.
Audit esmc_capacity_initialization_v2_20260918.json is retained on HPC3.
Corrected task631201 submitted with unchanged data/loss/budget, immutable
code_esmc_capacity_v2_20260918 and output esmc_capacity_32_v2_20260918.

## 2026-09-18 — Bound the first direct-GT ESMC capacity training

Predeclare docs/esmc_capacity_v1.md before launch. Use only the 32 shortest
accepted training groups (35–166 residues), raw-GT exact rebuilds, existing
frozen ESMC cache and unchanged observed chemical masks. Fresh same seed101
134,584,255-parameter core, no folding weights or teacher state/coordinate input.
Train native one-cycle/one-step coordinates using observed proper-rigid-aligned
mean squared Euclidean atom error; fit target into detached predictions in FP64,
no gradient through SVD, reflections, scale fitting or missing-atom imputation.
Seventeen focused mask/alignment/gradient/cache tests pass.

Capacity-specific dropout=0 and unchunked trunk in both modes, exact initial
train/eval check; original interface default remains available. Freeze unused
confidence/distogram heads, explicitly leaving confidence training/calibration
unfinished. Fixed forward seed12345 isolates capacity, final seed54321 is a
sensitivity diagnostic only. AdamW1e-4, wd1e-4, clip10, batch1, at most100epochs
(3,200 updates), five-epoch structural evaluations, success/futility/plateau
stopping and75-minute soft training/evaluation budget, one HPC3 H100 only.
Select by pooled experimental heavy-atom RMSD and require distance/per-protein
criteria for capacity success. Save raw coordinates, histories, atomic best/last
checkpoints and provenance; independently recompute saved metrics on CPU.

User preference persists: parallelize necessary independent experiments or CPU
assessment when useful, not speculative/redundant GPU grids. No additional GPU
experiment is justified before this first direct-GT optimization result.
No generalization, calibrated-confidence or end-to-end cost claim follows.
Submitted HPC3 task631181 (one H100,8CPU,96G,2h hard limit), immutable source
code_esmc_capacity_v1_20260918 and separate output esmc_capacity_32_v1_20260918.

## 2026-09-18 — Fresh ESMC all-atom core interface verified

HPC3 631114 completed 0:0 in 2:06. Fresh Mini-topology ESMC core has 134,584,255
parameters and zero folding-checkpoint loads; initial weight hash
29588108548a225370c84410699dbfd8c4c3c9474d2b31e149495ef0470e11a4.
Fixed training lengths35/951 generate 289/7,665 atoms; GT has 289/7,446 observed
atoms and 0/27 masked missing residues. Both GT records rebuild exactly from
raw mmCIF. Actual forward counts are one trunk cycle, one structure call, one
confidence call and one sample. Confidence logits/coordinates finite, repeated
inference and checkpoint reload exact. Matmul/cuDNN TF32 explicitly False.

Backward peaks 1.100/47.155 GiB, ESMC projection gradient norms4.577025/3.973495;
413 parameter tensors have nonzero gradients in both probes. At zero projection,
short-input output is insensitive to ESMC; after the fixed disposable L2=0.1
projection update, same-RNG actual/zero ESMC outputs differ by max0.0510254 A.
This establishes the usable conditioning/gradient path, not trained accuracy.
The unaligned GT MSE was only a derivative probe. First forward timings4.848/
7.460s include confidence0.075/1.350s but have different warm-up histories and
exclude ESMC extraction/data work; no end-to-end speed comparison.

Independent CPU audit verifies stored initial weights, actual cached ESMC inputs,
every observed/absent atom label, predictions and source/artifact checksums;
it does not repeat GPU derivatives or unarchived confidence tensors. Execution
snapshot/output code_esmc_core_interface_v1_20260918 / esmc_core_interface_v1_20260918;
validator code_esmc_core_validation_v1_20260918. Report and source/QA/GT/prediction
archive reports/esmc_core_interface_2026-09-18.md and directory. Large initial
weights/feature packets remain HPC3. Fifteen focused tests and lint pass.

Next specify a bounded direct experimental-GT capacity/training contract. Reuse
the new scratch core and accepted cache/masks; do not load teacher states or
promote the disposable projection probe. Trained structure/confidence quality,
formal held-out validation and end-to-end cost remain unfinished original goals.

## 2026-09-18 — Implement and submit the predeclared scratch ESMC interface gate

Implement src/fastglycan/models/esmc_core.py: direct fresh Protenix construction,
Mini 16/8/1/1 topology, 1152-to-449 ESMC projection, one trunk cycle and one
native structure step, optional standard confidence outputs. Never construct
the checkpoint-loading inference runner. Explicitly disable matmul and cuDNN
TF32 for this new scratch-core gate; record resolved configuration separately
from prior compatibility experiments. The training path explicitly requires
train mode because upstream get_pairformer_output otherwise disables gradients.

Importable experimental_training.map_experimental_atoms verifies the unchanged
GT contract and maps labels by residue/atom identity with explicit missing masks;
generated reference positions are never target coordinates. Fifteen focused
mapping/cache/GT tests and lint pass. The GPU check first constructs CPU weights
under a forbidden-torch.load guard, rebuilds raw GT for only the existing 35/951
training sequences, and checks the short input before the long one. It measures
actual call counts, deterministic replay, confidence, full-core gradients and
initial-checkpoint roundtrip. Observed unaligned coordinate MSE and a fixed-L2
0.1 ESMC projection update are disposable derivative/sensitivity probes only;
they are not a chosen performance-training objective.

Submitted one HPC3 H100 job 631114 (8 CPU, 96G, 1 GPU, 1h limit), immutable
code_esmc_core_interface_v1_20260918, new output esmc_core_interface_v1_20260918.
CPU preparation precedes CUDA work inside the one necessary allocation. No
additional model grid or full-data training. Inspect actual artifacts before
claiming the interface gate passes; no ESMC core quality claim yet.

## 2026-09-18 — Response supervision verified; close this teacher-side branch

Training 630851 completed 0:0 in 49:11, all four decode shards 630855 completed
0:0 in 2:15–2:34, corrected independent QA 631039 completed 0:0 in 2:11. Best
epoch2 response ratios 0.958219/0.948078 do not translate to better full-sampler
teacher-relative structure: all-atom/CA-distance ratios to c1 are
1.012301282/1.007846873 (2.940202631/2.052314430 A). Harms affect 28/64 and
32/64; joint 0.95-of-c1 gate and c2 parity fail. Same-architecture raw-state
model errors are 2.945227/2.081999 A; the small improvement over that model does
not justify promotion. No additional epochs or teacher-side loss/architecture
grid. This rejects the tested fixed first-response objective/schedule, not all
possible decoder-aware supervision.

QA failures 630856/631028 were due to a validator precision mismatch, not bad
weights: Protenix enable_tf32=False disables matmul TF32, while the original
response training/export/decode retained cuDNN's default True. The generic
validator additionally forced cuDNN=False; fused attention bias uses conv2d.
Only response MSE differed for 51/64 examples, with baseline/ordering/correction
statistics exact. Same-pair False/True policy probes reproduce the failed and
training losses exactly. Corrected policy yields exact full 64-record response
revalidation and all original pair/atom/metric/source checks, without relaxing
tolerances or rerunning training/decoding. Keep failed diagnostics; future
runtime provenance records both actual flags. Do not describe the earlier
config flag as globally TF32-off. Snapshot code_response_validation_v3_20260918;
QA root response_validation_v3_20260918. Actual baseline/full decoder comparisons
retain their original shared numerical policy.

Selected response checkpoint experimental-GT assessment now passes the local
CPU append: unchanged accepted raw-GT member hashes, identical c1 metrics and
independent FP64 response metrics for all 64 groups. GT pooled all-atom/CA/
CA-distance errors are 4.797496/4.583442/3.107093 A, small improvements over c1
(~0.35% all-atom, ~1.26% distance) but worse than c2 and raw-state learners.
Preserve this distinction from the teacher-relative failure. No GT-based
checkpoint choice, temporal-test or formal 1,600-group claim.

Final artifacts, actual source snapshots and reviewed figures are archived in
reports/stage1b_response_supervision_2026-09-18.* and directory; six-condition GT
reports/archive in reports/stage1b_experimental_validation_2026-09-18.* and directory.
All current response jobs are terminal. Original goal remains unfinished.

Predeclare docs/esmc_core_interface_v1.md as the next implementation gate toward
the original predictor: fresh random ESMC-conditioned all-atom core, explicit
Mini topology as a starting implementation baseline, no folding-checkpoint or
teacher-state input; exact cached feature/observed-GT mapping and measured actual
cycle/NFE/confidence/gradient behavior. Reuse already accepted data and test
shortest before longest training inputs. CPU checks before one necessary GPU
forward/backward; no new model training until its bounded direct-GT contract.

## 2026-09-18 — Validate the ESMC input boundary without a new GPU trial

Implement a strict canonical-monomer adapter for the existing pinned ESMC final
cache. It maps token residue identities, rejects existing ESM2 embeddings and
keeps chemical features unchanged. No new dataset, architecture, supervision
or trained-core claim. Fourteen focused tests and lint pass. CPU step 630851.3
completes 0:0 in 26s: original shortest/longest training sequences 35/951 have
exact cached feature mapping into actual Protenix token features and no other
feature changes. No GT reads, ESM recomputation or model inference. Actual
ESMC manifest hash remains a751c1581137248c4e3de75da4c0994d3c51c790bda547af4a0ea202355f0ba1.
Snapshot code_esmc_boundary_v1_20260918; output esmc_boundary_v2_20260918;
reports/stage1b_esmc_feature_boundary_2026-09-18.{md,json}. Preserve the original
separately trained ESMC all-atom objective and finish the existing response QA.

Initial CPU step 630851.2 failed its environment guard before featurization.
Slurm rewrote CUDA_VISIBLE_DEVICES; move the empty assignment into `/usr/bin/env`
after srun. Same immutable source, new output directory, no extra GPU allocation.

## 2026-09-18 — Keep ESMC core requirements explicit while response training runs

A CPU-only source/specification audit confirms the original conditioner is not
implemented in the current teacher-state emulation path: ESMC final width 1152
differs from Mini-ESM ESM2 width 2560, which feeds a 449-wide additive projection;
the inference dataset also invokes ESM2 preprocessing. Downstream single/pair
widths are 384/128. Preserve separately trained/randomly initialized ESMC core
requirements; do not silently treat a checkpoint projection swap or successful
ESM2 pair pilot as fulfillment. Zero projection initialization means future
conditioning smoke must include a gradient/update check. The existing ESMC
cache is accepted and must be reused. Report and source-hash evidence:
reports/stage1b_esmc_interface_audit_2026-09-18.{md,json}. No new architecture,
training run, split or target contract is introduced; current response pipeline
retains priority, with GT assessment after final QA.

## 2026-09-18 — Experimental validation baseline accepted without another GPU

CPU steps 630851.0 (40s) and 630851.1 (12s) completed 0:0 within the existing
training allocation, with no extra GPU reservation. All 64 GT records rebuild
exactly from raw mmCIF; all 320 condition metrics independently recompute in
FP64. Observed common GT has 140,457 atoms and 18,014 CA atoms; 944 missing
residues stay masked. Prediction coverage of observed GT is 100% throughout.
Pooled all-atom c1/c2/c4/pointwise/triangle errors are
4.814416/4.694222/4.537611/4.708911/4.706845 A; CA-distance errors are
3.146723/3.088734/2.871992/2.996987/2.994481 A. Pointwise/triangle improve GT
errors modestly despite their worse teacher-relative results. Preserve that
distinction and their original failed teacher-relative gates; these 64
pre-cutoff validation examples are not a temporal test or proof of no teacher
pretraining overlap. No automatic promotion or changed training selection.
Reports/figure/full GT archive: reports/stage1b_experimental_validation_2026-09-18.*
and directory. Immutable assessment/validation v1 snapshots dated 20260918;
output experimental_assessment_64_v1. Five focused tests and lint pass.

Prepare a local CPU-only append path for the selected response checkpoint,
requiring its original full-decoder QA first. It reuses unchanged accepted GT
member hashes and confirms FP32/FP64 and identity agreement. No intermediate
response checkpoint has been evaluated on experimental coordinates. Response
training 630851 is live through epoch nine; best epoch two remains 0.958219 /
0.948078 response ratios, while epoch-nine ratios regress to 1.115269/1.106131.

## 2026-09-18 — Parallel experimental-GT assessment without another GPU

The user requests parallel experiments only when they materially accelerate
progress without wasting compute. While response training 630851 continues,
predeclare docs/stage1b_experimental_validation_v1.md: map exactly the accepted
64 validation groups to their original Stage-B experimental records, preserve
observed masks and source checksums, and evaluate native c1/c2/c4 plus accepted
pointwise/triangle baselines. Add the selected response model only after its
existing decoded QA passes; do not select/tune it on these GT metrics.
This advances the original experimental-GT requirement without changing the
running experiment or accessing frozen temporal-test manifests/coordinates.

Strict sequence/residue/atom/mask checks and five focused tests pass. Snapshot
code_experimental_assessment_v1_20260918; output experimental_assessment_64_v1.
HPC3 rejected a standalone CPU batch submission because ACD requires GPUs;
instead use a one-CPU --overlap --gres=none step inside live job 630851, with
CUDA hidden, preserving the training process and requesting no additional GPU.
Logs: experimental_assessment_v1_step630851.{out,err}. Do not duplicate this step.

## 2026-09-18 — Combined longest-input training smoke passed

Running job 630851 passes the combined 951-residue learner/decoder smoke:
two optimizer steps, exact BF16 identity/reload, finite output gradients and
nonzero endpoint/context gradients on step two, with unchanged teacher weights.
Peak allocation 12,107,940,352 bytes (~11.276 GiB). Disposable smoke losses
11.245897 -> 11.244745 are an interface check, not a generalization result.
Fresh seeded weights are then restored and match the accepted baseline hash
exactly. The separate prior 14.410-GiB audit includes extra path-VJP work, so
these memory measurements are different workloads. Training/decoded gates
remain pending; do not infer useful structure improvement from smoke loss.

## 2026-09-18 — First-response cache accepted

Acceptance 630844 completed 0:0 (5:03), independently checking all 192 sample
artifacts, atom identities, splits, parent/source/checkpoint hashes and exact
longest train/validation c1/oracle response/cache replays. Controls, all traces
and 384 coordinate files are archived locally; bulk response packets stay HPC3.
Training 630851 is running with longest-input GPU smoke before optimization;
630855 native decoding and 630856 final QA remain dependency-gated. No learned
response or structural quality result yet.

## 2026-09-18 — Response training and mandatory decoded QA queued

Export 630834_[0-3] completed 0:0; acceptance 630844 remains running. Training
630851 is gated on acceptance and includes a two-update disposable 951-residue
smoke before restoring exact baseline initialization. Native decoding 630855
and independent final QA 630856 are dependency-gated; scontrol confirms the
actual chain. All use immutable code_response_training_v1_20260918 and separate
response_emulator_128x64_v1 / response_decoded_64_v1 outputs. Thirteen focused
tests and lint pass. No optimization result or quality claim yet.

## 2026-09-18 — Response cache export and differentiable full-pair path

Export 630834_[0-3] and exhaustive acceptance 630844 are submitted on HPC3,
with isolated response_cache_128x64_v1 and immutable code_response_export_v1 /
code_response_acceptance_v1 snapshots dated 20260918. Selection and supervision
follow the predeclared response pilot. The new importable response_training
helper checkpoints learner chunks while preserving full context gradients;
dense/chunk gradient equivalence and exact BF16 identity tests pass. No new
optimization before accepted cache and combined learner/decoder longest smoke.

## 2026-09-18 — Decoder gradient feasibility passed; predeclare response pilot

Audit 630782 and scalar/artifact QA 630783 completed 0:0 in 2:57 and 0:35.
All four training-only examples (35/91/408/951) reproduce first c1/oracle denoiser
responses exactly, preserve accepted c1 atoms, and yield finite nonzero pair
gradients through both pair_z and p_lm. Teacher weights remain unchanged. Peak
allocation at 951 is 14.410 GiB; shortest central-difference relative errors
0.0002032/0.00005409 pass. BF16-rounded perturbations are separately recorded
and substantially attenuated. Both learned raw-MSE updates have a locally
ascending response loss at length 408; no population inference follows.
QA independently reproduces saved losses/directions/FD and all learned pairs,
checks lineage/source/artifact hashes, but does not repeat decoder backward.
Thirteen focused tests and lint pass. Reports/figure/archive are
reports/stage1b_decoder_gradients_2026-09-18.* and directory; immutable execution
code_decoder_gradient_v2_20260918 / decoder_gradient_audit_v2_20260918. No live jobs.

Predeclare exactly one new training hypothesis in
docs/stage1b_decoder_supervision_pilot_v1.md: original pointwise architecture,
fresh matched initialization and fixed 128/64 groups; supervise the first
denoiser response at identical noise using the c1-single/c4-pair target.
Use full predicted pair states with differentiable rebuilt caches and the
unchanged twenty-epoch optimizer schedule. This changes supervision/workload,
not architecture; no raw-state auxiliary loss or hyperparameter search.
Derived response cache acceptance and combined learner/decoder longest-input
smoke precede training. Select by held-out response MSE including epoch zero,
then require full 64-target native-sampler structure gates. No response export
or new training is launched yet. Preserve the original ESMC-600M objective,
experimental-GT/full-gate/one-evaluation requirements and frozen temporal test.

## 2026-09-18 — Explicit gradient-path checkpoint import

Execution 630777 failed because Protenix calls torch.utils.checkpoint without
importing its submodule. The execution-only v2 explicitly imports it, preserving
all model/loss/selection/gate settings and initial failure artifacts. Audit
630782 and after-success scalar/artifact QA 630783 use immutable
code_decoder_gradient_v2_20260918 and decoder_gradient_audit_v2_20260918.
QA 630780 was dependency-cancelled. No new training or success claim.

## 2026-09-18 — Frozen decoder gradient audit submitted

HPC3 job 630777 uses immutable code_decoder_gradient_v1_20260918 and isolated
decoder_gradient_audit_v1_20260918. The predeclared four-training-target audit
rebuilds pair_z and p_lm differentiably; c_l is atom-reference-only. Three local
tests cover both gradient paths, capture isolation and finite differences.
Actual decoder replay, numerical derivative acceptance and 951-residue memory
are still pending. No optimization or research/data-contract change is made.

## 2026-09-08: Adopt joint-distribution framing

Decision: frame the project as `Fast Joint Glycan Ensemble Models for
Conformational Design`, with one-step generation as an implementation axis.

Reason: GlyContact explicitly reports that its von Mises model does not learn
angle-angle dependencies, while GlycoShape preserves weighted MD conformers.
The scientific test is whether those dependencies change geometric-event and
edit-ranking decisions.

## 2026-09-08: Keep the first chemical graph fixed

Decision: fix residue count, linkage positions, branch topology, and anomeric
state; allow only an allow-listed set of monosaccharide substitutions.

Reason: changing linkage changes the atom graph and degrees of freedom. A
continuous soft sequence is an optimization relaxation, not a physical molecule,
so every final candidate must be evaluated as a discrete legal edit.

## 2026-09-08: Require weighted reference records

Decision: every conformer record carries population weight, simulation condition,
and effective sample-size metadata.

Reason: equal-weight cluster representatives can distort rare-event probabilities;
MD frames also have autocorrelation and cannot be counted as independent samples
without qualification.

## 2026-09-08: Use the GlycoShape ZIP as the import authority

Decision: import through `GET /api/download/<identifier>`, preserve the raw ZIP
and `data.json`, split `PDB/alpha.pdb` and `PDB/beta.pdb` into individual models,
and map `archetype.cluster_levels` weights only when the count exactly matches
the PDB model count.

Reason: the live API returns representative multi-model PDBs plus cluster
percentages, while cached GlyContact mirrors can have a different current cluster
count. The archive's metadata and models are therefore treated as an atomic pair.
The requested lookup ID may differ from the alpha/beta structure-specific
GlyTouCan IDs, so both identifiers are retained.

## 2026-09-13: Pivot to one-step protein monomer folding

Decision: make protein monomer folding the active project. Target
`protenix_mini_esm_v0.5.0`, MSA disabled, one Pairformer cycle, one structure NFE,
one sample. Preserve the glycan importer as a historical prototype rather than
delete it.

Reason: the new objective removes the need for mutation-pair data and gives a
clean Stage 0 quality/cost experiment. However, DCFold already publishes a
Protenix-derived all-atom one-recycle/one-step model, so the contribution cannot
be “one-step folding” alone. The proposed distinction is a training-efficient,
teacher-optional Clean-Structure MeanFlow adaptation, tested against native
Protenix and consistency baselines.

## 2026-09-13: Require a six-point Stage 0 matrix before training

Decision: evaluate `(cycles, steps)` = `(4,5)`, `(4,2)`, `(4,1)`, `(2,2)`,
`(1,2)`, `(1,1)` with `N_sample=1`, MSA off, fixed seed, and end-to-end timing.

Reason: Protenix exposes cycle/step overrides, but its docs require
`--use_default_params false` for manual overrides. The matrix separates diffusion
collapse from recycle collapse and prevents a new loss from being chosen before
the actual bottleneck is measured.

## 2026-09-13: Treat Mini-ESM training as an explicit integration task

Decision: use Mini-ESM for Stage 0 inference, but do not assume its training
path is turnkey. Before Stage 1, either add a local dataset loader for cached
ESM2-3B embeddings with a versioned cache contract, or begin with the Mini
non-ESM model and add ESM later.

Reason: the current Protenix training dataset does not attach ESM features by
default, and the maintainer describes Mini-ESM support as inference-first. The
embedding cache, tokenizer, alignment, and backend therefore affect both
reproducibility and the MSA-off claim.

## 2026-09-13: Separate matched monomer evaluation from DCFold headlines

Decision: compare DCFold only on matched monomer, MSA-off subsets and report
protocol differences. Keep a five-seed variance subset in Stage 0 even though
the deployment contract is one sample.

Reason: DCFold's published evaluation spans broader all-atom tasks, while this
project intentionally narrows the first target to monomers. A single headline
number would conflate task, data, MSA, and sampling differences.

## 2026-09-13: Replace ESM2 with ESMC as the active sequence conditioner

Decision: use frozen ESMC-600M with cached per-residue embeddings as the active
conditioner for a randomly initialized folding core. Use ESMC-300M as a memory
baseline, ESMC-6B as an upper-bound ablation, and keep the official Protenix
Mini-ESM checkpoint as a separate ESM2 compatibility baseline.

Reason: ESMC is the representation-learning branch of the current Biohub ESM
release and exposes sequence embeddings directly. ESM3 is a multimodal,
iterative sequence/structure/function generator; its structure track is not
allowed in the main input path because it would introduce an unstated folding
teacher. Changing from ESM2 to ESMC also changes embedding dimensions and
requires a learned adapter plus a separately trained folding core.

## 2026-09-13: Use UniProt for sequence coverage, experimental PDB for labels

Decision: build the sequence universe and self-supervised corpus from a pinned
UniProt release, but use only experimentally resolved PDB chain coordinates for
the main all-atom structure labels. Join the two through residue-level SIFTS
mapping and retain construct, mutation, missing-residue, isoform, and release
metadata. Do not use AlphaFold/ESMFold/ESM Atlas coordinates in the main target
set.

Reason: UniProt is a sequence and annotation database, not an all-atom
structure-label source. This removes coordinate-teacher bias while retaining
the unavoidable inductive bias of the chosen pretrained ESMC representation.
The release identifier and mapping snapshot are part of the reproducibility
contract.

## 2026-09-13: Treat ESMC/ESM3 as representation priors, not teacher-free truth

Decision: keep ESMC frozen and sequence-only in the main path. Report the exact
model revision and test for sequence overlap with the ESMC pretraining corpus
when that corpus is available. Use ESM3-open only as a sequence-hidden-state
ablation; never feed its structure-track outputs to the folding model.

Reason: ESMC is explicitly trained to represent protein biology from billions of
sequences, while ESM3 jointly models sequence, structure, and function and uses
iterative masked generation. Removing AF/ESMFold coordinates avoids a coordinate
teacher, but neither model is an unbiased representation source.

## 2026-09-13: Use exact-identity de-duplication for experimental GT

Decision: de-duplicate only at 100% sequence identity. Preserve near-identical
sequences, engineered constructs, and small mutations when they have valid
experimental PDB/SIFTS records. Multiple experimental structures for the same
exact sequence remain separate structure records unless a later ablation shows
that a single-label protocol is required.

Reason: the dataset should expose local sequence-to-structure changes instead
of erasing them with family-level clustering. Exact-sequence groups are still
assigned to one split so repeated labels for the same sequence cannot leak
across train, validation, and test.

## 2026-09-14: Start the experimental GT raw snapshot on hpc2

Decision: use the 2026-09-08 SIFTS CSV snapshot as the first raw manifest,
  with complete `pdb_chain_uniprot` and `uniprot_pdb` files. The observed
  segment file is currently a clearly marked partial download pending resume.
  Download all 244,406 PDB entries having a chain-level UniProt mapping as
  compressed mmCIF, plus UniProt FASTA for the 76,273 mapped accessions. Keep
  the PDB entry files and accession-batched FASTA files in separate raw
  directories under `/hpc2hdd/home/shuang886/Folding/Dataset`.

Reason: this preserves all experimentally mapped structures before monomer
filtering and exact-identity de-duplication. Near-identical constructs and
small mutations remain available for the later GT builder; no predicted
coordinates are downloaded.

## 2026-09-14: Re-estimate storage for the mapped coordinate-only GT

Decision: do not provision another 100 TB machine for the current raw GT
download. The active scope is compressed mmCIF for SIFTS-linked PDB entries plus
mapped UniProt FASTA, not a mirror of the complete PDB Core archive or its
experimental attachments. Based on the live download rate, the final raw
mmCIF layer is expected to be roughly 90--100 GiB; reserve 0.5--1 TB for
decompression, parsed shards, indexes, and temporary copies.

Reason: the previously mentioned TB-scale figure referred to a full PDB Core
snapshot and broader archival/working copies. It is not the size of this
coordinate-only, UniProt-linked subset. Additional storage may be revisited
for full-UniProt ESMC embedding caches or archival backups, neither of which is
required for the first GT build.

## 2026-09-14: Validate the initial mapped PDB raw layer

Status: all `244,406` manifest entries are present as `.cif.gz`, with no
remaining partial files. A full parallel `gzip -t` pass reported zero errors.
Gemmi parsing of a random 200-entry sample also succeeded; every sampled entry
contained at least one protein chain, while many contained multiple protein
chains/entities.

Implication: the raw layer is usable, but an entry is not yet a training
example. The GT builder must select SIFTS-mapped protein chains, apply the
monomer/length/quality policy, and only then perform 100% sequence-identity
grouping while retaining near-identical constructs and small mutations.

## 2026-09-14: Complete the SIFTS-linked raw snapshot before split work

Status: the observed-segment SIFTS file has finished its resumable download and
passes `gzip -t`. The raw snapshot now contains the three pinned SIFTS flatfiles,
`244,406` complete compressed mmCIF entries, and `76,273` UniProt FASTA records.
The FASTA accession set exactly matches the accession set in
`pdb_chain_uniprot.csv.gz`; no empty FASTA records were found. No sequence-
identity grouping or train/validation/test split has been performed yet.

Implication: subsequent work should treat these files as the immutable raw
input layer and build chain-level metadata/quality tables separately. Exact
100% SI grouping remains a later split-stage operation, with its alignment
method and denominator frozen before any partition is generated.

## 2026-09-14: Raw-layer acceptance and GT-builder gates

Acceptance: the raw snapshot is complete and internally consistent for the
current scope. It contains `244,406` PDB mmCIF files, `1,031,850` SIFTS mapping
rows, `1,557,033` observed-segment rows, and `76,273` non-empty UniProt FASTA
records whose accession set exactly matches the SIFTS accession set. The PDB
gzip layer passes a full integrity check.

The raw layer is not yet a trainable GT set. A sample of 200 entries showed
X-ray, electron-microscopy, and solution-NMR records, canonical protein chain
lengths from 11 to 3,159 residues (median 371 in that sample), multiple-model
NMR entries, and substantial residue/atom incompleteness. These require an
explicit quality and monomer policy.

Critical parser rule: SIFTS `CHAIN` must be resolved through
`_entity_poly.pdbx_strand_id` to an entity, then to one or more
`_struct_asym.id` label chains. It must not be looked up directly as a
`_struct_asym.id`, and `auth_asym_id` alone is not unique. In a 200-entry audit,
all 890 sampled SIFTS rows matched `pdbx_strand_id`; direct label-chain lookup
would have missed 338 of them. The global SIFTS table has `992,086` unique
PDB-chain pairs, with `9,927` pairs linked to multiple UniProt accessions; all
accessions must be retained as provenance until a later ambiguity policy is
declared.

Training is gated on a processed chain table and structure shards containing
the PDB polymer sequence, residue/atom coordinates, atom masks, residue index
mapping, experimental method/resolution/model metadata, and explicit missing-
residue/alternate-location handling. The UniProt sequence remains annotation
and coverage metadata; the folding input sequence should be the construct
sequence represented by the experimental PDB chain so that coordinates and
tokens align. SI grouping and split generation occur only after this GT layer
is built and audited.

## 2026-09-14: Structure-first GT and non-imputing primary branch

Decision: make the PDB mmCIF the authoritative source for the training sample.
The construct sequence, residue identifiers, coordinates, atom masks, and
residue masks are all derived from the resolved PDB entity/label chain. UniProt
accessions and SIFTS residue mappings remain attached only for provenance,
traceability, and later analysis; they do not define the model input sequence
or replace PDB coordinates.

Missing atoms are kept as missing in the primary branch and represented by atom
masks for the loss. Do not silently repair or overwrite observed coordinates.
PDBFixer may be evaluated as a separately versioned derived branch for missing
residues, but every imputed residue/atom must carry an `imputed_mask`, and the
default experimental GT loss must exclude imputed targets. The raw mmCIF files
remain immutable.

Reason: using PDB-derived sequence and coordinates keeps the sequence-to-label
alignment exact for constructs, engineered mutations, truncations, and
noncanonical experimental designs, while preventing structure completion from
being mistaken for experimental evidence.

Scope note: the current raw manifest still discovers entries through the pinned
SIFTS chain-to-UniProt table. Thus the sample content is structure-derived but
the inclusion universe is currently SIFTS-linked. An all-experimental-PDB
universe, including entries without a UniProt mapping, would require a new
entry manifest and a separate download decision.

## 2026-09-14: Lock the first-version entry universe

Decision: use the staged `244,406` SIFTS-linked PDB entries as the complete
first-version entry universe. Do not add PDB entries that lack a SIFTS-UniProt
link in this version. SIFTS is an inclusion/provenance index only; all model
inputs and experimental targets continue to be extracted from the PDB mmCIF
files.

Reason: fixing the entry universe now keeps the raw snapshot reproducible and
avoids expanding download and quality-policy scope before the chain-level GT
builder is audited.

## 2026-09-14: Switch the training unit to jointly modeled protein chains

Decision: the first model will not be single-chain-only. A training example is
a selected PDB structure instance containing a jointly modeled set of protein
chains. Each chain keeps its own PDB-derived sequence, residue/atom coordinates,
and masks; the instance additionally carries chain indices and inter-chain
geometry. Ligand and RNA entities remain provenance/context metadata and are
not model inputs in the first version.

The GT builder must explicitly distinguish asymmetric-unit coordinates from a
declared biological assembly using the mmCIF assembly categories. It must not
silently concatenate chains from unrelated entities or apply crystallographic
copies as if they were an observed biological complex. Total residues, chain
count, and interface coverage become dataset strata and evaluation dimensions.

Reason: the intended folding task is joint multi-chain structure prediction;
single-chain filtering would remove the inter-chain geometry and interface
supervision that the model is expected to learn.

## 2026-09-14: Harden Stage A before the full scan

Decision: do not start the 244,406-entry catalog scan until the Stage A scanner
has the corrected chain resolver, entity-aware atom classification, date
metadata, assembly composition summaries, and deterministic shard execution.
The authoritative SIFTS chain mapping is now
`_pdbx_poly_seq_scheme.pdb_strand_id -> asym_id`, with conservative
`auth_asym_id -> label_asym_id` and unambiguous entity-only fallbacks. Entity
categories and component IDs distinguish protein, nucleic acid, water, ions,
small molecules, other polymers, and unknown non-protein atoms; only protein
entities contribute observed-residue summaries.

The scanner writes ordered, deterministic gzip JSONL shards using SHA256 PDB-ID
assignment, atomic `.part` files, and a resume check. Stage A also records
deposition/release/revision dates and uses Gemmi generator metadata to count
generated assembly chain instances without materializing coordinates. The
active import path is `onestepfold.data`; `fastglycan.gt_catalog` is only a
compatibility shim.

This supersedes the earlier wording that made jointly modeled multi-chain
structures the first training view: the universal catalog and GT contract stay
multi-chain-aware, while the first materialized training/evaluation view is a
monomer pool.

Validation: a real HPC pilot over `101m`, `6xu7`, and `7wxm` had zero errors,
corrected `6xu7` composition (76 protein plus 7 nucleic-acid chains), separate
water/ion/small-molecule counts, complete date fields, identical repeated
output SHA256, and successful resume/shard checks. The next gates are 1,000
and 10,000-entry audits. Coordinate materialization, SI grouping, split
generation, and ESMC caching remain blocked until the catalog audit is accepted.

The subsequent 1,000-entry HPC pilot (eight workers) completed in about 46
seconds with 1,000 successes, zero errors, zero unresolved SIFTS rows, complete
date coverage, and Gemmi assembly composition for every record. This is a
throughput baseline only; a 10,000-entry distribution audit is still required
before the full job array.

The 10,000-entry audit then completed with 10,000 successes, zero errors, zero
unresolved SIFTS rows, complete date/composition coverage, and an approximately
4.8 MiB catalog shard. Its distribution included 1,191 solution-NMR entries,
324 entries with 20 models, and smaller theoretical/scattering categories;
water, small molecules, ions, other non-protein atoms, and nucleic acid atoms
were present in 7,866, 5,875, 3,346, 466, and 389 entries respectively. The
scanner is therefore ready for a full job array, but the quality policy must
stratify these categories before selecting the monomer training view.

## 2026-09-15: Freeze structural monomer eligibility and launch full catalog

Decision: the v1 monomer view is selected from biological assembly composition,
not ASU chain count. A candidate has exactly one generated protein chain
instance, zero generated nucleic-acid chain instances, and zero generated other
polymer chain instances. It also has a primary X-ray, electron-microscopy, or
neutron method, one coordinate model, and a 20--1024 residue construct.
Water, ions, and small molecules remain allowed in the primary `monomer_clean`
view; entries with zero small-molecule atoms are marked `monomer_apo_like`,
while polymer-context cases remain `contextual`.

Resolution, residue/backbone/heavy-atom completeness, chain breaks, and geometry
thresholds are intentionally deferred until the full Stage A catalog and Stage
B materialization distributions are available. The 244,406-entry Stage A scan
is launched as deterministic 256-shard jobs; only the catalog is generated at
this stage.

## 2026-09-15: Use Biopython pairwise identity for split construction

Decision: use Biopython `Bio.Align.PairwiseAligner` as the authoritative
sequence-identity calculator for the later split stage. The mode is global with
match `+1`, mismatch `-1`, gap-open `-1`, and gap-extend `-1`; identity is
identical residues divided by all global alignment columns, including gaps.
Exact sequence SHA256 is only a lossless candidate index, and same-digest
buckets are still pairwise-verified. CPU job-array parallelism is acceptable
for this offline construction step. No split is generated until the catalog
and Stage B GT are accepted.

## 2026-09-15: Accept full Stage A catalog and exact-SI candidate manifest

Status: the complete 256-shard Stage A scan contains 244,406 entries and
244,406 unique PDB IDs, with zero non-empty error files, zero partial outputs,
zero unresolved SIFTS rows, and zero missing assembly-composition records. The
catalog aggregate shard-manifest hash is
`8e62a4bdf1ee1ba4967e7b35fb2f3fd7f2de067055dbde9d81f10a113d581cf0`.

The frozen catalog-only monomer policy selects 84,232 `monomer_clean` entries;
64,674 have initial release on or before 2021-09-30 and 19,558 are later.
18,427 are also eligible for the zero-small-molecule `monomer_apo_like`
subset. Full-catalog resolution and sequence-length medians are 2.15 A and
225 aa; candidate-view medians are 1.90 A and 283 aa. These are descriptive
statistics only; Stage B completeness and geometry thresholds remain pending.

Strict 100% identity processing has completed on the candidate table. The
Biopython 1.87 global calculator verified 42,640 same-sequence member pairs,
forming 41,592 exact sequence groups from 84,232 records. The manifest is an
exact-sequence grouping artifact, not a near-homology split; all exact groups
must remain atomic in a later split.

## 2026-09-15: Run and accept the Stage B 10k materialization pilot

Decision: use an 8,000-record stratified sample plus 2,000 deterministic stress
cases for the first Stage B audit. Materialize fixed atom37 heavy-atom tensors
in NPZ tar shards and keep compact chain/residue/provenance/QA metadata in JSON;
do not duplicate coordinate arrays in the metadata file. The multi-chain-aware
materializer uses Gemmi assembly operators, while the current candidate view
contains one selected protein chain per biological assembly.

Validation: 32/32 workers completed 10,000/10,000 records with 64 tar shards,
20,000 paired tar members, zero index/member mismatches, zero shape errors,
zero metadata length errors, zero non-finite valid coordinates, zero mask
inconsistencies, and zero materialization errors. Missing sequence positions
retain sequence/residue metadata but have `residue_mask=false`; no PDBFixer
coordinates are used. After correcting the canonical three-letter fallback for
missing residues, 1,845 records contain at least one modified/noncanonical
component and are retained as a side-chain masking stratum; the earlier 8,721
count was a fallback-token QA false positive.

The pilot coverage medians are 0.943 observed-residue, 0.942 N/CA/C frame,
0.942 N/CA/C/O backbone, and 0.934 canonical-heavy-atom coverage. Same-sequence
variance found 3,373 pilot records in 911 exact groups, with 2,462
representative comparisons and 190 (7.72%) above the fixed RMSD/TM disagreement
threshold. This supports exact-group-aware record sampling rather than uniform
PDB-record sampling, but does not by itself freeze quality cutoffs.

## 2026-09-15: Accept full Stage B and freeze split views

Full materialization succeeded for all 84,232 `monomer_clean` records in 348
tar shards with 168,464 members, zero errors, zero shape/mask/finite-coordinate
violations, and zero missing member pairs. The frozen quality policy produced
78,259 Train-valid records, 45,815 HQ-Eval-valid records, and 5,973 rejects.

Quality-filtered exact groups and the initial-release cutoff (2021-09-30) now
define the split artifacts: 31,689 train-seen groups / 59,959 records, 6,711
unseen temporal test groups / 12,940 records, and 932 leakage-excluded
post-cutoff same-sequence groups / 5,360 records. The near-homology audit uses
Biopython `PairwiseAligner` with a separate high-gap-cost global scoring policy,
residue identity, shorter-sequence coverage >=0.70, and at least 50 aligned
residues. Only 15 groups / 18 records pass the strict <0.30 identity boundary;
the temporal test remains the primary held-out benchmark. ESMC embeddings are
not yet cached; they are the next data-layer operation and will be keyed by
exact sequence SHA256 plus model revision.

## 2026-09-15: Freeze GT quality v1 and launch full Stage B

Decision: apply a two-tier coordinate policy after full materialization. Train
v1 requires resolution <=4.5 A, N/CA/C frame coverage >=0.80, canonical
heavy-atom coverage >=0.75, internal missing fraction <=0.15, finite valid
coordinates, zero unexplained CA breaks, zero chirality violations, and zero
configured bond/peptide outliers. HQ-Eval v1 tightens these to <=3.0 A,
0.95/0.90 coverage, and <=0.02 internal missingness. Terminal missingness is
allowed and remains masked; modified residues are retained with unmapped side
chains masked. Clash counts and density are recorded only, not hard filters in
v1.

The 84,232 `monomer_clean` candidates are materialized in full Stage B tar
shards. The resulting per-record quality index is the authoritative input for
rebuilding exact-sequence groups and the 2021-09-30 time split. A group is
train-seen if it has a valid pre/on-cutoff member; later records of such a group
are leakage-excluded rather than test records. Only groups whose valid members
are all post-cutoff are test candidates. ESMC caching remains downstream of
this quality/split stage.

## 2026-09-15: Pin ESMC representation cache contract

Decision: use `biohub/ESMC-600M` at HF revision
`28aed46fcaf217dfa59f78a589bb449aa3ae5d98` with Biohub/esm revision
`bf343ba264b650dff7a073643725f9aaa1fdbe8d`. Build a 2,000-group all-layer
probe first, compare final/intermediate/all-layer representations with a small
structure-aware contact probe, and only then materialize the full 38,400-group
cache. Store residue-aligned BF16 features in sharded safetensors keyed by
sequence SHA256 and pinned model revisions.

Reason: Biohub ESMC exposes 36 transformer layers plus an embedding state, and
the folding representation may not be optimal at the final MLM layer alone.
Caching all layers for the full corpus would multiply storage by roughly 37, so
the probe is a cheap, reversible decision gate. ESMC remains a frozen sequence
representation prior; it is not treated as a structure-coordinate teacher.

The local 2,000-group all-layer smoke completed 2,000/2,000 groups and 594,600
residues in 37 BF16 safetensors shards. A preliminary 500-group,
group-held-out CA-contact probe (32,000 balanced pairs) scored layer 36 at
AUROC 0.706, versus 0.635 for layer 34 and 0.615 for a simple 12/24/36
concatenation. This is a representation diagnostic rather than a folding claim;
the final-layer result supports using `feature_variant=final` for the full
cache while retaining the all-layer probe as an auditable artifact.

## 2026-09-15: Accept the ESMC-600M final-layer cache

The pinned final-layer cache completed on one A800 in 33m47s using local-only
Hugging Face files. It contains 38,400/38,400 quality-valid exact sequence
groups, 11,615,845 residue rows, 178 sharded safetensors, and 26.8 GB of
BF16 feature data. The independent Slurm validator completed successfully in
1m11s with exact group coverage, unique manifest IDs, model/revision checks,
BF16 shape checks, and per-shard SHA256 checks. The cache is stored under
`/hpc2hdd/home/shuang886/Folding/esmc_600m_final_v1`; ESMC all-layer features
remain available only in the 2,000-group probe artifact to avoid multiplying
the production cache by 37. A pinned-model recomputation of one 327-residue
sequence matched its cached slice at cosine 0.999992 (maximum absolute error
0.00387 in float32 comparison after BF16 storage), and eight random cached
slices were finite with exact residue-by-hidden shape.

## 2026-09-15: Freeze Stage 0A dev/test views and factorial protocol

The Stage 0 compatibility baseline remains official
`protenix_mini_esm_v0.5.0` with its native ESM2 conditioner; the ESMC cache is
not used in this baseline. The protocol is now the complete 3x3 factorial over
cycles `{1,2,4}` and structure steps `{1,2,5}`, one sample, BF16, MSA/template
off, and maximum length 1024. The anchor is `(4,5)` and the variance seeds are
`101,103,107,109,113`.

From the 6,711 post-cutoff temporal candidate groups, 3,464 have HQ-valid
targets. A deterministic joint-stratified selector (length, resolution,
apo-like, method) froze 1,024 `temporal_dev_v1` groups, a nested 128-group
`temporal_variance_v1` subset, and 2,440 remaining HQ groups as
`frozen_temporal_test_v1`. All 15 strict low-homology groups are excluded from
dev sampling and listed in `frozen_temporal_low_homology_groups_v1`; eight have
HQ targets and seven remain group-only exclusions because no HQ target exists.
Repeated generation with the same seed produced identical manifest SHA256s.

The first Protenix runner targets the `i64m1tga800ue` partition with one A800
per independent factorial-point job and records command/environment plus
`/usr/bin/time -v` output. The modern `protenix==1.1.0` CLI is used to load the
`protenix_mini_esm_v0.5.0` checkpoint; the package wheel and checkpoint SHA256
are pinned separately. A compute-node smoke test and fixed kernel/backend
metadata are required before the sweep; no Stage 0 accuracy result is claimed
yet.

## 2026-09-15: Submit Stage 0 points as independent A800 jobs

Decision: do not request all eight A800s on one `i64m1tga800ue` job. Submit
each of the nine `(cycle, step)` settings as its own one-GPU job with 8 CPUs,
64G RAM, and a default 12-hour walltime. This matches observed scheduler
placement and makes a failed setting independently restartable without
repeating the other eight points.

The staged ESM2 conditioner is `esm2_t36_3B_UR50D.pt` with SHA256
`7de8b4082ba15891959ab368b77ce3886697af1efb16d3c9e9e7b0c5d3f07500`; it is
stored beside the Mini checkpoint under the pinned Protenix runtime root.

The functional gate and full 3x3 sweep were submitted on hpc2 as independent
one-GPU jobs. The smoke gate is job `12754884`, the one-target functional gate
is `12755045`, and the nine factorial jobs are `12755102` through `12755110`.
All full jobs depend on `afterok:12755045`; pending scheduler state is not an
inference result.

## 2026-09-16: Complete Stage 0A A800 sweep and preserve lightweight results

All nine independent `i64m1tga800ue` jobs completed with exit status 0. Each
of the 1,024 frozen temporal-dev targets produced one CIF and one confidence
summary for every `(cycle, step)` setting, for 9,216 predictions total. The
confidence summaries had zero parse errors and zero `has_clash` flags; peak RSS
was approximately 17.2 GiB per job. The full machine-readable summary is
tracked in `reports/stage0_runtime_summary_2026-09-16.{json,csv}` and the
reproducible parser is `scripts/summarize_stage0_runs.py`.

This result is explicitly a runtime/output-yield checkpoint, not a folding
accuracy result. Raw multi-gigabyte CIF/JSON outputs remain on HPC at
`/hpc2hdd/home/shuang886/Folding/stage0_v1/protenix_runs`; GT-backed TM-score,
lDDT, RMSD, and geometry evaluation must happen before interpreting the
factorial quality surface.

## 2026-09-16: Complete Stage 0B GT-backed collapse-surface scoring

All 9,216 Stage 0 predictions were evaluated against their exact sequence-group
Stage B GT targets. The evaluator reported 9/9 settings with 1,024/1,024
successful records and no parse or alignment errors. It computes fixed-residue
Kabsch Cα TM-style score, Cα lDDT, all-heavy-atom lDDT, Kabsch backbone RMSD,
and sidechain RMSD; the aggregate definition and caveat are documented in
`reports/stage0_eval_summary_2026-09-16.md`.

The mean Cα TM-style surface was:

```text
             step=1  step=2  step=5
cycle=1       0.8809  0.8816  0.8794
cycle=2       0.8933  0.8944  0.8894
cycle=4       0.9029  0.9009  0.8990
```

All-atom lDDT showed the same broad cycle effect but non-monotonic step effect.
Against the paired `c4_s5` anchor, `c1_s1` had median Delta TM -0.0051 and
11.5% of targets below -0.05; `c2_s2` was effectively tied (median +0.0002),
and `c4_s1`/`c4_s2` were slightly above the anchor on this dev view. This is
evidence to prioritize recycle/trunk collapse and internal structure timing;
it is not a final temporal-test result and does not yet justify a MeanFlow
method claim.

## 2026-09-16: Add paired bootstrap and hard-tail diagnostics

The 1,024-target paired analysis uses `c4_s5` as an anchor and 5,000
target-level bootstrap resamples. For `c1_s1`, mean Delta TM-style score was
`-0.0181` (95% bootstrap CI `[-0.0222,-0.0142]`), median Delta was `-0.0051`,
and 11.5% of targets fell below `-0.05`. For `c2_s2`, mean Delta TM-style
score was `-0.0047` (CI `[-0.0080,-0.0016]`) and mean Delta all-atom lDDT was
`-0.0012` (CI `[-0.0023,-0.0002]`). `c4_s2` was above the anchor on mean
all-atom lDDT by `+0.0071` (CI `[+0.0065,+0.0077]`) on this dev view.

The `c1_s1` Delta-TM `< -0.05` tail contains 118/1,024 targets. Its median
length was 369.5 residues versus 281.0 outside the tail, and median resolution
was 2.00 A versus 1.80 A. These are descriptive signals, not causal evidence;
the next experiment profiles internal model stages and tests representation/
confidence-based adaptive recycling.

## 2026-09-16: Profile internal Stage 0 model timing

Four independent A800 profiling jobs (`c1_s1`, `c1_s5`, `c4_s1`, `c4_s5`)
ran on the same 128-target prefix with a runtime-only `sitecustomize` overlay.
The overlay GPU-synchronizes wrappers around pairformer, diffusion, and the
confidence head and writes one record per target without changing model code or
outputs. On the shared-node comparisons, `c1_s5 -> c4_s5` increased median
pairformer time by approximately `0.585 s` and median model-forward time by
`0.587 s`; `c4_s1 -> c4_s5` increased median diffusion time by `0.053 s` while
median pairformer time changed by `0.002 s`. The timing scope excludes model
load, preprocessing, and output serialization. These results support treating
recycle/trunk collapse as the primary efficiency target and structure-step
collapse as a secondary optimization.

## 2026-09-16: Advance to predictive, risk-aware recycling

Stage 0D uses only `temporal_dev_v1`; the frozen temporal test remains unread.
GT oracle routing confirms meaningful target-dependent recycle demand. On the
practical `c1_s1 -> c2_s2 -> c4_s5` path, jointly requiring TM-style score and
all-atom lDDT within 0.01 of `c4_s5` needs 2.231 mean cycles, a 44.2% reduction
from fixed four-cycle inference. The fixed-`s1` joint oracle needs 2.568 mean
cycles under the same tolerance. These are unattainable upper bounds that
assume reusable intermediate cycle states, not router results.

The first predictive audit defines hard targets as `c1_s1` TM-style degradation
below -0.05 versus `c4_s1` (126/1,024 targets). Five-fold out-of-fold evaluation
groups 784 closest-pre-cutoff-train sequence proxies. Cycle-1 confidence raises
AUROC from about 0.63 for sequence-only features to 0.87--0.89. At TM
catastrophic risk <=1%, the best simple learned router uses 2.066 mean cycles,
versus 2.102 for a pTM threshold and 2.465 for the reactive cycle-1-to-cycle-2
distance-map convergence baseline. However, joint TM/all-atom risk is harder:
the learned router needs 3.177 cycles at <=1% joint risk, while the reactive
baseline needs 2.920. Therefore a generic classifier is not yet the method;
future work must test joint-risk targets and genuinely cycle-1 internal state
features before making a novelty claim.

## 2026-09-16: Complete cycle-1 internal-state router audit

The pinned Protenix cycle-1 hook completed on A800 job `12759723` with
1,024/1,024 records, one Pairformer-cycle state per target, and zero feature
errors. It records compact single/pair representation statistics without
persisting model tensors. The analysis is in
`reports/stage0d_router_analysis_internal_2026-09-16.{json,md}`; the JSON
records the feature-file SHA256 for provenance.

Adding these internal statistics to cycle-1 confidence features changes the
TM-catastrophe (risk <=1%) HGB policy from 2.066 to 2.031 mean cycles. For the
joint TM/all-atom risk <=1% constraint it changes 3.177 to 3.156 mean cycles;
the geometry-plus-internal variant is not consistently better. These are
small, dev-only, out-of-fold diagnostic gains on `temporal_dev_v1`, not a
method claim. The frozen temporal test remains unread. Stage 0D therefore
continues to treat predictive risk-aware recycling as the research question,
with `c2_s2` and reactive convergence retained as strong non-learned baselines.

For sidework, use the two Precision W7900 cards for the pinned ESMC-300M scale
ablation. Hash-partition the 38,400 exact sequence groups across two independent
cache writers, merge only manifests, and validate full coverage/checksums. Do
not recompute the already accepted ESMC-600M cache or use ESM3 structure-track
outputs as teacher labels.

## 2026-09-16: Accept the Precision ESMC-300M scale-ablation cache

The two W7900 partitions completed in 840.2 and 847.4 seconds. Their merged
cache contains 38,400/38,400 groups, 11,615,845 residues, and 719 BF16
safetensors shards occupying 21 GB. The independent validator checked every
shard checksum, feature shape, model/revision field, sequence length, and exact
group coverage. The pinned model revision is
`f0d413606442e6b433d5e75e9aae3285ca9b137f`; the Biohub/esm revision remains
`bf343ba264b650dff7a073643725f9aaa1fdbe8d`. Use this cache only for the 300M
conditioner ablation; ESMC-600M remains primary. An independent recomputation
of one 125-residue sequence matched its cached `[125,960]` BF16 slice at cosine
0.9999932 with maximum absolute error 0.0009766.

## 2026-09-16: Complete Stage 0E c2-to-c4 routing audit

An independent two-cycle `c2_s2` Protenix run completed on A800 job
`12761522` in 29:56 with 1,024 predictions and zero hook errors. Stage 0E
labels a target hard when `c2_s2` is worse than `c4_s5` by more than 0.05 in
TM-style score or all-atom lDDT; 76/1,024 dev targets are hard under this
joint label. The feature artifact and input checksums are recorded in the
Stage 0E JSON report.

At joint catastrophe risk <=1%, the GT oracle needs 2.129 mean cycles. The
best current family-proxy grouped OOF learned policy is HGB with c2 confidence
and c1-to-c2 trajectory features at 2.477 cycles; c2 confidence plus deltas is
2.475. The existing reactive c1-to-c2 distance baseline is 2.551 cycles, so
the learned policy closes only a small part of the oracle gap. A matched-setting
`c1_s1` to `c2_s2` coordinate-change proxy is weaker at 2.729 cycles and is not
an in-forward intermediate structure.

This is a positive but diagnostic result, not yet a method claim. Thresholds
are swept on the same OOF predictions, so the next methodological gate is
nested calibration or a held-out dev split before any frozen-test evaluation.
The current default remains fixed `c2_s2`; recycle emulation is not started
until this calibration is complete.

## 2026-09-16: Start Stage 1A recycle residual characterization

The router line is frozen as a diagnostic; Stage 1A asks whether the c2-to-c4
refinement itself is cheap to approximate. A residual hook was added in
`scripts/protenix_residual_sitecustomize.py`; it keeps only the previous cycle
tensor and emits compact single/pair residual norms, sequence-distance
locality, and pooled spatial/channel low-rank energy. It never serializes full
`L^2 x d` pair tensors.

Before the hidden-state hook completed, the existing standalone c2_s2 and
c4_s2 predictions were compared as a coordinate proxy. Across 1,024
temporal-dev records, median Kabsch C-alpha RMSD was 1.076 A and median
pair-distance RMSD was 0.752 A. The 76 joint-hard records had medians 5.234 A
and 3.422 A, with median residue-displacement p90 7.068 A and active-residue
fraction 0.908, versus 0.747 A and 0.064 for nonhard records. This is strong
evidence that late recycle correction is concentrated in a small hard tail,
but it is explicitly a cross-setting coordinate proxy rather than an
in-forward hidden-state residual.

The expanded coordinate audit adds residual concentration/locality diagnostics.
For joint-hard targets, the median top-10-residue displacement-energy fraction
is 0.275 versus 0.676 for nonhard targets, while median pair-distance residual
energy within sequence distance <=8 is 0.0027 versus 0.0126. Thus the hard
tail is not simply a few local side-chain edits; its c2-to-c4 coordinate proxy
is a broader rearrangement. Hidden-state residual measurements are still
pending the A800 smoke/full hook.

## 2026-09-16: Fix residual hook shape and failure handling

The first A800 residual smoke reached the model output successfully but exposed
two hook-only bugs: Protenix's Pairformer hook emits unbatched `[L,C]` and
`[L,L,C]` tensors, and an exception while summarizing one transition removed
the previous-cycle tensor before later transitions could use it. The hook now
normalizes optional batch dimensions and only releases the previous tensor after
the residual summary succeeds. The original model prediction was unaffected;
the residual full run remains gated on a clean replacement smoke.

The replacement A40 smoke confirmed the shape fix but found a second
diagnostic-only backend issue: CUDA `linalg_eigh` does not support BF16 on that
GPU. Channel covariance is now explicitly accumulated in FP32 before the
eigendecomposition; model inference remains BF16 and unchanged. A clean smoke
is required again before the full residual run.

The subsequent A40 run showed the same BF16 limitation inside pooled spatial
SVD (it dispatches through CUDA eigendecomposition). The pooled spatial
diagnostic is now also cast to FP32; all residual summaries are analysis-only
and do not alter Protenix inference.

## 2026-09-17: Pass the Stage 1A residual smoke gate

The final single-target smoke (`12767861`) ran on an A40 debug node in 1:27
with the pinned Mini-ESM runtime and produced one `cycle_count=4` JSONL row with
all three transitions (`c1_to_c2`, `c2_to_c3`, `c3_to_c4`) and zero
`feature_error` fields. The diagnostic hook performs its linear algebra on
detached CPU FP32 tensors for cross-GPU determinism; Protenix inference remains
BF16. The short emergency smoke was cancelled after the debug smoke passed.
Full `c4_s2` residual characterization over `temporal_dev_v1` is submitted as
A800 job `12767871` with 8 CPUs and 64G RAM.

## 2026-09-17: Close Stage 1A and start parallel residual-emulation branches

The full Stage 1A job `12767871` completed with 1,024/1,024 valid rows and all
three transitions. The corrected analyzer now recovers sequence length from
the Stage 0E `features.log_length` field and reports length bands plus partial
correlations. Pair residual mean remains correlated with c2 all-atom
degradation after length control (approximately -0.40 for c2-to-c3 and
c3-to-c4), so raw Frobenius scaling is not the sole explanation. The pooled
rank-8 result is explicitly interpreted as low-rank spatial magnitude
structure, not a claim about the signed `L x L x d` residual tensor.

The next work is parallel rather than serial. `select_teacher_pairs.py`
selects one deterministic quality-valid pre-cutoff train record per exact
sequence group; a 32-group end-to-end teacher smoke passed on two debug A40
jobs (`12769064`/`12769065`) with 32/32 predictions for both settings and
validator coverage 64/64. The 16-shard, 16,000-group
`c2_s2` and `c4_s2` arrays are queued as Slurm jobs `12768989` and `12768990`
on `i64m1tga800ue`. The first queue attempt exposed and fixed zero-padded
array-shard and Protenix environment propagation issues before any inference
ran. The input selector accepts the frozen train-only manifest
which omits an explicit `split` field, while still filtering a combined
manifest when one is supplied.

The residual overlay now has an opt-in `ONESTEPFOLD_SIGNED_SKETCH=1` path that
writes deterministic FP16 spatially pooled signed pair sketches and records
cosines between adjacent residual directions. A one-target A40 debug smoke
(`12768912`) passed with all three transition sketches and direction cosines;
the corrected 256-target `c4_s2` diagnostic is queued as `12769005` on the
debug partition and is a diagnostic artifact only. It does not read the frozen
temporal test. Coordinate-refiner training remains gated on
successful teacher-pair QA; no new model claim is made yet.

The first 1B implementation is now in `src/onestepfold/models/coordinate_refiner.py`.
`GlobalCoordinateRefiner` is deliberately a C-alpha-only baseline: a small
global Transformer predicts a bounded correction in a residue-local N/CA/C
frame and returns the correction in Cartesian coordinates. Unit tests verify
rigid-transform consistency and residue/frame masking. It is a benchmark
component, not an all-atom replacement or a claim that the late residual is
local.

The 256-target signed-sketch diagnostic (`12769005`) completed on the debug
A40 node with 256/256 rows and 1,280 sketches. Adjacent residual directions
are not aligned: pair cosine medians are -0.086 (`c2->c3`) and -0.131
(`c3->c4`), while single cosine medians are -0.122 and -0.289. The signed
random-projection spatial sketch has median rank-8 energy about 0.82 for the
late transitions, substantially below the nonnegative magnitude-map rank-8
energy around 0.99. Therefore the simple scalar fixed-point extrapolation is
not promoted as the primary emulator; keep it only as a cheap negative
baseline, and prioritize a learned global coordinate residual or a richer
signed latent probe.

## 2026-09-17: Isolate Protenix teacher-shard working directories

Decision: every Slurm teacher-pair shard must run Protenix from a private
working directory under its output directory, and the wrapper must return a
non-zero status when Protenix logs per-target `Data error` messages.

Reason: Protenix's ESM2 featurizer writes a relative `./esm_embeddings`
directory. Concurrent c2/c4 array tasks sharing a process working directory
overwrote each other's temporary sequence-to-embedding index. The Protenix
runner can still exit zero after skipping data-error targets, so Slurm's
`COMPLETED` state is not sufficient evidence of a complete teacher shard.
Teacher-pair validation must require matching c2/c4 artifacts and empty data
error logs. The corrected wrapper is committed as `79da1e8`; formal isolated
arrays are `12770049` and `12770050`.

## 2026-09-17: Restrict teacher pairs to Protenix-supported sequences

Decision: teacher-pair generation uses only sequences in the canonical
20-amino-acid alphabet `ACDEFGHIKLMNPQRSTVWY`. Groups containing `X`, `U`,
`B`, or `Z` remain in an explicit exclusion manifest and are not silently
canonicalized.

Reason: the accepted PDB GT contains 171 unsupported-symbol groups in the
initial 16,000-group input (320 rows were excluded when selecting the corrected
v3 pool because the selector operates on the full pre-cutoff group table).
Protenix Mini's `PROTEIN_1to3` parser raises `KeyError` for these symbols.
This is a teacher compatibility filter only; the observed GT dataset remains
unchanged. The corrected v3 input has 16,000 valid groups across 16 shards,
and arrays `12771048`/`12771049` are the only current formal submissions.

## 2026-09-17: Accept the mixed-source c2/c4 teacher corpus

Decision: accept the consolidated DiamondHill teacher corpus for downstream
paired analysis. c2 shards 0--11 come from hpc2 array `12771048`, c2 shards
12--15 come from hpc3 ACD jobs `628767--628770`, and c4 shards 0--15 come from
DiamondHill. Preserve this mapping in the corpus provenance rather than
treating the c2 setting as single-backend output.

Reason: uniform validation on DiamondHill found all 16,000 expected group IDs
in both settings. Exhaustive QA parsed all 32,000 CIF files, checked every
confidence JSON and expected recycle count, and matched every shard log to its
expected successes with zero data errors. This establishes completeness and
artifact integrity; it does not establish numerical equivalence between GPU
backends. Consolidation was copy-only and did not move or modify EngramFold,
shared protein data, or Protenix checkpoints.

## 2026-09-17: Freeze the exact-group teacher split and loader contract

Decision: freeze `teacher_pair_manifest_v1` with 14,400 train groups and 1,600
validation groups. Assignment uses seed 101 and a versioned SHA256 rank over
the exact-sequence group ID. The 16,000-row teacher pool already contains one
record per pre-cutoff exact group; the frozen temporal test is not read or
modified by this split.

The paired loader resolves artifact paths relative to the accepted output
root, parses c2/c4 lazily, verifies the declared sequence, requires identical
atom keys, preserves missing backbone atoms as masks, and performs no
coordinate imputation. It also requires `num_recycles=2` for c2 and 4 for c4.
An exhaustive DiamondHill pass loaded all 16,000 pairs, aligned 37,321,433
atoms, and found zero failures or missing N/CA/C/O atoms. This freezes the
input contract for the first coordinate-refiner baseline; it does not imply
backend equivalence or model-quality calibration.

## 2026-09-17: Use hpc3 as the sole OneStepFold training host

Decision: all subsequent OneStepFold training runs on hpc3. DiamondHill keeps
the accepted source/archive copy of the c2/c4 teacher corpus, while hpc3 uses
the copy rooted at `/data/user/shuang886/Folding/stage1b/teacher_pairs_v3` and
the existing `/data/user/shuang886/Folding/esmc_600m_final_v1` cache.

The transfer was copy-only, excluded transient Protenix `work` directories,
and did not delete or modify the source. The compact teacher output on both
systems has 64,094 files and 7,608,200,910 bytes with the same relative-path
and size digest. hpc3 independently found 16,000/16,000 c2 and c4 predictions.
Its ESMC manifest contains 38,400 exact groups and covers every teacher group
with zero missing records or sequence-length mismatches. A joint smoke loaded
one paired CIF example and its `[L,1152]` BF16 ESMC slice successfully. This is
an infrastructure acceptance, not a coordinate-refiner quality result.

## 2026-09-17: Pass the 32-target coordinate-refiner overfit gate

Decision: use frozen ESMC-600M final-layer residue features, c2 backbone
coordinates, and a c4 C-alpha target rigidly Kabsch-aligned into the c2 frame
for the first coordinate-refiner training path. Load ESMC ranges lazily from
their safetensors shards, keep atom/padding masks explicit, and batch by length.

hpc3 H100 job `629419` trained on the 32 shortest records in the frozen train
split. The aggregate uncorrected c2 baseline C-alpha RMSD was 1.2432 A; the
best training RMSD was 0.1712 A at epoch 255. The final-to-baseline RMSD ratio
was 0.1377 and the final-to-initial coordinate-MSE ratio was 0.000612, passing
the predeclared 0.50 and 0.10 gates. This establishes implementation integrity
and small-set capacity only. It is not validation evidence and does not justify
an all-atom or thermodynamic claim. The next gate must select checkpoints only
with the frozen 1,600-group validation split.

## 2026-09-18: Test explicit c2 geometry with a matched Stage 1B pilot

The user approved the geometry-conditioning experiment after inspection found
that the original Transformer consumes only ESMC and sequence positions. The
original c2 frames only rotate the output correction. The new optional
`radial_frames_v1` branch summarizes all other valid c2 residues in 16
log-spaced radial bands (2--128 A): density, mean unit direction in the query
frame, and mean relative frame orientation. A 208-to-hidden linear projection
adds these invariant features before the existing Transformer. The generic
geometry helper lives in `src/fastglycan/models/relative_geometry.py`, following
repository guidance for new importable code. Existing protein orchestration
remains in `src/onestepfold`.

Keep the original loss, target alignment, frozen teacher/ESMC artifacts,
4,096/1,600 group selection, seed 101, AdamW learning rate 0.0003, weight decay
0.0001, batch size 8, hidden size 128, two layers, BF16, ten epochs, and existing
validation-only coordinate-MSE selection and both 0.95 acceptance ratios.
Initialize shared parameters identically to the baseline; the added projection
has 26,624 parameters, so this is an input-branch experiment rather than a
strictly capacity-matched ablation. No frozen temporal-test reads are allowed.

Tests must verify rigid-transform consistency, sensitivity to relative geometry
once the zero-initialized output head is nonzero, padding exclusion, and finite
geometry gradients. Run a batch-8 length-1024 BF16 forward/backward check on
HPC3 before training. Use an isolated code snapshot and output directory, and
record source hashes with the training report. Loss/weighting changes are
deferred to a separate experiment so they do not confound this comparison.

The approved geometry pilot completed on HPC3 H100 as job `629570` (exit 0:0,
6:22 elapsed). All 18 focused tests and the longest-batch BF16 GPU check passed.
The exact training contract matches baseline `629499` apart from the geometry
feature field. The selected epoch-6 checkpoint was revalidated on all 1,600
groups: CA-RMSD 4.21877 A versus c2 4.34962 A (ratio 0.96992), pair-distance
RMSE 3.30074 A versus c2 3.18466 A (ratio 1.03645). Every evaluated epoch had
distance error worse than c2. The joint 0.95 gate is not met: keep this as a
diagnostic checkpoint, with a separate loss ablation as the next experiment,
not automatic full training. Source/checkpoint hashes and the matched comparison
are recorded in `reports/stage1b_geometry_comparison_2026-09-18.md` and its JSON
artifacts. The frozen temporal test remains unread.

## 2026-09-18: Isolate pair-distance supervision and audit per-protein behavior

The active user goal authorizes continued experimental progress toward efficient
protein refinement, with HPC3 preferred for computation and persistent memory
updates. After the geometry-only pilot improved CA coordinates but worsened
distances, predeclare two bounded distance-loss pilots: coordinate MSE plus
lambda times pair-distance MSE, with lambda 0.5 and 2.0. Pair MSE pools all valid
unordered within-protein pairs per batch, in FP32 with explicit padding masks.
This changes supervision only. Keep the geometry architecture, seeded initial
weights, 4,096/1,600 exact groups, ten epochs, optimizer and original coordinate-
only checkpoint selection fixed; both original <=0.95 error-ratio gates remain.
Resume fingerprints must include the new objective to prevent accidental reuse
of checkpoints trained with a different loss. Zero weight preserves old contracts.

Use two independent one-H100 Slurm array tasks, each preceded by the longest-
batch BF16 loss/gradient check. Re-evaluate original sequence-only and geometry-
only checkpoints read-only; emit per-protein CA/distance errors, signed distance
bias, correction norms and radii of gyration, as well as length/residual strata.
Keep pooled acceptance metrics unchanged. Record coordinate and distance losses
separately, plus clipping frequency. New importable loss code lives under
`src/fastglycan/models/geometry_losses.py`.

These bounded pilots are diagnostics toward the original MSA-free, efficient
all-heavy-atom predictor. A passing CA pilot is not completion of that goal;
all-atom geometry, experimental-GT quality and end-to-end cost still require
subsequent validation. Do not repeatedly widen this CA hyperparameter grid if
both loss weights fail: use the per-protein evidence to reassess the representation
or target rather than lowering the gate or treating teacher agreement as GT.

Distance-loss array `629598_[0-1]` was submitted and both tasks are running on
HPC3 H100s. Task 0 uses lambda 0.5 and re-evaluates the prior baselines before
training; task 1 uses lambda 2.0. The 21 focused tests passed on HPC3, and both
longest-batch BF16 loss/gradient checks passed (finite nonzero geometry gradients,
peak allocated memory about 599 MB). The isolated source snapshot is
`.../coordinate_refiner/code_distance_v1_20260918`; output directories are
`pilot_geometry_distance_p05_4096x1600_v1` and
`pilot_geometry_distance_p20_4096x1600_v1` under the same root. Results remain
pending and must be verified from live jobs and final artifacts.

Both distance pilots are now terminal and accepted as complete experimental
artifacts (not successful emulators): `629598_0` completed 0:0 in 7:07 and
`629598_1` in 8:23. Best epochs 9 and 7 revalidate exactly. Lambda 0.5 yields
CA/distance ratios 0.979665/1.002997; lambda 2.0 yields 0.985066/0.994245.
Both fail the unchanged joint 0.95 gate. Contracts differ from the geometry
baseline only in the explicit loss specification; source, checkpoint and
per-protein file hashes are verified.

The full 1,600-group per-protein audit finds that geometry-only predictions
shrink every protein (median radius change -0.1772 A); distance losses reduce
the median shrinkage to -0.0641/-0.0561 A but still shrink about 96% of proteins.
Only 32.81%/31.94% improve both errors. The 636 baseline-error-below-1-A groups
still suffer about 19% pooled distance-error degradation. Even lambda 2.0's
pooled distance improvement has a worse macro per-protein mean than c2.
Report: `reports/stage1b_distance_comparison_2026-09-18.md`.

Stop this loss-weight grid. Next implement and test an indexed pair-geometry
attention ablation against the lambda-2.0 baseline, keeping data/optimizer/loss
fixed, because the current radial branch summarizes neighbors before attention.
This remains a hypothesis; also audit the already-available c2 confidence signal
before any separate confidence-conditioning change. Do not inject c4 residual
strata as inference features or lower the gate. Full training, all-atom geometry,
experimental-GT evaluation and measured end-to-end efficiency remain outstanding
requirements of the original goal; no goal-completion claim is supported.

## 2026-09-18: Test indexed pair-geometry attention at fixed distance supervision

Add optional `pair_bias_v1` on top of the existing radial-frame input branch.
For each indexed residue pair, encode 16 distance RBFs, scaled log distance,
unit directions in both endpoint frames, and relative frame rotation (32
features). A shared 32-to-8 projection supplies additive attention-head biases
to the existing two Transformer layers, adding 256 parameters. It is initialized
to zero after all existing parameters, preserving baseline weights and initial
predictions. Query chunking bounds intermediate pair-feature memory.

Use explicit pre-norm encoder operations through public MultiheadAttention to
preserve continuous additive-bias semantics during both training and inference;
test inference against the gradient-enabled standard encoder path. Verify rigid
invariance, indexed sensitivity, padding, gradient flow and neutral initialization.
The comparison is against `629598_1`: lambda 2.0, same 4,096/1,600 groups,
seed, optimizer, model dimensions, ten epochs, selection and both 0.95 gates.
Confidence remains excluded, to isolate pair conditioning. No new teacher
artifacts or frozen-temporal-test access are needed.

The pair-attention pilot is submitted as HPC3 job `629624` and is running on
an H100. All 28 focused tests pass. The batch-8 length-1024 BF16 GPU check passes
with nonzero radial and pair-bias gradients, about 1.29 GB peak allocated memory,
and the same first two losses as the neutral lambda-2.0 baseline GPU check.
Code and outputs are isolated under `code_pair_bias_v1_20260918` and
`pilot_pair_bias_4096x1600_v1`. A separate read-only c2-confidence audit on the
existing validation groups is running; no confidence feature is added to this
model and no inference-time policy is fitted from validation labels.

## 2026-09-18: Audit and separately condition on existing c2 quality estimates

The 1,600-group read-only audit found strong confidence/residual associations:
pLDDT vs CA error Spearman -0.7347 (length-controlled -0.7377), and gPDE +0.7939
(length-controlled +0.7852). Of 561 groups with pLDDT >=90, 76.65% already have
c2-to-c4 CA error below 1 A, yet the lambda-2.0 refiner worsens pair error for
84.14%. This motivates a separate input ablation; it does not calibrate a
threshold policy or establish experimental-GT accuracy.

Predeclare `c2_quality_v1`: per-CA CIF pLDDT/100, global c2 pLDDT/100, c2 pTM,
and log1p(c2 gPDE), with range checks and masked padding. C4 confidences and
target-derived residual strata are never features. The accepted raw teacher
manifest/cache remain unchanged; this is an opt-in derived input contract,
recorded in checkpoint fingerprints. Add a separate zero-initialized
4-to-hidden confidence projection (512 parameters), preserving shared weights
and initial predictions. Existing deployed checkpoints all have confidence_dim=0
and remain loadable; the new confidence path is explicitly versioned.

Run this against the same lambda-2.0 radial baseline `629598_1`, not combined
with pair bias: same data/seed/optimizer/ten epochs/selection/gates. Keep it
independent from live pair-attention job `629624`. Tests must prove c4-confidence
changes cannot alter input features, confidence padding is isolated, neutral
initialization matches the baseline, and gradients reach the new projection.
Continue per-protein reporting to assess harm to already-close structures.

All 31 focused tests passed on HPC3 (PyTorch 2.7.1). The independent confidence
pilot was submitted as job `629633`, using isolated `code_confidence_v1_20260918`
and `pilot_confidence_4096x1600_v1`. Its launcher requires a longest-batch BF16
GPU gradient/memory check before training. Pair job `629624` remains independent.

## 2026-09-18: Indexed pair attention completed without a material gain

HPC3 `629624` completed 0:0 in 14:20; best epoch 7 gives CA/distance ratios
0.984755/0.996009. Selected-checkpoint revalidation and source/checkpoint/example
hashes all pass. Pair attention does not improve the matched radial baseline
materially, and already-close groups suffer 23.79% pooled distance degradation.
Final-epoch clipping frequency is 96.68%, so this bounded result is not proof
of an irreducible representation ceiling. No full training is warranted.

Added a read-only directional diagnostic from stored RMS norms using
2<r,d>=||r||^2+||d||^2-||r-d||^2. Median cosine is 0.1199 for radial and
0.1225 for pair attention. Even target-aware optimal per-protein attenuation
in [0,1] yields CA ratios only 0.98102/0.97977. This bounds whole-protein
attenuation of these fixed predictions, not retraining, per-residue scaling
or amplification. It is label-dependent and must not become an input policy.
Report: `reports/stage1b_representation_comparison_2026-09-18.md`.

Confidence job `629633` passed the longest-batch BF16 H100 check (599 MB,
confidence gradient L1 0.02289) and has started training. Wait for its declared
ten-epoch result and verify before making the next experimental decision.

## 2026-09-18: Confidence conditioning helps some strata but still fails the gate

HPC3 `629633` completed 0:0 in 6:55, selecting epoch 9 by the original coordinate
MSE rule. CA/distance ratios are 0.978622/0.996743. Full revalidation reproduces
the selected checkpoint metrics; frozen-source, checkpoint and example hashes,
contract matching and 1,600 unique finite rows pass. Checkpoint SHA256 is
`07b4a5ef3c19f0cba2462775b62d418ed87e788056a500109325f097e23145e7`.

Both errors improve for 34.44% of proteins; macro distance RMSE 1.63740 A is
slightly below c2's 1.63990 A. Already-close-group pooled distance harm falls
from 19.00% to 12.27%, but remains material. Radius shrinks for 93.44% of
proteins. Median directional cosine is 0.1301; hindsight whole-protein
attenuation reaches only CA ratio 0.97375. Confidence is informative but these
results do not establish a useful emulator, calibrated uncertainty, or a
successful all-atom predictor. All 31 focused tests and GPU checks passed.

Stop adding variants in this bounded representation comparison. Before another
training run, compare matched training/validation directional behavior and
inspect loss/optimizer gradients on fixed training batches; final-epoch clipping
is 96.68%, which is a diagnostic concern rather than a causal conclusion.
No full training or gate change. Reports, curves and per-protein diagnostics
are in `reports/stage1b_representation_comparison_2026-09-18.*` and
`reports/stage1b_representation_diagnostics_2026-09-18.json`. Original efficient
MSA-free all-heavy-atom prediction remains the active, unfinished objective.

## 2026-09-18: Predeclare read-only train/gradient/Adam audit

Before another training run, evaluate both selected radial lambda-2 and c2
confidence checkpoints on their exact 4,096 training groups and revalidate on
the same 1,600 validation groups. Compare directional alignment and error ratios.
From the accepted training subset select 256 length-stratified groups with seed
103, in deterministic batches of eight. Measure parameter- and output-space
gradient norms/cosines for coordinate versus weighted distance loss, plus the
actual combined BF16-backprop gradient. Replay one AdamW step with clipping 10
and without clipping from the saved model AND optimizer state independently
for each batch. Restore all state between probes, save no trained weights, and
verify the input checkpoint hash remains unchanged. Post-step losses are on
the same training batch; they cannot establish validation improvement or a
better training policy. Frozen temporal test remains untouched.

Submitted as HPC3 array `629639_[0-1]` (radial/confidence) from isolated
`code_optimization_audit_v1_20260918`; outputs are under
`optimization_audit_v1_20260918/{radial,confidence}`. Snapshot import checks
and all 27 copied focused model/training tests pass. The replay uses the actual
joint-objective backward gradient, because separate BF16 backward sums can
round differently. Both separate gradients are retained for alignment analysis.

## 2026-09-18: Audit supports a controlled duration/clipping continuation

HPC3 `629639_0/1` completed 0:0 in 2:00/1:25 with hashes and validation metrics
verified. Training CA/distance ratios are 0.979916/0.987406 for radial and
0.969506/0.983616 for confidence; directional fit is weak on training too.
Only 1/32 and 2/32 fixed batches have opposing coordinate/distance parameter
gradients. Median Adam update norm increases 1.557x/1.346x without clipping;
same-batch objective after the unclipped replay is lower in 32/32 and 31/32.
This is not evidence of validation improvement or proof of clipping causality.

Predeclare two confidence continuation branches from the exact same epoch-10
last checkpoint and saved Adam/RNG state, through epoch 30. Preserve inherited
history and epoch-9 best checkpoint. One retains clipping 10; the other changes
only clipping to 100, retaining a finite outlier guard. All other contracts,
selection, and both 0.95 gates are fixed. Parent artifacts remain immutable;
derived checkpoints explicitly record parent hashes and the threshold change.
No full training or additional representation/loss-weight variants. Report:
`reports/stage1b_optimization_audit_2026-09-18.md`.

Continuation submitted as HPC3 array `629642_[0-1]`, clipping 10/100 respectively,
from `code_clip_continuation_v1_20260918`, output directories
`pilot_confidence_clip10_epoch30_v1` and `pilot_confidence_clip100_epoch30_v1`.
The 28 focused tests pass. Independent recursive comparisons verified both
derived best and last checkpoints against the parent for every model tensor,
optimizer moment, RNG state, history entry, epoch and best metric. Only the
explicit clipping contract/fingerprint and fork provenance change. Trainer
checkpoints/reports now retain initialization provenance through subsequent
resumes; inherited history remains attributed to the parent source snapshot.

## 2026-09-18: Continuation fails; audit teacher stochasticity before more model variants

HPC3 `629642_0/1` completed 0:0 in 9:37/10:46. Both retain best epoch 9 with
ratios 0.978622/0.996743. Epoch-30 ratios are 1.006344/1.031555 (clip 10) and
1.003703/1.023550 (clip 100), despite lower training losses. Selection, inherited
state/history, source/checkpoint/example hashes and revalidation pass. Selected
per-protein files are byte-identical to the parent confidence run. Stop this
duration/clipping experiment; no full training or retrospective gate change.
Report: `reports/stage1b_clip_continuation_2026-09-18.md`.

Independent source/config reconstruction on HPC3 and DiamondHill found the
teacher CLI retains `mc_dropout_apply_rate=0.4` and `mc_dropout_rate=0.4`.
Inspected configuration/runner/model source hashes match across these hosts;
the recorded DiamondHill teacher command contains no MC-dropout override.
The runner seeds once per shard, selects MC dropout per input, applies dropout
inside each recycle when selected, then performs diffusion sampling. Thus
identical seed labels alone do not isolate the recycle effect. This is current
source reconstruction rather than historical runtime tracing; the actual
noise contribution remains unmeasured. Artifact/alignment/split QA still stands.

Predeclare a separate HPC3-only diagnostic, not a teacher-corpus replacement:
eight length-stratified <=256-residue examples from the accepted 4,096 training
groups, selected independently of residuals; reuse identical prepared features.
Compare forced-MC-on c2/c4 with equal per-target seed; MC-off c2/c4 with an
explicit shared diffusion seed; an exact MC-off c4 repeat; and an alternate
diffusion seed. Record actual MC decisions and GPU RNG state hashes at the
diffusion boundary, save coordinates and measure aligned CA/pair differences.
This bounded diagnostic cannot establish a full-corpus noise floor or recreate
the historical mixed-device shard RNG stream. No corpus overwrite, new split,
temporal-test access or further refiner training before reviewing evidence.
No teacher diagnostic job has been submitted yet. Configuration/source report:
`reports/stage1b_teacher_pairing_audit_2026-09-18.md`.

## 2026-09-18: Launch the isolated same-device teacher pairing diagnostic

Implemented runtime-only instance hooks in `src/fastglycan/teacher_pairing.py`
and orchestration in `scripts/audit_teacher_pairing.py`. The focused test
verifies observation of recycle-dependent RNG drift, diffusion-seed control,
preservation of trunk computation/input features, and hook restoration.
All six conditions reuse the same prepared feature object via defensive copies.
Use per-target seed 101; matched diffusion seed 12345, alternate seed 12346;
forced MC application rates 1/0 retain dropout probability 0.4. Explicitly
update both config.model.N_cycle and the model's cached N_cycle attribute.
Save actual flags, feature/trunk/RNG hashes, all-atom coordinates and CA/pair
comparisons, including the original accepted pair for each selected train group.

Submitted as HPC3 H100 job `629659` from immutable source snapshot
`code_teacher_pairing_audit_v1_20260918`, writing
`teacher_pairing_audit_v1_20260918` under the coordinate_refiner root. The
focused RNG-hook test passes. No installed Protenix source, accepted teacher
artifact, split or temporal-test data is modified. Verify the live handle
before any rerun; this is a bounded diagnostic, not a replacement teacher corpus.

The first runtime diagnostic `629659` completed 0:0 in 2:18. All eight MC-on
c2/c4 pairs have different RNG hashes at diffusion entry, whereas explicit
MC-off/shared-noise pairs match. Median CA differences: MC-on 0.819 A,
MC-off/shared-noise 0.280 A, alternate c4 noise 0.585 A, accepted mixed-source
pair 0.796 A. However, exact-repeat trunk hashes differ in 5/8 examples, with
repeat CA error up to 0.609 A despite matching inputs/RNG/MC-off flags. These
numbers cannot yet be treated as an isolated sampling-noise decomposition.
Run the same eight examples/conditions with deterministic algorithms and
CUBLAS_WORKSPACE_CONFIG=:4096:8 before interpreting stochasticity magnitudes.
Keep the original diagnostic immutable; use code_teacher_pairing_det_v1_20260918
and teacher_pairing_det_v1_20260918 as separate source/output paths.

## 2026-09-18: Deterministic teacher pairing reproduces; predeclare bounded v2 pilot

HPC3 deterministic audit `629664` completed 0:0 in 1:27. All eight repeated
c4 trunk hashes and every atom coordinate are exactly identical; c4 alternate-
noise runs retain identical trunk hashes. Forced-MC-on c2/c4 sampler-entry RNG
hashes differ in 8/8; MC-off/shared-diffusion-seed hashes match in 8/8. Median
CA differences: forced MC-on c2/c4 0.81372 A, MC-off paired c2/c4 0.28081 A,
alternate c4 noise 0.56574 A, original mixed-source pairs 0.79605 A. The paired
recycle maximum remains 5.47054 A. All 96 saved coordinate files across both
audits and frozen source hashes pass checks; metrics were recomputed from
coordinates. Source/manifest/checkpoint artifacts remain unchanged.

These eight length<=256 examples demonstrate confounding and a reproducible
alternative, not a full-corpus noise floor or proof that every failed model
was limited by noise. MC-on versus MC-off changes both dropout and noise
coupling; do not report that contrast as a pure dropout effect. Original
artifact/alignment/split QA still stands. Report updated at
`reports/stage1b_teacher_pairing_audit_2026-09-18.md`.

Next implement a separate versioned paired-teacher pilot on 512 train / 256
validation groups, selected with the existing length-stratified seed 101/102
rules from the frozen 14,400/1,600 splits, covering lengths through 1024.
Use HPC3, MC off, deterministic algorithms, per-target reset of feature/trunk
RNG, shared prepared features and a shared c2/c4 diffusion seed. Generate CIF
and confidence files compatible with the strict loader, plus explicit pairing
protocol/hash and RNG traces. Require longest-target repeatability and full
artifact/loader QA before training. Keep original 16,000-pair corpus immutable;
this is a new derived protocol/root, not a replacement or alternative split.

After acceptance compare the same radial/confidence architecture on old versus
new teacher data for identical 512/256 group IDs: same initialization seed,
coordinate+2*pair loss, clip 10, AdamW settings, ten epochs, and coordinate-MSE
selection. This tests a pairing-protocol intervention, including changed c2
inputs, not label-only denoising. The small validation result is exploratory;
the full 1,600-group gate remains required before full training. No generation
or training job for this bounded v2 pilot has been submitted yet.

## 2026-09-18: Launch the bounded paired-teacher generation

HPC3 H100 array `629674_[0-3]` now runs from immutable snapshot
`code_paired_teacher_v2_20260918` under the coordinate_refiner root. New data
root: `/data/user/shuang886/Folding/stage1b/teacher_pairs_paired_v2_pilot512x256`.
The existing selectors yield train lengths 35--1002 and validation 45--1009;
we do not force endpoint examples or change selection. Four deterministic
L-squared-balanced partitions each contain 192 groups. Their longest examples
(1009/1002/951/911 residues) require identical complete c4 traces and every-atom
coordinate repeats before continuing. Each target resets feature and trunk
seed 101 separately, reuses prepared inputs, and resets sampler seed 12345;
MC application rate 0 and deterministic algorithms/CUBLAS control are explicit.
Standard CIF/confidence artifacts pass the strict loader before a trace is
recorded. The protocol, selections, source, checkpoint and artifact hashes are
recorded independently. Nine focused tests pass locally and on HPC3.

Independent acceptance will revalidate all 768 artifact/trace hashes, exact
parent selection identity/order, longest repeats, and the actual confidence-
enabled ESMC/target training join. Only then create the new root's acceptance
marker and run the matched ten-epoch old/new comparison. Trainer contracts now
bind derived data to its accepted protocol hash; original contracts retain
their previous fingerprint. No original teacher data or temporal test is changed.

All four longest examples passed exact complete-trace and every-atom repeats
in the running generation array. Twenty-one focused pairing/training/geometry/
loss/confidence tests now pass locally and on HPC3. Submit independent acceptance
as `629682`, `afterok:629674`; HPC3 requires a GPU request even for this CPU
validator, so its accepted submission explicitly adds `--gres=gpu:1`. The
CPU-only submission was rejected before any job was created. Submit matched
old/new training array `629683_[0-1]`, `afterok:629682`; both dependent jobs use
immutable snapshot `code_paired_comparison_v2_20260918`. Training output roots:
`pilot_original_teacher_512x256_v2` and `pilot_paired_teacher_512x256_v2` under
coordinate_refiner. Both dependencies require successful completion and cancel
if the prerequisite becomes impossible. The trainer also records actual seeded
initial-weight hashes without changing old run-contract fingerprints. Generation
continues; acceptance/training have not run yet. Check live handles before reruns.

The next continuation rechecked live Slurm handles: all four generation workers
remain RUNNING, and acceptance/training remain dependency-pending; no rerun is
needed. Prepared `scripts/summarize_paired_teacher_comparison.py` to verify
actual initialization/group/source/contracts and selected-checkpoint metrics,
then recompute pooled errors and compare curves, residual tails, directional
fit and shrinkage. Use own-protocol relative error for learning comparisons;
also retain fixed original-easy group membership when contrasting harms.
Raw c2/c4 residual changes across protocols are not experimental-structure
accuracy gains. Lint/import checks pass; analysis awaits actual training output.

## 2026-09-18: Controlled teacher generation completes

All generation tasks `629674_[0-3]` completed 0:0 in 13:42, 13:41, 13:32,
12:58, respectively. All 768 pairs were written. Archived controls under
`reports/stage1b_paired_teacher_512x256_2026-09-18/control`; locally verified
all 768 protocol/paired-feature/RNG traces, four worker completions and all
four longest repeat NPZ hashes and exact every-atom equality. Independent
HPC3 acceptance `629682` has started and is reading all artifacts/features;
training `629683_[0-1]` remains dependency-pending. Do not restart generation.

## 2026-09-18: Paired-protocol comparison is negative for the CA refiner

Acceptance `629682` completed 0:0 in 2:26: all 768 pairs / 227,718 residues
pass artifact/trace/source/checkpoint/ESMC/actual-training-read QA. Acceptance
marker, validator source, all worker/trace hashes and four longest every-atom
repeats also pass independent local checks. Old/new matched training
`629683_[0-1]` completed 0:0 in 1:13 / 1:12. Actual initialized-weight SHA256
is identical (`8d8095c2cde9ad40e18caa03d5fb9f053cc0766151cc175dc4e3572e7bc6d738`),
as are ordered groups, source hashes and all non-teacher training-contract fields.
Independent best/last checkpoint hashes, contracts, histories, finite weights,
selected-checkpoint revalidation and per-protein pooled metrics pass.

Original protocol selects epoch 9: CA/distance ratios 0.987727/0.994711.
Controlled paired protocol selects epoch 4: ratios 1.000206/1.000051, with
every validation epoch worse than identity c2 in both metrics. Paired c2/c4
baseline CA RMSD is 2.02620 A versus 3.82983 A original; median per-protein
baseline falls 1.5034 -> 0.4744 A. This is reduced teacher disagreement, not
improved student or experimental-structure accuracy. Paired training MSE barely
falls 1.42380 -> 1.41705, and median correction/residual cosine is 0.0184 versus
0.1021 original. Only 19.14% / 33.59% improve both metrics. The original model
contracts 99.61% of proteins, while paired training contracts only 4.30% and
mostly expands slightly; contraction was not an immutable architectural behavior.
Neither comparison passes the 0.95 reference, and the formal 1,600-group gate
is still unpassed. This bounded result cannot prove that all architectures or
larger training budgets would fail.

Report: `reports/stage1b_paired_teacher_pilot_2026-09-18.md`; curves/diagnostics:
`reports/stage1b_paired_teacher_comparison_2026-09-18.{png,json}`; independent
checkpoint audit: `reports/stage1b_paired_teacher_training_audit_2026-09-18.json`.
All raw control and training report/example snapshots are in
`reports/stage1b_paired_teacher_512x256_2026-09-18/`. No jobs remain from this
experiment; do not rerun or expand the CA-refiner/loss-weight grid.

Next inspect teacher single/pair-state and structure-decoder interfaces before
predeclaring a bounded representation-level distillation diagnostic. The
hypothesis is that post-hoc coordinates discard useful internal information;
the current experiment has not established that cause. Prioritize a route that
supports all-heavy-atom prediction and the eventual one-cycle/one-structure-
evaluation objective. No new training, corpus replacement, split modification
or frozen temporal-test access is authorized by these negative results alone.

## 2026-09-18: Predeclare an internal-state/decoder boundary diagnostic

Direct inspection of the installed HPC3 Protenix source confirms the trunk
returns `(s_inputs, s, z)`. Before diffusion it derives `pair_z` and atom-attention
`p_lm/c_l` caches from z; when cached, `z_trunk` is passed as None. Therefore
interventions must replace trunk outputs before cache construction, not only
replace diffusion kwargs. The confidence head also consumes s and z. The
sampler calls the denoising module once per noise-schedule interval; count
actual calls rather than assuming the eventual one-evaluation target is met.
GitNexus resources/index/tools are unavailable, so this trace uses installed
source directly, following the exploring skill's source-verification principle.

Predeclare eight training-only examples from the accepted controlled 512:
the longest training target plus seven length-stratified examples from the
remaining 511, selector seed 105. No validation or temporal test selection.
Use the already accepted deterministic feature/trunk seed 101 and shared
diffusion seed 12345, MC off, two diffusion steps, one sample, same checkpoint.
Capture native c1/c2/c4 states; require identical input embeddings, agreement
with the accepted c2/c4 feature/trunk traces, and exact all-atom native versus
cached-state c2/c4 replay. Return replay states at the trunk boundary so all
decoder caches rebuild. Then inspect c2-single/c4-pair, c4-single/c2-pair, and
halfway-both states. Save states and all-heavy-atom coordinates with provenance;
record decoder cache hashes and actual denoising NFE. Measure CA, CA-pair and
all-heavy-atom agreement to native c4 under the same noise.

This is an interface and teacher-sensitivity diagnostic with target-aware
interventions, not a learned student, a GT quality experiment, or proof that
the CA-refiner failed because of information loss. It is a bounded prerequisite
for choosing a representation-level all-atom distillation experiment. Keep
all prior corpora/checkpoints/splits immutable; no full training is launched.

Implemented `src/fastglycan/teacher_states.py` and `scripts/audit_teacher_states.py`.
The boundary clones saved states on replay, rejects mismatched input features,
and restores the original teacher method on exit. Three focused state/RNG tests
pass locally and on HPC3, including downstream in-place mutation protection and
cache sensitivity. Submitted H100 job `629756` from immutable snapshot
`code_teacher_states_v1_20260918`, output `teacher_states_audit_v1_20260918`,
both under coordinate_refiner. Runtime results are pending. The primary
ESMC-600M conditioner is unchanged; this is the Mini-ESM teacher compatibility
path. Report: `reports/stage1b_teacher_state_boundary_2026-09-18.md`.

## 2026-09-18: All-atom state replay passes; pair intervention dominates this diagnostic

HPC3 state audit 629756 completed 0:0 in 4:36; independent validation 629768
completed 0:0 in 0:12. Eight lengths: 1002, 53, 170, 233, 295, 305, 361, 539.
Prepared inputs and c2/c4 trunk hashes match the accepted controlled corpus;
input embeddings match across cycles, sampler RNG matches across conditions,
and native versus replayed c2/c4 coordinates match every atom exactly. Decoder
cache hashes follow the pair donor. All 24 saved-state file/tensor hashes and
64 coordinate hashes, source/runtime provenance and recomputed metrics pass;
archived audit/validator/local source and coordinate hashes also pass. All
predictions have exactly two actual decoder NFE. No learned student was trained.

Median/atom-pooled all-heavy-atom RMSD to c4 (A): c1 1.06608/8.16026,
c2 0.43837/3.74213, s2/z4 0.10495/0.47232, s4/z2 0.38737/4.08356,
halfway 0.22323/1.69980. Pair-only improves all eight; single-only improves
five and worsens pooled error, driven by the longest protein. This supports
examining pair-state learning but is a target-aware intervention, not evidence
of learnability, GT quality, or general population behavior. States have
[L,449] FP32 inputs, [L,384] BF16 single, [L,L,128] BF16 pair; 24 tuples occupy
1,321,359,528 raw tensor bytes and remain on HPC3. Report/figure:
reports/stage1b_teacher_state_boundary_2026-09-18.{md,png}. Raw local audit,
validation and all coordinate artifacts: reports/stage1b_teacher_states_2026-09-18/.

Before choosing a learned early-state emulator, reuse the already verified
snapshots for the one-cycle starting point: c1/c4 replay controls, c1-single/
c4-pair, c4-single/c1-pair and halfway c1/c4 states. Keep exactly the same eight
training targets, input/noise and two-step decoder; no target reselection,
regenerated corpus or frozen-test read. This is a bounded additional decode
check, not another c2-only learning detour. No follow-on job is submitted yet.
The original ESMC-600M / efficient one-cycle, one-structure-evaluation all-atom
objective remains active and has not been achieved.

## 2026-09-18: Launch the predeclared c1 state controls after permissions recover

The local test command was interrupted by a sandbox initialization failure
before execution; after the user restored permissions, rechecked files, queue
and absence of the new snapshot. No prior c1 job existed. Local/HPC3 state/RNG
tests (three) and lint pass. Submitted H100 job `630486`, immutable snapshot
`code_teacher_c1_states_v1_20260918`, output `teacher_c1_states_v1_20260918`,
under coordinate_refiner. This reuses the previous eight inputs and verified
c1/c4 snapshots; no new trunk inference or teacher corpus is generated. Check
zero trunk-stack calls, two actual decoder NFE, parent feature/noise/cache
hashes and exact c1/c4 atom correspondence/replay. Conditions are replay c1,
replay c4, s1/z4, s4/z1 and halfway c1/c4. These target-aware controls are not
learned-student results; the original ESMC-600M/all-atom objective is unchanged.

Independent c1 state-composition/coordinate verification is submitted as
`630499`, afterok:630486, with immutable `code_teacher_c1_states_validation_v1_20260918`.
It reloads the parent c1/c4 snapshots, recomputes each prescribed intervention
and its tensor hashes, checks donor-cache dependencies and exact replay against
old coordinates, and recomputes CA/all-atom/pair errors. The c2 reference is
read from the accepted parent coordinates for the same eight targets.

## 2026-09-18: C1 oracle control passes; predeclare a learned pair-state pilot

HPC3 630486 completed 0:0 in 4:00; independent 630499 completed 0:0 in 0:33.
All eight c1/c4 replays are atom-exact. Parent input/source/checkpoint/state,
composed/returned tensor, cache-donor and shared-noise hashes pass; all 40
coordinates/atom identities and recomputed metrics pass. Each cached condition
has zero new trunk-stack calls and two decoder NFE. Three state/RNG tests pass
locally/HPC3; lint/shell/plot checks pass. Do not rerun these jobs.

Median/pooled all-heavy-atom RMSD to c4 (A): c1 1.06608/8.16026,
c2 0.43837/3.74213, s1/z4 0.13103/1.12361, s4/z1 1.19933/7.21675,
halfway c1/c4 0.51796/4.95762. s1/z4 improves 8/8 over c1 and 6/8 over c2;
the 53- and 539-residue cases remain slightly worse than c2. These target-aware
results support testing c1 pair-state learning but do not prove learnability,
generalization, GT accuracy or inference cost. Report/figure and full local
audit/coordinate archive: reports/stage1b_teacher_c1_states_2026-09-18*.

Predeclare the next learned experiment in
`docs/stage1b_pair_state_emulator_pilot_v1.md`. Select a nested 128 train / 64
validation from accepted controlled 512/256 using length-stratified seeds
101/102; no new split or residual-based selection. Export c1/c4 states plus
native c1/c2/c4 coordinates with accepted deterministic provenance and strict
QA before training. Train a shared zero-initialized residual MLP predicting
z4-z1 from c1 pair, c1 endpoint singles, c1 row/column pair means and sequence
separation only. Preserve s1/input embeddings and decoder. The document freezes
widths, twenty epochs, 4096 sampled ordered pairs per protein visit, AdamW
0.0003/0.0001, clipping 10, seed 101 and BF16; select by full held-out macro
pair-state MSE with epoch-zero identity eligible. Require all 64 validation
proteins decoded and compared to c1 AND c2; state-MSE reduction is insufficient.

Both decoded all-atom and CA-pair errors <=0.95 of c1 define an exploratory
learning signal; useful cycle saving additionally requires parity with c2 and
measured lower inference cost. No automatic full training or formal 1600-group
gate claim follows. This is a teacher-side compatibility experiment, still
requiring ESM2-backed c1 inputs and two decoder calls. The original ESMC-600M,
one-cycle/one-structure-evaluation all-heavy-atom objective remains unfulfilled.
No new export/training job is submitted yet.

## 2026-09-18 — Start the predeclared learned-state cache

Submitted HPC3 630528_[0-3], four independent one-GPU workers of 48 groups,
using immutable code_pair_state_export_v1_20260918 and new derived root
pair_state_cache_c1c4_128x64_v1 under coordinate_refiner. The deterministic nested
128/64 selection has manifest hash
1a959fdac83f8688ec9cb1a7deb95e4cf4e06670e9ca4450fcbfc8468d43d33f;
train/validation lengths are 35–951 / 45–770. Original parent records, split
and CIF paths are preserved; CIF paths explicitly resolve against the parent.
Export includes native c1/c2/c4 atoms, c1/c4 states and longest per-worker c4
cached replay, with accepted-parent input/trunk/noise comparisons. Eleven
existing state/pairing/protocol tests and new-source lint pass before submission.
Full independent cache QA and model checks are still required before training.

The first model implementation is now fixed: shared endpoint and row/column
context projections (32 channels each), separate LayerNorms for singles/local
pairs/context, FP32 raw row/column means before normalization, signed i-j
separation. Concatenation has 272 channels, two 256-wide SiLU hidden layers,
and zero-initialized 128-channel FP32 output/addition. All Linear layers have
biases. Training follows the predeclared twenty epochs, per-protein 4096 ordered
pair samples, raw state MSE, AdamW and BF16 protocol; selection uses full-pair
BF16 macro MSE with identity eligible. Five CPU tests pass, including exact
identity, gradients, input restriction, chunk/reload consistency, protein
weighting and BF16 selection. A disposable-model longest-input GPU check must
pass inside the training job before optimization starts. No architecture sweep.
Export 630528_[0-3] completed 0:0 in 6:19–6:26; independent QA 630549 is running.

QA 630549 completed 0:0 (3:11), all 192 samples/11,508,357,752 state bytes,
parent CIF atoms and four longest exact replays accepted. Training 630554
completed twenty epochs, selected epoch 20, macro/pooled state-MSE ratios
0.795290582/0.780328721. Exact selected-checkpoint revalidation and disposable
longest BF16 GPU identity/gradient/chunk/reload checks pass. State loss alone
does not establish success. Decoder array 630570_[0-3] and independent final
QA 630576 submitted with afterok dependencies; all 64 held-out groups must be
decoded with identity checks and compared to both c1 and c2. No end-to-end
latency or experimental-GT claim follows from cached decoding.

## 2026-09-18 — Learned pair-state MSE improves, decoded structure does not

All four decoder jobs 630570_[0-3] completed 0:0 in 2:13–2:48; final independent
QA 630576 completed 0:0 in 1:04. All 64 learned pair tensors independently
recompute exactly. All c1 identity atom replays, checkpoint/source/artifact
hashes, fixed-single/noise/trunk-count checks, full selected-checkpoint state
validation and recomputed structure metrics pass. Each cached condition has
zero trunk calls and two decoder NFE. Eighteen focused local tests pass.

The 187,344-parameter c1-only residual MLP selects epoch 20. Validation macro/
pooled state-MSE ratios are 0.795290582/0.780328721, with 63/64 groups improving.
Pooled c4-relative all-atom errors are c1 2.904474 A, c2 1.934670 A, student
2.945227 A; CA-distance errors are 2.036336/1.441237/2.081999 A. Student/c1
ratios 1.014031/1.022424 fail the <=0.95 exploratory gate; student/c2 ratios
1.522340/1.444591 also fail parity. Student harms 45/64 all-atom and 38/64
CA-distance cases relative to c1; only 16/64 improve both. Descriptive
per-protein state-gain/structure-gain correlations are 0.0745 and -0.0984.

Record this as a negative structural result. Do not extend epochs just because
state MSE is still falling, promote this model, or start full-data training.
This establishes that raw state MSE is insufficient as a structural selection
proxy for this model; it does not prove the architecture or state-emulation
direction fundamentally impossible. Before another learned run, use a bounded
training-only state-component/decoder-sensitivity diagnostic to identify what
the decoder responds to. A decoder-related loss is a hypothesis to validate,
not an established fix. No latency benchmark is needed to claim success for
this failed-quality pilot; end-to-end speed remains unmeasured.

Reports/plot/diagnostics: reports/stage1b_pair_state_emulator_2026-09-18.{md,png,json}.
The matching directory archives accepted cache controls, best/last checkpoints,
history, independent validation, all decoder traces and 128 coordinate files;
local checkpoint/history/control/worker/coordinate hashes verified. Bulk state
tensors stay on HPC3. All jobs completed; no live project jobs remain. Preserve
the frozen parent/test and the original ESMC-600M MSA-free all-heavy-atom,
eventually one-cycle/one-structure-evaluation objective. The formal 1,600 gate
and direct experimental-GT evaluation remain unfinished.

## 2026-09-18 — Predeclare training-only state-component controls

The completed learned pilot is substantive progress and a negative structural
result. Resume from accepted cache/checkpoint artifacts; HPC3 queue is empty.
Predeclare docs/stage1b_pair_component_audit_v1.md before another run: longest
accepted 128-train protein plus seven length-stratified remaining training
groups (seed 105), no validation selection or optimization. Decompose ordered
pair residuals into orthogonal global/row/column/interaction components. Decode
eleven fixed native/learned/oracle/component-hybrid conditions with c1 singles
except the exact c4 replay. Source inspection shows decoder conditioning
concatenates z with relative-position embedding before normalization, projection
and two transitions; raw LayerNorm(z) alone is not the decoder input. Capture
actual pair_z error plus all-atom/distance metrics, independently reconstruct
the cache transform, and retain exact replay/hash/NFE/atom checks. This is a
target-aware diagnostic, not a learned result or a claimed remedy. Two focused
component tests verify reconstruction, orthogonal energy and exact endpoints.

Audit 630609_[0-3] completed 0:0 (2:24–3:41). Independent QA 630623 stopped
before interpreting results because dataset features do not yet contain relp;
Protenix.forward generates it internally. Preserve the failed validator and
qa_work directory. Corrected immutable validator snapshot
code_pair_components_validation_v2_20260918 invokes the same generate_relp
function from chain/residue/entity/token/symmetry IDs; QA 630632 is running in
new qa_work_v2. No prediction or source snapshot was rerun or overwritten.

A single next architectural candidate is implemented separately in
src/fastglycan/models/triangle_pair_state_emulator.py, with protocol
docs/stage1b_triangle_pair_pilot_v1.md. It adds 16 directional shared-neighbor
channels to the first hidden preactivation while preserving seeded baseline
shared initialization, zero-output identity, all inputs/loss/splits/schedule.
Three CPU tests pass, including a perturbation invisible to row/column means
but visible to the triangle branch, branch gradients and chunk/reload checks.
It has not been tested on GPU or trained. Activate only after the component
audit's independent QA. Pair-specific relational information is a working
hypothesis; no learned improvement or speed gain is claimed.

## 2026-09-18 — Component audit accepted; prioritize relational information

Corrected independent QA 630632 completed 0:0 in 3:35. All 88 actual pair_z
caches exactly match independent frozen-conditioning reconstruction; all eight
learned pair predictions, compositions, c1/c4 atom replays, sources/hashes and
coordinate metrics pass. Local archive source/worker/88-coordinate hashes
also verify. No new optimization or held-out selection occurred.

Across eight training examples, target interaction energy has median fraction
0.77623. Learned component error ratios have medians global 0.12674, row
0.80493, column 0.73634, interaction 0.83871. Learned raw-state and actual
conditioned-pair MSE ratios average 0.76924/0.75837, yet pooled all-atom error is
4.82452 A versus c1 4.85514 A and c2 2.36998 A. Oracle interaction alone gives
0.46593 A, improving all eight; oracle full pair 0.30413 A; oracle additive
4.07125 A; learned-additive + oracle-interaction 0.54137 A, oracle-additive +
learned-interaction 4.26232 A. These are target-aware interventions, not usable
inference inputs or a learned quality gain. The existing 64-validation negative
result remains authoritative. Merely replacing raw MSE by conditioning MSE is
not established as a remedy: conditioning MSE already improves substantially.

Next test the single predeclared 16-channel outgoing triangle branch while
holding raw loss and all data/training/selection settings fixed. The pointwise
MLP lacks pair-specific shared-neighbor communication; this provides a testable
representation hypothesis, not proof that the new branch can learn the needed
interactions. CPU implementation tests pass and total parameters are 195,568;
actual longest BF16 GPU forward/backward check, pipeline integration, training
and full decoded evaluation remain pending. No architecture/loss grid or full
training is authorized by these diagnostic outcomes. Keep temporal test frozen,
record actual inference cost if quality passes, and continue toward the original
ESMC-600M MSA-free all-heavy-atom one-cycle/eventually one-structure-evaluation goal.

Report/plot/diagnostics: reports/stage1b_pair_components_2026-09-18.{md,png,json};
full local worker/validation/88-coordinate archive in its directory. HPC3 root
pair_component_audit_v1_20260918; immutable audit/QA snapshots recorded above.
All current jobs are complete. Do not resubmit finished audits.

## 2026-09-18 — Integrate the predeclared triangle comparison

The prior turn completed accepted component evidence, so this is a progress
continuation. HPC3 queue rechecked empty and accepted artifacts present. Wire
the independent 16-channel triangle class through an explicit config factory
into the existing trainer, decoder and independent validator; preserve all old
immutable snapshots. Eleven focused model/factory/loss tests pass. The new
training path requires longest-input BF16 forward/backward, finite nonzero
triangle gradients, exact identity/reload and chunk checks before optimization.
It also verifies the actual shared initialization hash and all predeclared
non-architecture training/data fields against the accepted pointwise baseline,
binding the accepted component audit and baseline report hashes. The independent
validator repeats those lineage checks. No new architecture or loss settings
are introduced beyond the already predeclared branch.

Submitted training 630661, afterok decoder array 630663_[0-3] and afterok final
QA 630664 on HPC3. Immutable code_triangle_pair_v1_20260918 includes all three
entrypoints; new outputs triangle_pair_emulator_128x64_v1 and
triangle_pair_decoded_64_v1 remain separate from every accepted baseline.

## 2026-09-18 — Triangle comparison accepted as another negative structural result

HPC3 630661 completed 0:0 (2:57), decoder 630663_[0-3] completed 0:0
(2:19–2:52), and independent QA 630664 completed 0:0 (0:42). Eleven focused
tests pass. Longest 951-residue BF16 GPU identity/forward/backward has finite
nonzero triangle-branch gradients, exact reload/chunk checks and peak allocation
2,005,014,016 bytes (1.867 GiB). Actual shared initial weights hash matches
baseline 8154fc92ad855da8d533339c380f93afadc278d6dedd5ed55df06e26a43b4586;
all predeclared non-architecture fields match. Independent QA repeats lineage,
full state metrics and all 64 learned pair/c1-atom replays exactly. Local archive
checkpoint/history/worker/source/128-coordinate hashes also verify.

Best epoch is 20, validation macro/pooled state-MSE ratios 0.791984322/0.776587014,
only slightly better than pointwise 0.795290582/0.780328721. Pooled all-atom
error 2.957158 A versus c1 2.904474, c2 1.934670 and pointwise 2.945227 A;
CA-distance error 2.086126 A versus 2.036336/1.441237/2.081999 A. Ratios to c1
1.018139/1.024451 and to pointwise 1.004051/1.001982 establish no structural
gain. All-atom/CA-distance harm affects 44/64 and 39/64 groups relative to c1.
Do not extend these raw-MSE configurations, expand a small architecture grid,
promote either checkpoint or launch full-data training. This does not prove
all relational models incapable; it rejects this predeclared candidate/schedule.

Predeclare docs/stage1b_decoder_gradient_audit_v1.md as the next bounded action:
check whether actual denoised-coordinate responses provide a verified gradient
to c1 pair states through the frozen decoder. Four fixed training groups,
shortest and longest plus two stratified seed-107 groups; no validation use.
Keep common noisy input/c1 singles, use c4 pair only for supervised diagnostic
responses, rebuild pair_z and p_lm/c_l with gradients, freeze teacher parameters,
and require replay/finite-gradient/finite-difference/longest-memory checks before
any new training protocol. Source inspection confirms callable DiffusionModule
forward (inplace_safe=False) and a no-grad runner wrapper. Recorded accepted
runtime disables sampling autocast and produces FP32 pair_z. The first denoised
response is not the final sampler output, which undergoes an Euler update;
record actual noise/coefficient/NFE values rather than assuming defaults. No
one-evaluation folding or learned quality claim follows from a gradient audit.

Report/curves/diagnostics: reports/stage1b_triangle_pair_2026-09-18.{md,png,json},
with full training/checkpoint/decoded/QA archive in its directory. All current
jobs complete; next gradient audit has not been implemented or submitted. Keep
the primary ESMC-600M/all-heavy-atom/one-structure-evaluation target, experimental
GT requirement and formal held-out gate intact.
