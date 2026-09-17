# Stage 1B coordinate-refiner 32-target overfit gate

Date: 2026-09-17

The first coordinate-refiner training path passed its deliberately small
overfit gate on hpc3. This gate tests data alignment, optimization, masks, and
model capacity; it is not a held-out quality result.

The input consists of the 32 shortest records in the frozen training split
(length 21--39; 1,069 valid residues). Each example joins the existing frozen
ESMC-600M final-layer BF16 slice to the accepted c2/c4 teacher pair. The c4
C-alpha coordinates are rigidly Kabsch-aligned into the c2 C-alpha frame before
forming the residual target. Padding and invalid residues remain masked.

Slurm job `629419` ran on one H100 80GB in `emergency_acd` and completed with
exit code zero in 1:23, including data loading. The 400-epoch optimization took
48.49 seconds. The best checkpoint occurred at epoch 255:

- aggregate c2 baseline C-alpha RMSD: 1.2432 A;
- best training C-alpha RMSD: 0.1712 A;
- best-to-baseline RMSD ratio: 0.1377;
- final-to-initial coordinate-MSE ratio: 0.000612.

Both predeclared gates passed: coordinate MSE was at most 10% of the randomly
initialized value, and C-alpha RMSD was at most 50% of the uncorrected c2
baseline. The checkpoint SHA256 is
`ebd9f2c92713ce12ece69734d72c4537f1c4c112e88475a2afd7dbaccda2e814`.

This result proves that the frozen ESMC/teacher join and local-frame refiner can
fit a small training set. It does not show validation generalization, all-atom
improvement, or thermodynamic truth. The next gate is a fixed train/validation
experiment on hpc3 with checkpoint selection restricted to the 1,600-group
validation split.
