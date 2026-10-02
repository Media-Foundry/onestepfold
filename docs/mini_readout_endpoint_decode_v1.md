# Readout endpoint S1 audit — locked before decoding

Audit the12 fixed8192-update checkpoints from e301abae's shared-readout experiment.
This is a NEW post-hoc endpoint audit. Original latent fit gates/results remain
unchanged. No new training, checkpoint selection, teacher collection, ESM or C4.

Same1W53 T37,19nonWT hard AA, two OLD noises230201/230211. Include ALL three
architectures(free_hidden,pair,channel), BOTH training targets(raw,R32 matrix), BOTH
initialization seeds231301/231303. The free-hidden table remains diagnostic only.

Each student uses WT s_inputs, exact target s, WT z+predicted Δz, and independently
rebuilt native target atom graph/reference chemistry. No prediction of Δs. References:
Exact(target inputs/s/z), Baseline(WT inputs,target s/z), WT-z, oracle spatial R32.
All references replayed and compared bitwise to previous closure packets.

Budget:456 student mutant/noise outputs +152 reference mutant/noise outputs +2 WT
=610 S1 calls. No C4/ESM forward; hooks reject C4. Sixteen arms,640 scored rows including
the shared WT output; these are NOT640 distinct network calls or independent proteins.

Checkpoint/source/teacher hashes fixed first. Recompute12 terminal raw and label
NMSE values using the loaded weights before decoding; do not change model weights.
The12 predictions are generated once each as19-AA batches and reused for both noises.

Report every checkpoint separately (38nonWT instances,2rankings per checkpoint):
-19-AA Spearman,Top1,regret,top3/5 recall against BOTH Exact and Baseline;
-CA/all-atom lDDT, global/local RMSD, pair/contact differences, P95/P99/max local
  deviation and >1Å instances; main compression reference is Baseline;
-geometry pass→fail and fail→pass identities, severe clash counts and checked
  chirality, together with absolute passes. Baseline9/38 does not imply valid design.
-association of raw latent NMSE with functional metrics across the12 fixed endpoints,
  descriptive only (one site, correlated seeds/noises, no inferential sample-size claim).

Do not hide a worse seed/noise or promote a model using one attractive metric.
No new functional acceptance threshold chosen after seeing results, no automatic
capacity search/multi-context training. Latent fit and decoded utility remain different
claims. The target function remains the fixed parent GT CA-distance proxy, not mutant
experimental response or binder efficacy. This panel is development-only.

Use one HIP-only worker on HIP0, verify PCI before model allocation. Frozen decoder,
same code path and feature packing. Publish all terminal records, coordinates/hashes,
reference replays and independent score audit; preserve failures in denominators.
