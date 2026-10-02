# Conditional local functional-rank diagnostic v1

Locked before new decoding, 2026-10-02. No training, weight changes, soft inputs,
Jacobian probes, new sites, candidate selection, or deployment promotion.

## Scope and reuse limit

Reuse the 50 sites in the ten TRAIN parents frozen by hard_response_rank_v1.
The previous run stored only `s[i]`, `z[i,:]`, `z[:,i]`, and `s_inputs[i]`.
It did NOT store complete decoder conditioning. Recompute 960 unique native hard
C4 endpoints, verify all archived slices and atom/topology identities exactly,
and retain full conditioning remotely for subsequent audit. This recomputation
is counted, not hidden as cache reuse. These are development proteins, isolated
by accession only, not a homology-independent test set.

For each target AA, all native chemistry, atom inventory, `s_inputs`, other `s`
tokens, and the complement of the two `z` strips remain EXACT HARD-TARGET values.
Only the three archived response blocks are replaced. Thus the experiment asks
whether the local tail matters conditional on exact global target information.
It cannot certify compression of the entire hard mutation response or speedup.
The basis itself uses all 19 hard-mutant endpoints: this is oracle, in-sample
compression, not a predicted basis or held-out-AA interpolation experiment.

## Intervention

- Public Mini-ESM v0.5.0 + ESM2-3B, frozen FP32 native full C4, eval, no MC dropout.
- Original AA order `ACDEFGHIKLMNPQRSTVWY`; 19 non-WT deltas promoted to FP64
  before subtraction; mean over these 19, NOT the WT-inclusive set.
- Original unscaled concatenation metric, including duplicated `z[i,i]`.
- Centered Gram eigendecomposition, equivalent to feature-space SVD; reconstruct
  mean plus rank K centered response, add WT, cast once to FP32.
- K = 1,2,3,5,8,10,12,15. Diagnostic controls K=0 (mutant mean) and K=18
  (complete centered response). WT is kept exact at every K.
- Two reconstructed diagonal copies must agree within atol=rtol=1e-6;
  use their average at the shared slot. All other tensors retain native values.
- Reference, sham and intervention use identical packed contiguous layout.
  Exact slice reinsertion must give bitwise-identical coordinates (noise 225001)
  for every non-WT endpoint. K18 input max error <=1e-5, coordinate max error
  <=1e-3 Angstrom; these are engineering controls, not a quality acceptance gate.
- Same controlled stable-Euler S1 with native inference schedule; no added churn,
  rigid augmentation or dropout. Seeds 225001 / 225011; identity-bound initial
  atom noise, shared within each exact/intervention pair and across shared atom
  identities. Recompute reference-dependent decoder caches for EVERY intervention.
- 960 C4 /3840 recycle calls; 21,870 denoiser calls including 950 shams;
  20,920 saved unique predictions (WT once per parent/noise, reused across sites
  and ranks). No fair end-to-end speed claim from this experiment.

## Structure, chemistry and ranking

Primary reference = exact hard-mutant model output under the same noise, NOT
experimental mutant truth. Report CA/all-atom inter-residue lDDT (15A neighborhood,
per-atom mean, thresholds .5/1/2/4A), global CA Kabsch RMSD, local CA RMSD in that
SAME global frame, nonlocal CA distance RMSE, 8A contact disagreement/Jaccard,
and distance-bin disagreement (2,4,...,20A edges, sequence separation >=3).
The fixed local region is parent observed GT CA within 8A of the site plus
sequence +/-2; if site GT is missing use sequence +/-2 only.

Geometry uses full native heavy inventory, graph distance <=3 exclusions,
nonbonded distance <1A severe counts, maximum penetration and ALL checked CA,
ILE and THR stereocentres. Report exact baseline, new failures and counts;
zero severe plus checked chirality is not complete chemical validity.

Rank the pre-existing parent-backbone task: mean delta=1A Huber error for ALL
observed parent experimental CA pairs separated by >=3 sequence positions.
This is a structure-preservation proxy, not mutant ground-truth quality or
binding efficacy. Lower is better. No compactness objective or post-hoc sign flip.
For each site and each noise, report Spearman (average ties), top1 regret in the
EXACT objective, top1 agreement and top3/top5 recall; stable AA order resolves
selection ties. Report exact task range, task MAE, normalized regret; a range
<=1e-8 is labeled low signal, not informative success. Constant-rank Spearman
is undefined and must remain missing. Give both 19 non-WT and 20-AA results.
No best noise, cherry-picked site or threshold-based promotion.

Aggregate sites/noises within protein, then across ten proteins. Bootstrap ten
proteins (seed225101,10000 resamples); instance/site counts are descriptive,
not independent protein replication. All outputs and failures retained. Keep
primary K5 alongside the full curve, rather than selecting a favorable K after
seeing results. No numerical threshold defines "95% ranking retained": report
actual agreement, regret and distributions separately.

## Storage and stopping

Archive code/protocol and weight/input hashes before launch. Retain full native
conditioning and all decoded coordinates outside Git on DiamondHill; copy compact
reports and local coordinate evidence, with hashes and paths. Eight GPU workers,
then eight CPU scoring workers. Maximum one hour for decoding and one hour for
scoring; interrupted or nonfinite instances remain failures, never silently
removed. Engineering corrections get a new run directory and retain failed logs.
After collection stop; assess this conditional local result before any global
state experiment, residual-Jacobian experiment, or response-head training.
