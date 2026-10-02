# R24 spatial extension v1 — user-requested bounded follow-up

The user explicitly authorized adding R24 after spatial v1 closed. Preserve v1 unchanged; R32 and R16 already exist and are reused as paired controls, not rerun or called new results. Same10parents/50sites/950mutants/two noises; channel-specific FP64 SVD of hard Delta z only. No new C4/ESM/AA compression/training in this extension.

New arms: Exact, Baseline, channel R24, actual reconstructed channel full-L sham. Exact target s remains available, WT s_inputs and native target chemistry/noise/layout are unchanged. R24 uses 2L24C scalars. Target-derived factors are oracle, not WT-predictable by construction.

Reuse v1 metrics, fixed genotype/parent-GT task and both references. Report R16/R24/R32 Spearman,Top1/regret,local tails,geometry transitions and factor counts, including failures. Predeclared descriptive comparison only: no new deployment threshold or automatic declaration of elbow. R32 prior rho0.990667,Top1 95/100,new geometry18 vs Baseline; increasing rank is not assumed to remove failures. Do not alter geometry rules.

8GPU/32CPU, inherited assignments and 7200-second phase bounds;0C4/0ESM/7620S1,960native rebuilds,950SVD. Full rank inherited max input1e-5/coords1e-3 guards. Independent CPU matrix-SVD audit at first nonWT of each site for R24/full; all saved references, sample independent lDDT and all ranking checked. Keep the original 50-site panel as development/stress evidence. Stop R extension after this point.

Student pilot is separate: factor generation from WT inputs only, oracle s at frozen decoder, no direct SVD-factor MSE (gauge ambiguity). Teacher/data split, training budget and losses must be locked before training; no claim that the current oracle panel constitutes independent generalization.
