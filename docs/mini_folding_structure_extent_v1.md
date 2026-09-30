# Frozen-output C4/S1 local/global extent diagnostic v1

This is posthoc development analysis of completed coordinate-weight ablation
outputs, not a new quality gate or independent test. Analyze ALL455 proteins,
all five locked models and both assigned noises (4550 existing coordinates).
No new prediction, training, repair, source admission or checkpoint selection.
Original TRAIN128, added TRAIN295 and observed DEV32 remain separate.

Question: when coordinate weight0 improves local lDDT but worsens aligned CA RMSD,
is the extra error concentrated in a few residues, or does it persist across a
larger part of the structure? Existing results alone do not establish topology
changes or a faulty backward implementation.

Use the same observed CA identities and experimental GT as the terminal score.
Verify input mapping/GT and prediction hashes; rederive the CA coordinates from
atom37 GT and compare them exactly with the native mapping. Independently recompute
FP64 proper Kabsch RMSD and require agreement with archived scores within1e-8 Å.
No reflection, new atom matching or symmetry reassignment.

For every output, report all aligned per-residue residuals, median/P90/max,
fraction exceeding2/5 Å, and fraction of total squared error in the worst ceil(5%N)
residues. Also report RMSD of the remaining residues USING THE ORIGINAL alignment;
this exclusion is descriptive and does not revise model scores. At numerically
zero total error (SSE<=1e-20), tail fraction is null rather than an artificial pass.

Independently align consecutive nonoverlapping32-CA fragments from the first
observed residue, with a final fragment of at least3 residues. Skip fragments
crossing missing residue IDs and report coverage. Pool fragment squared errors
weighted by residues. This is a measure of local shape error, not a reconstructed
or repaired output and not a claim that the fragments are biological domains.

Compute CA pair-distance error over all unique pairs and separately for sequence
separation>=24, grouped by EXPERIMENTAL GT distance<15 Å,15–30 Å,>=30 Å. Report
pair count, MAE, RMS error and signed mean for each band. Empty bands remain null;
report valid protein counts rather than replacing them with zero. Include GT and
predicted radius of gyration. Do not infer better structure from a size ratio alone.

Aggregate each protein's two noises before cohort summaries. Candidate/control
per-residue positive squared-error increases also get a top5% concentration
summary. These extra diagnostics are exploratory; their bootstrap intervals are
conditional on fixed noises, with no multiplicity/generalization claim. They do
not overwrite original lDDT, chemistry, RMSD or promotion decisions.

One CPU-only8-worker Slurm job on HPC3 acd_u, GPU hidden (the partition may still
reserve one),20-minute cap. Preserve failures in output and stop on incomplete
records; do not silently drop any protein. Bind new code/protocol and old lock,
scored-instance export and worker reports before execution. Save per-protein
results and cohort summaries; no changes to frozen evaluation directories.
