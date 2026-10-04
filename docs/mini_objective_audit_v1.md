# Score-objective audit v1 — 2026-10-05

Read-only follow-up to completed context_replication_v1. No training, data removal,
new C4/ESM/S1, model selection or new loss run. Historical results remain frozen.

All 12 runs/all saved TRAIN snapshots: decompose 19 non-WT old-noise mean labels
and predictions into candidate mean and centered components in raw task units.
Report raw, mean and centered label energy; total, mean and centered residual MSE;
old/new/four-noise candidate rank correlations. Include every site. Zero-variance
ranking is undefined and counted explicitly, not silently replaced with success.
For all 160 sites, compare old and new centered scores, rank and old-select/new-eval
regret. Two noises per group are a diagnostic, not a noise ceiling estimate.

Gradient probes fixed before inspecting gradients: n32, both architectures, both
seeds, initialization / 32768 / terminal131072, all128TRAINsites =1536probes.
Use original globally scaled MSE and exact checkpoint, no optimizer updates.
Same full parameter set within each architecture at every site; report full norm,
readout score-module norm, mean-loss and centered-loss gradients and their inner
product. Gradients are before clipping; simulated clip1 reports norm and scale
only, not an AdamW update. Gradient magnitudes are not cumulative influence.
Verify checkpoint hashes, TRAIN prediction replay, and parameters unchanged.

The three previously disclosed energy-heavy sites are tracked as a fixed set;
report their shares in each decomposition without redefining the set by outcome.
No threshold, normalization floor or loss intervention is selected from held data.
Only if audit motivates a new loss comparison will it receive a separate protocol.
