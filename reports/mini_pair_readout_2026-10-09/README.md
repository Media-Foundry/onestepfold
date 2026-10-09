# Frozen Mini pair readout diagnostic

Source: DiamondHill
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/pair_readout_v1b_20261009`.
Four fixed 8208-step checkpoints from the closed pair-recovery experiment;
two TRAIN-only shared linear fits per checkpoint. Original frozen features,
site scales, all 19 candidates, all pair rows and all channels are retained.
The centered head is latent-only. The full head and fixed mismatched residual
are decoded with actual candidate B_inputs/B_s, chemistry and archived noise.

`readout_lock.json` pins all code, original checkpoints, TRAIN weights, rank
tolerance and protocol. `runs/*/*/readouts.pt` stores both fitted matrices,
the original matrix, and the reduced augmented QR factors. `fit.json` records
the spectrum, effective rank, objectives and all contributing TRAIN sites.
`evaluation.json` records a second full-field objective calculation, latent
metrics and all coordinate hashes. Full coordinate NPZ files stay at source.
`scores.json.gz` retains every candidate/noise task, geometry and fidelity
record, including unchanged archived controls. No held labels enter fitting.

`manifest.json` contains source-file hashes. `verify_results.py` checks them,
independently solves the reduced systems, verifies site/length weights and
all-field row counts, checks second-pass objectives and frozen-state hashes,
and recomputes ranking, regret and geometric counts. Historical controls are
compared to the previous experiment. `analyze_results.py` creates equal-parent
summaries and descriptive paired intervals without any fitting or selection.

`failed_preflight` retains the initial snapshot and synthetic-test logs. The
remote PyTorch build lacks CPU LAPACK; no real feature extraction or fitting
had begun. SciPy LAPACK supplies the same FP64 QR/SVD in v1b. The first test
invocation also named a legacy test absent from that snapshot; the four new
solver tests were then run explicitly. All failures remain recorded.

These are new label-fitted diagnostics on development data, not zero-training
audits, independent confirmation, or a new folding speed benchmark. The
unchanged native candidate recycle is still required to generate B at use time.
