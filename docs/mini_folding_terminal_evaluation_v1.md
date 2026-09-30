# Fixed terminal folding evaluation — 2026-09-30

This implements the already frozen folding-scale cycle. Primary comparison:
expanded TRAIN423 versus TRAIN128 at exactly 2048 new updates, on the new32
validation proteins. Both start at the retained native full-diffusion512 checkpoint,
reset optimizer and receive8192 new exposures. The data histories differ; this is
not an isolated causal estimate of training-set size or a from-scratch comparison.

Evaluate public C4/S1, public C4/S2, retained512, TRAIN128 terminal and expanded423
terminal on all455 proteins and both assigned noises. Original128 and added295
training cohorts stay separate; new32 validation stay separate from both. Old64
validation are not reread. TRAIN noises600001/600011, validation810013/810029.
No checkpoint/seed selection, new optimization, geometry repair or extra epochs.
All three learned models are C4/S1/K1, frozen ESM2/Pairformer and FP32 native
diffusion. ESMC remains a later matched interface experiment.

Training audit must complete before evaluation lock creation. Bind terminal and
retained checkpoints, originating training-lock hashes, full selected288 parameter
names, cache/source/GT/public-weight hashes, private runtime code and calibration.
Only terminal2048/8192 continuation payloads with the retained parent hash load.
Use the shortest original TRAIN protein for public parity and checkpoint reload
checks; never use validation for engineering selection. Check excluded parameters
unchanged and model state keys restored. Run eight deterministic length-squared
balanced shards on H10080GB; first shard releases the remaining seven after success.
Errors remain failures with the full planned denominator; do not silently resubmit
into, overwrite, filter or finish a partially evaluated frozen run.

4550 total coordinate outputs. Reuse1692 already audited TRAIN public S1/S2
predictions;2730 learned predictions plus192 validation public diffusion calls
give2922 new prediction NFEs. Eight workers additionally use10 probe NFEs each:
3002 new NFEs total. These evaluations reuse cached C4 conditioning and therefore
do not measure live ESM/Pairformer latency. Record actual timing and memory with
this scope; do not label diffusion-only timing as end-to-end folding speed.

Score observed experimental GT with the unchanged AA/Cα-lDDT definition and masks,
and independently recompute distances to check both scores. Synthetic S2 references
are training auxiliaries, not GT. Preserve all coordinates, per-noise/per-protein
scores, strict checked stereocentres, severe pairs and worst penetrations, typed
connections and GT Cα RMSD. Legacy ideal-window joint pass is not
the sole veto, and zero severe pairs is not full chemical correctness.

Average the two noises within each protein before primary means, paired P01/P05,
worst5% mean, delta<-0.05 counts and10000 protein-resample bootstrap intervals
(seed20260930). Report paired per-noise values as well; no best-of-two. Compare
expanded−TRAIN128, both terminals−retained/S1/S2, retained−S1 and S2−S1. Geometry
counts include both-noise per-protein success and newly damaged originally clean
instances. Retain length and assembly metadata for descriptive strata; do not use
strata to select a model or claim independence from pretraining.

Scheduler COMPLETED0:0, worker reports, exact assignment coverage, hash checks,
and expected NFE counts must agree before aggregate results are complete. Offline
cohort aggregation rejects missing, duplicate or unexpected records. Summaries
cannot certify deployment, complete sequence gradients, design utility or binding.
Complete this bounded comparison, then decide the next experiment from quality,
paired tails, chemical failures and cost together.
