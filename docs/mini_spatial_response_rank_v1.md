# Per-mutant spatial response rank v1 — locked before decoding

This is a distinct, bounded diagnostic of residue-axis Delta z compression, following the CLOSED AA-axis linear compression studies. No new hard C4/ESM, JVP, fitting or training. Reuse all 10 TRAIN parents / 50 sites / 950 non-WT endpoints and 10 WT, seeds 225001/225011. These remain development/stress data, not new independent validation. Preserve 6UFE-92.

## Representations and intervention

For EACH mutant independently, D[j,k,c] = z_target - z_WT in FP64, without centering across AA or spatial positions, and without symmetrizing directed pair state.

* `channel`: separate L-by-L matrix SVD per channel; optimal Frobenius rank-R matrix approximation per channel. Store two [C,L,R] factors, absorbing singular values: 2LRC scalars.
* `shared`: HOSVD left/right bases from sum_c D_c D_c^T and sum_c D_c^T D_c; core[R,R,C] = U^T D V. Reconstruct U core V^T. Storage 2LR + R²C. This is a specific shared-spatial Tucker projection, not globally optimized Tucker fitting and not the proposed learned channel projection / CP parameterization.

R = 0,4,8,16,32,64,full L. No adaptive rank selection or result-dependent expansion. Full L must actually reconstruct/decode, not substitute exact output. SVD/HOSVD use target endpoints: oracle representation ceilings, not WT-only prediction or measured speedup. The per-channel Frobenius optimum is NOT a functional upper bound for arbitrary learned low-rank matrices.

Decode with exact target s, WT s_inputs, rebuilt native TARGET atom graph/chemistry and identity noise; replace ENTIRE z by z_WT + D_hat. R0 = WT z, distinct from previous AA-PCA K0 mean-mutant z. No exact global pair complement. s is deliberately exact: this isolates pair spatial compression, not the complete student task.

Two freshly replayed references: Exact = target s_inputs/s/z; Baseline = WT s_inputs + target s/z. Compare to both, since WT-input substitution has known small nonzero effects. WT archived coordinates have noise axis only; mutant prior arrays have arm and noise axes.

## Preflight and execution

Before panel decoding, check longest existing endpoint L221 FP64 factorization/full reconstruction and runtime. Four focused unit tests check full rank, asymmetric known rank, independent per-channel SVD/energy, zero response/validation/storage. No preflight functional results select R or variants.

Eight existing GPU assignments, 32 unchanged CPU scoring assignments; hard chemical rebuild and input/weight/source hashes audited. Forbid Pairformer calls by runtime hook. Expected 960 chemical rebuilds, 950 decompositions, 28,520 actual single-sample S1 denoiser calls; reuse identical R0 across variants (1,900 calls avoided). No new C4. Both full-rank paths checked against uncompressed Baseline using inherited input max 1e-5 / coordinate max 1e-3 tolerances. Nonfinite/error/timeout remains failure. GPU and CPU phase limits 7200 seconds each, no candidate/rank expansion.

## Outcomes and independent audit

Same frozen task and metrics as prior global response rank: parent experimental CA distance Huber proxy, not experimental mutant structures or binding. Report 19-AA Spearman, Top1/regret/recalls, full distributions and paired protein-bootstrap intervals (10 parents, 50 sites, 100 site/noise rankings, 1900 mutant/noise outputs per arm). Also AA/CA lDDT to references, mutation-neighborhood CA RMSD in global alignment, >1A tails and worst case, severe clashes/strict checked chirality and new failure transitions. Do not call operational geometry checks complete chemistry.

Report energy per mutant and channel, factor scalar counts, reconstruction/decomposition timings and allocation. No cross-AA low-rank interpretation. Head factor-generation/storage can be smaller, but dense z materialization and native S1 memory/compute remain; target s is still supplied. Current oracle SVD timings are not student inference performance.

For independent CPU verification, archive R8/R16/full projected z for lexicographically first non-WT AA at all 50 sites. Recompute with independent NumPy decompositions from immutable endpoints; verify full/energy/projection values. Recompute saved-coordinate score/ranking evidence without GPU. Preserve all failures and stop after this batch. No automatic training, architecture promotion, deployment or reversal of AA-linear stop decision.
