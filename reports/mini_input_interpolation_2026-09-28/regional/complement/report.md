# Hard-neighborhood input-source interpolation

Existing development targets: 8bzn; region: complement. Fixed native chemical graph, noise211, C4/S1, FP32, no dropout/augmentation. No training, objective changes, smoothing, threshold changes or sequence optimization. HHH is constant in alpha and is exactly replayed across the source workers. R means restype/profile only; C means the five current reference fields; E means ESM2 recomputed for the probabilities.

## Alpha scan

Rows are probability interpolation, not logits saturation. Legacy softmax replay is separate. Geometry columns use all predicted atoms and the frozen graph-distance≤3 exclusion. Hard starts may themselves fail chemistry: small displacement is not a chemistry-validity gate.

| Case | Sources | α | Tracked distance Å | Min nonbond Å | Severe pairs <1 Å | AA RMSD vs hard Å | CA RMSD Å | Bond RMSE Å |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 8bzn | E | 0 | 6.26658 | 0.57936 | 8 | 0.00000 | 0.00000 | 0.28777 |
| 8bzn | E | 0.2 | 7.14284 | 0.17897 | 212 | 12.89650 | 12.81974 | 0.39776 |
| 8bzn | E | 0.2581587 | 6.67192 | 0.13393 | 187 | 12.92353 | 12.80116 | 0.41592 |
| 8bzn | R | 0 | 6.26658 | 0.57936 | 8 | 0.00000 | 0.00000 | 0.28777 |
| 8bzn | R | 0.2 | 6.38467 | 0.38837 | 15 | 0.78893 | 0.68743 | 0.29093 |
| 8bzn | R | 0.2581587 | 6.38656 | 0.55382 | 13 | 0.99518 | 0.85867 | 0.29156 |
| 8bzn | C | 0 | 6.26658 | 0.57936 | 8 | 0.00000 | 0.00000 | 0.28777 |
| 8bzn | C | 0.2 | 6.37413 | 0.32454 | 11 | 0.57169 | 0.32140 | 0.42831 |
| 8bzn | C | 0.2581587 | 6.41678 | 0.50957 | 11 | 0.74217 | 0.43672 | 0.45048 |
| 8bzn | ERC | 0 | 6.26658 | 0.57936 | 8 | 0.00000 | 0.00000 | 0.28777 |
| 8bzn | ERC | 0.2 | 7.25154 | 0.18194 | 220 | 12.86295 | 12.82830 | 0.50556 |
| 8bzn | ERC | 0.2581587 | 3.62950 | 0.19772 | 218 | 13.64929 | 13.59988 | 0.52099 |

## Endpoint and dependency checks

All alpha0 coordinates are bitwise identical across source arms for each target. Unselected input fields have zero deltas. Native sequence/atom/residue/chain identities remain unchanged. Every forward actually calls both input and diffusion atom-reference cache builders, with equality checks on all five reference fields and fresh d_lm/v_lm. Full Pairformer conditioning and diffusion caches are recomputed. ESM reuse is restricted to the same hashed prepared probability input; no stale input-dependent conditioning is reused.

Detailed input/conditioning deltas, reference intraresidue bond contraction and mask ranges are in the per-arm JSON. Per-residue reference-bank contributions and unaligned/aligned backbone comparisons are in prepare_*/reference_audit.json. These observations do not introduce a new soft-chemistry representation.
