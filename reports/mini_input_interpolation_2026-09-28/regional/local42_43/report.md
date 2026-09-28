# Hard-neighborhood input-source interpolation

Existing development targets: 8bzn; region: local42_43. Fixed native chemical graph, noise211, C4/S1, FP32, no dropout/augmentation. No training, objective changes, smoothing, threshold changes or sequence optimization. HHH is constant in alpha and is exactly replayed across the source workers. R means restype/profile only; C means the five current reference fields; E means ESM2 recomputed for the probabilities.

## Alpha scan

Rows are probability interpolation, not logits saturation. Legacy softmax replay is separate. Geometry columns use all predicted atoms and the frozen graph-distance≤3 exclusion. Hard starts may themselves fail chemistry: small displacement is not a chemistry-validity gate.

| Case | Sources | α | Tracked distance Å | Min nonbond Å | Severe pairs <1 Å | AA RMSD vs hard Å | CA RMSD Å | Bond RMSE Å |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 8bzn | E | 0 | 6.26658 | 0.57936 | 8 | 0.00000 | 0.00000 | 0.28777 |
| 8bzn | E | 0.2 | 6.28704 | 0.38849 | 7 | 0.09841 | 0.09179 | 0.28935 |
| 8bzn | E | 0.2581587 | 6.29509 | 0.38530 | 7 | 0.13287 | 0.12386 | 0.28981 |
| 8bzn | R | 0 | 6.26658 | 0.57936 | 8 | 0.00000 | 0.00000 | 0.28777 |
| 8bzn | R | 0.2 | 6.31494 | 0.55912 | 8 | 0.03125 | 0.02814 | 0.28832 |
| 8bzn | R | 0.2581587 | 6.32842 | 0.55652 | 8 | 0.03964 | 0.03564 | 0.28844 |
| 8bzn | C | 0 | 6.26658 | 0.57936 | 8 | 0.00000 | 0.00000 | 0.28777 |
| 8bzn | C | 0.2 | 5.29852 | 0.50891 | 8 | 0.08521 | 0.05728 | 0.29390 |
| 8bzn | C | 0.2581587 | 5.04741 | 0.46592 | 8 | 0.10790 | 0.07297 | 0.29391 |
| 8bzn | ERC | 0 | 6.26658 | 0.57936 | 8 | 0.00000 | 0.00000 | 0.28777 |
| 8bzn | ERC | 0.2 | 5.37701 | 0.46485 | 9 | 0.17108 | 0.14914 | 0.29586 |
| 8bzn | ERC | 0.2581587 | 5.15293 | 0.38800 | 11 | 0.22444 | 0.19640 | 0.29635 |

## Endpoint and dependency checks

All alpha0 coordinates are bitwise identical across source arms for each target. Unselected input fields have zero deltas. Native sequence/atom/residue/chain identities remain unchanged. Every forward actually calls both input and diffusion atom-reference cache builders, with equality checks on all five reference fields and fresh d_lm/v_lm. Full Pairformer conditioning and diffusion caches are recomputed. ESM reuse is restricted to the same hashed prepared probability input; no stale input-dependent conditioning is reused.

Detailed input/conditioning deltas, reference intraresidue bond contraction and mask ranges are in the per-arm JSON. Per-residue reference-bank contributions and unaligned/aligned backbone comparisons are in prepare_*/reference_audit.json. These observations do not introduce a new soft-chemistry representation.
