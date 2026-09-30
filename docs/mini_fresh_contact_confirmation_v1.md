# Frozen raw-contact method: fresh source confirmation v1

2026-09-30. Preparation precedes any new model prediction or repair score.
The method is frozen at30301dd6. No training, weight/window/budget search,
failed warm start, further old-seven tuning, or reuse of reserved32 outcomes.

## Source and isolation

Select eight proteins in the existing SHA-ranked extension pool order, after
native chemistry and complete native-heavy-atom GT mapping checks. The source
pool is the previously materialized, backbone-complete remainder of
connection_calibration_extension_v1_20260930, not its64 measured proteins.
Reuse all historical BLAST/HSP exclusions and within-pool edges, and additionally
exclude identities, PDBs, accessions and qualifying HSPs to all64 calibration/
held-out sources. Original reserved32 and eight local-fit sources were already
included in the historical exclusion searches. Use their metadata only.
Enforce unique PDB/accession and pairwise sequence isolation among selected rows.
No ranking by GT connection residual, geometry, predicted quality or repair outcome.

The available remainder is24 proteins, length67–382, all homooligomer complete
single chains, X-ray resolution<=1.5Å. This intentionally bounded confirmation
does not establish long-chain, monomer or pretraining-data independence. Assembly
context remains explicit. Require supported native covalent graph (no disulfide/
other crosslink), full observed native heavy atoms, identity mapping, finite GT,
and native reference replay. Rebuild GT from mmCIF and compare to archived arrays.
All source/preflight exclusions are retained. If fewer than eight pass, report the
shortage; do not relax chemistry, substitute by outcomes or start a partial panel.
After locking selection, all inference/solver failures remain in the denominator.

## Comparison and interpretation, locked before predictions

Eight proteins x two fixed noises400009/400031. Native FP32 Mini-ESM v0.5.0,
ESM2-3B, C4/S1, K1; four complete recycles, MC dropout off, identity augmentation,
identity-bound initial noise, gamma0=0, lambda=1, eta=1. GT is evaluation-only.
For each raw input compare the whole-CCD-ideal ZERO-start calibrated connection
solver against exactly the same solver plus frozen raw-contact term. Both arms
are newly solved, same3x60 L-BFGS budget and final-iterate rule; no best checkpoint.
Use unchanged templates/calibration/code from the completed raw-contact trial.
Before execution bind all input/model/runtime/method hashes and audit zero starts.

Primary paired quality: protein-equal mean AA-lDDT and CA-lDDT, both against
experimental GT with the same native atom mapping and masks. Report raw, both
arms, per-protein/per-noise changes and worst cases, including remaining raw gap.
Confirmation of the small development gain requires both paired means positive,
no reduction of zero-severe+strict checked chirality+raw RMS budget count, all
planned outputs present and finite, and audit success. This is an engineering
confirmation screen, not a significance claim, chemical certification or deploy gate.
Any missing output means this screen is not established; never complete-case pass.

Geometry is separately reported: severe pair counts/rates, penetration distribution
and worst pairs, checked stereocentres, bond/peptide errors, every connection
residual and outlier fraction, cis/trans branch mismatches, raw displacement
distribution and largest atom/residue changes. Retain original thresholds and
`joint_pass` under the explicit label **legacy geometry joint check**. Its0/N
does not alone reject the method: both32-protein experimental calibration halves
were wholly rejected by its chainwise maxima. Do not replace it with fittedq99
or infer chemical validity from the weaker safety composite. No new chemistry
threshold is invented in this experiment. Real overlap/chirality failures remain.

Record per-arm wall time, closure/iteration count and peak memory. Fixed hardware,
threading and scheduling are required for timing comparisons; a new contact term
adds work even with equal iteration limits. Stop after the locked batch. Mixed or
negative confirmation closes this version for further consideration, not another
same-panel parameter sweep. Any positive result remains a detached iterative
output, not a one-step differentiable design oracle or hard-mutation utility.
