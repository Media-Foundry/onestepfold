# Factor-only student pilot v1 — freeze before parameter updates

User authorized NEW-protein pilot after the R24 extension. R16/R24/R32 show gradual tradeoffs, not zero geometry failures. Fix rank32 for the first learning test (R32 prior19AArho.990667,Top195/100,newgeometry18), to reduce representation capacity as a competing failure source. No rank/width/loss/update changes after validation scores. No AA-axis bottleneck. Old50sitesstayregression/stress and do not enter updates.

## Data and scope

Use selection.json from mini_factor_student_teachers_v1:24new response-task parents,16TRAIN+8validation,2sites each,all19nonWT. Operational BLAST near/domain+accession connected-component isolation across the entire candidate pool and oldpanel; one parent/component. Historical folding TRAIN source; not pretraining-unseen claim. Teacher full hard nativeESM2+C4/publicMini, two noises230201/230211, frozen hashes. Exact target s is supplied ONLY at decoder; predictor inputs exclusively WT s/z,mutation position,WTAA,candidateAA. No experimental mutant GT or binder task.

## Predictor and loss

Width128,2global node attention blocks,4heads,FFwidth512; WT s, mutation row/column of WT z, global WT pair row/column means, WT site single, relative-position bucket and discreteAAembedding difference. Full WT z supplies shared attention bias. Output U,V[candidate,L,128,32], each channel independent; expand sum_r(UV)/sqrt32. Shared generator does not require shared output spatial basis. WT query gated to exactlyzero. Vprojection startszero; Uprojection random, avoiding all-zero bilinear dead gradient. Two initialization seeds230301/230303; seed reset AFTER decoder setup. Same sampling schedule seed230401 for both.

Train only reconstructed Delta z (gauge-invariant), never SVD U/V labels. AdamW lr3e-4,weight_decay1e-4,globalgradclip1,FP32,1024updates/seed,one uniformly drawn TRAINparent/site/nonWT/noise perupdate. First256updates latent-only warmup. Remaining768updates:

L = normalized_Delta_z_MSE + .25 coordinate_MSE + .25 CA_distance_MSE + .01 clash_penalty + .1 chirality_penalty.

Latent normalization is each target response mean-square, floor1e-6, no validation fitted statistics. Decoder frozennativeS1,WT s_inputs,oracle target s,native targetchemistry,matched identitynoise. Coordinate target is uncompressed Baseline(WT s_inputs+target s/z), unaligned common-frame MSE;CA distance pairs sequencegap>=3. Clash/chirality match existing operational auxiliaries: graphdistance<=3excluded,meanpenetrationhinge1.5 plus top16tailhinge1.9/scale.1;checkedCA/ILE/THR normalizedsignedvolume margin.2. Teacher coordinates are not claimed chemically perfect. Geometry loss is a penalty, not a guarantee.

No ESM/C4/diffusion parameter updates. No checkpoint selection on validation, no early stopping/extra updates. Save final only plus full exposure/loss logs. Enforce training-only teacher access and audit parent roles. One native frozen-S1 joint-gradient preflight on first trainingparent, testing exact Baseline replay,finite losses/gradients,nonzero factor Vgradient,one reversible optimizer step. It cannot select a model or hyperparameters. Training bound3600s perseed;failuresretained.

## Evaluation locked before fitting

Evaluate both final seeds on ALL8validationparents/16sites and4hash-first TRAINparents/8sites (training fit probe). All19AA×2noises;WTshared. References: Exact, Baseline, WTz+oracle s, oraclechannelR32+oracle s, studentseed0+oracle s,studentseed1+oracle s. No oracle target z/basis enters predictor. Independently rebuild native chemistry/cache for decoder; exact replay guards. No quality-based case exclusion. Teacher and student sites share masks,task,coordinatespace and geometry scoring.

Report latent normalizederror relative to WTzbaseline and oracleR32,19/20AA Spearman/Top1/regret,local tails,geometrypass/recovery/newfailure,protein means (separate TRAINprobe/validation),seed variation. ParentexperimentalCAHubertask remains a model-response probe, not experimental mutation effect. Bootstrap proteins within each role;small8-parentvalidationuncertaintyandhistoricaldevelopmentlimits retained. Allseeds/noisesreport,notbest-of.

Time WT-only20AAfactor generation and denseexpansion separately, plusconditionalS1decoding; preserveone-queryversusbatchparity. Exacttarget s remains external, so no completeWT-onlyspeedupclaim. Densepairmaterializationcostincluded;factorstoragealoneisnotinferencecost. Small-pilotfailuredoesnotproveallnonlinearpropagatorsimpossible. Stop after final evaluation;no automaticDelta s predictor or largertraining.
