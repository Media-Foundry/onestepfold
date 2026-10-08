# Mini final-recycle LoRA: fixed-budget noise coverage control v1

Status: locked before training outcomes. User authorizes running the single/dual-noise comparison after the completed geometry audit. No change to model, rank, training parents, candidate exposures, loss weights, optimizer, or geometry thresholds. This is a new four-run batch, not an extension or selection of old runs.

## Question and boundaries

Does exposure to both archived sampling noises reduce the geometry/response deterioration of the adapted candidate recycle, compared with exposure only to230201? This tests a complete training-recipe intervention, not a proven causal diagnosis or a claim that noise diversity solves transfer.

Mini remains `protenix_mini_esm_v0.5.0`, rank16/alpha16 LoRA on32 single/pair transition output projections,655360 trainable parameters. Frozen original WT3 memory, candidate's archived native s_inputs and query-MSA features, one native adapted recycle, frozen S1 with actual candidate chemistry. No oracle target final s/z; no ESM/MSA preparation, new C4 teacher generation, RCSB, new architecture, decoder unfreezing or rank search. Candidate preparation remains outside the model-only boundary. Native MSA execution within the final recycle remains included.

## Paired arms and budget

- Single: only decoder noise230201 and its matching archived teacher coordinates.
- Dual: alternate230201/230211 by each particular candidate's exposure index; teacher and decoder noise indices always match.
- Both: seeds272001/272003, exactly8208 updates, globalbatch2, same27 TRAIN sites across15 parents,513 distinct mutants,32 exposures/mutant. Dual gets16 exposures/noise; single gets32 for230201.
- Both arms start from the same saved step0 parameters and empty optimizer state for each seed. Original trained checkpoints are not initialization. Four fresh all-DDP runs; original mixed serial/DDP run is historical only.
- Same AA/site schedule: site=step%27, visit=step//27, AA index=(2visit+rank)%19. Dual noise index=floor((2visit+rank)/19)%2. This prevents permanent AA-to-noise/rank confounding. Full schedule counts are tested and audited from actual logs.
- Original objective: aligned all-atom MSE +0.25 CA-distance MSE +0.01 clash +0.01 chirality. AdamW lr1e-4,wd1e-4,eps1e-8,clip1 after DDP gradient averaging. No additional S1 call per update, hence same candidate decode budget.
- Two ranks each handle one candidate. No learning-rate scaling. Device-pair/wave counterbalance: HIP0,2 runs single272001 then dual272003; HIP1,3 runs dual272001 then single272003. HIP4/5 evaluate immutable checkpoints. Only HIP_VISIBLE_DEVICES selects hardware.

## Integrity gates and recovery

Frozen code/protocol/source-lock/step0 hashes in noise_lock.json. Both seeds must pass new two-noise zero-state replay on fixedT37A and four discarded serial-versus-DDP mixed-noise update comparisons before ANY formal run. Both noise indices and an intra-update mixed-noise pair are covered. Gradient and parameter tolerance rtol1e-5/atol1e-7, actual errors retained. Prior full912candidate/two-noise zero replay is reused by SHA-verified step0 coordinates and matching initial weights, not relabeled as newly run.

Native source weights, reference caches, hook cleanup and paired final replica hashes remain checked. Atomic checkpoints every128 updates and fixed4104/8208. No automatic overwrite/restart of an existing history; interrupted attempts require explicit provenance-preserving recovery. Controller records jobs and fails on errors, without touching unrelated processes.

## Evaluation and interpretation

Full48site/912candidate/two-noise panels at0,4104,8208. Step0 is immutable audited reuse. Each new checkpoint evaluates all candidates, regardless of training loss; terminal8208 remains primary. Three roles remain separate: TRAIN27sites/15parents, same-parent new-site3sites, new-parent18sites/9parents. All are development data, not independent confirmation.

Evaluate same-noise ranking, average-noise ranking/Top1, old230201-select/new230211-evaluate raw regret, centered AA distance response, local structure tails, absolute geometry and pass-to-fail/fail-to-pass. Existing summary fields `old_spearman` and `new_spearman` denote230201/230211; **230211 is a TRAIN noise for dual**. Do not call its improvement unseen-noise generalization. No third/fourth evaluation noise is generated in this bounded comparison. New-parent evaluation remains held out of parameter updates, but reuses these noise identities.

Extra mandatory per-parent/per-noise geometry: number of severe pairs and wrong checked chirality centres across ALL outputs, including those already failing the disabled baseline. Do not rely on net pass count. Preserve continuous per-centre signed volumes and reference-oriented ratios in original score archive. Keep2ED6,2EBE,2FKZ and6ZRWP80; no exclusions or threshold changes. Failures at multiple candidates sharing one centre are not independent physical mechanisms.

Primary contrasts are dual minus single, paired by parent within each seed; disabled and Exact remain references. Same reporting includes typical/worst parent regret and the already-failed output population. A gain only on230211, a seed-specific gain, or better pass count with worse severe error counts is insufficient for promotion. No outcome-triggered hyperparameter sweep, early-checkpoint selection, training extension or automatic model promotion.

Post-evaluation native replay checks0/4104/8208, candidate order, disabled restoration and no-edit bypass. Existing model-only timing workload is retained, but scientific focus is quality, not new speed claims. Final report explicitly separates training-noise coverage from unseen-protein transfer and from untested unseen-noise robustness.
