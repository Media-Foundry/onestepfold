# Independent experimental backbone calibration v1

2026-09-30. Read-only follow-up to 3b10f921. The goal is to estimate experimental
connection variability independently of the seven repair-development proteins.
No solver, inference, coordinate changes, new acceptance rules or model training.
The existing independent32 results and rejection remain unchanged.

Source: DiamondHill structure pack `scratch_structure_data_v1_20260927`, TRAIN
only, canonical sequence length50–1024, X-ray resolution≤2 Å. Require one matching
chain, complete observed N/CA/C/O, contiguous label residue IDs, no modified
residues or annotated chain break, verified prepared-file hashes. Do not screen
on measured connection residuals, clashes, chirality, or old repair success.
Missing side chains and disulfides do not exclude a backbone calibration source;
this is not a declaration of full chemical support for the repair representation.
Keep assembly context. Backbone-complete and chain-break screening conditions
the population and may truncate extreme connection failures; report this limit.

Exclude all21070 historical reference sequences and their recorded PDB/accession
exclusions, the reserved32, and all eight recent local-fit sources by sequence,
PDB and accession. Reuse calibrated BLAST2.17.0 search: BLOSUM62, word3, gaps11/1,
SEG yes, composition2, E≤.001, aligned residue pairs≥50 and either identity≥.30
with shorter coverage≥.70 or E≤1e-5. Retain HSPs and fixed original reference
residue database size; record actual augmented database size separately. Screen
both candidate→reference and candidate→candidate. Reject search warnings pending
audit. This is development isolation, not exclusion from Mini/ESM pretraining.

Before measuring residuals, rank by SHA256 of
`connection-calibration-v1:20260930:` plus group ID. Form at most512 eligible
sources in each resolution stratum (≤1.5 Å, >1.5–2 Å). Greedily select32 per
stratum after isolation, enforcing unique PDB/accession and pairwise HSP exclusion
across the entire panel. No relaxation if fewer available: report the shortage.
Within each stratum alternate selected rows into calibration and held-out roles,
giving32+32 overall if sufficient. Lock source identities, roles, sequence
searches, protocol and code hashes before reading connection residuals.

Reconstruct observed backbone by identity from the original mmCIF (recorded
chain, label residue, atom name, altloc); verify one proper rigid transform against
the packaged GT. Retain occupancy, B-factor and selected-altloc information; the
primary measurements use all selected observed backbone atoms. Low occupancy or
alternate conformation sensitivity is descriptive, not grounds to replace a
selected source. Mapping/measurement failures remain in the selected denominator.

Measure the five frozen residual definitions with the independent NumPy route;
check plane phase against Gemmi. Use nearest cis/trans solely to DESCRIBE GT.
Record cis/trans and following-Pro/other separately, including absolute phase
deviation and bond lengths/angles. This does not infer a prediction-time branch.

Fit empirical absolute-residual q95 and q99 on CALIBRATION only, with NumPy linear
quantiles. Primary common-trans values are separate for following-Pro and other;
require≥100 edges from≥8 proteins per class or mark the estimate unsupported.
Report equal-protein weighted empirical distributions as a sensitivity to pooled
edge weighting. Cis observations remain descriptive; no rare-cis threshold fit.
On held-out sources report coverage of each locked q95/q99 interval, per protein
and pooled, with protein-resampling95% CIs (2000 draws, seed9302026). Do not alter
quantiles or selection after held-out results. Also retain original objective
activity and old gate outcomes for both roles. Neither an empirical quantile nor
coverage constitutes a validated chemical accept/reject threshold.

Stop after this corpus audit. A future objective intervention requires a new
protocol and direct quality/geometry comparison; do not mechanically turn these
quantiles into gates or fit cis/trans labels from GT at deployment.
