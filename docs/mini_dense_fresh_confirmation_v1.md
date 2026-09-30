# Frozen dense diffusion: fresh32 confirmation v1

2026-09-30, after5a97fcec, BEFORE fresh candidate selection or model outputs.
One learned candidate only: diffusion_dense terminal512, checkpointSHA
7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829.
No parameter, recipe, sampler, checkpoint or evaluation-threshold tuning.

## Source selection

Select32 NEW proteins,16 each in50–255 and256–1024 residues. Reuse the frozen
4096-candidate source pool and its full-target BLAST/HSP searches from
diffusion_training_sources_v1_20260930. Preserve all original21,175-reference
identity/HSP exclusions, plus exclusions against ALL160 prior TRAIN/validation
identities, PDBs, accessions and qualifying pair HSPs. Require mutual isolation
among the new32 by exactly those rules. This is independence from the method's
development data, NOT proof of absence from Mini/ESM pretraining or unrelated folds.

Keep the original source contract: structure-derived construct sequence, canonical
50–1024, X-ray<=2.5Å, release<=2021-09-30, one model, author-supported monomer or
homooligomer, no other polymer/nucleic-acid component, known SIFTS accession,
complete finite observed N/CA/C/O and continuous backbone, no unsupported crosslink/
disulfide, observed SG proximity exclusion<2.3Å, >=90%native heavy atoms observed.
Missing GT atoms remain masked; prediction chemistry uses the full native inventory.
Retain assembly/ligand/context metadata. No ranking by model scores, peptide residuals
or observed chemical quality beyond the frozen input-support preflight.

Rank remaining candidates by SHA256('dense-confirmation-v1:20260930:'+group_id),
separately within each length stratum. Greedily visit in that order, rebuild GT twice
and native chemical input using the unchanged qualify_adapter_source. Use8 single-
thread CPU workers in batches16; record every source failure. Skip candidates with
known conflicts to prior160 before chemistry; new/new conflicts are checked during
greedy acceptance. Stop at16 per stratum. No inference before independent audit.
If the fixed pool cannot fill quotas, report the shortage, do not relax criteria or
run an unregistered reduced panel. Do not alter old source selection/manifests.

Lock identities, masks, source hashes and roles before inference. All new rows use
role=validation and confirmation_cohort=dense_v1; none can enter training. Reparse
all archived HSPs independently, verify hashes/full search settings, reconstruct
selection order, and audit GT observation/atom mappings before releasing predictions.

## Inference and evaluation

Use native Mini-ESM FP32, frozen ESM2/trunk,4 recycles, matched conditioning and
identity-bound noise. Seeds700021 and700027 are fixed now; no extra-noise selection.
Compare public S1, public S2 and the one frozen learned S1. All32×2×3=192 outputs,
with4 diffusionNFEs per target/noise (256 total), plus explicitly counted engineering
replays. Each target's C4 conditioning is computed once and shared; no GT-based
conditioning, coordinate repair or selection. No old validation32 predictions.

Primary: learnedS1−publicS1 AA-lDDT, first average two noises per protein, then32
protein means; report10000 protein-bootstrap interval with seed20260930. A positive
lower bound supports confirmation of AA improvement on this cohort; it is NOT a
chemical/design/deployment gate. Report CA-lDDT and paired P01/P05/worst5% tails,
severe quality regressions, publicS2 gap, all full-inventory geometry and calibrated
connection diagnostics, and introduced severe collisions/lost checked chirality.
Keep all failures in denominators. Do not introduce post-hoc noninferiority margins,
reinterpret old joint_pass, or hide worst individual cases in net improvements.

Use the existing scoring definitions with independent dense-distance AA/CA checks
and original experimental GT/masks. Report both counts per64 noise instances and
the number of proteins satisfying the finite geometry combination at both noises.
No best-of2, no treating64 noise instances as64 independent proteins. Report runtime
including conditioning separately from cached diffusion. Whole-batch failure does
not authorize target replacement after outputs. Complete and close this one cohort
before considering larger training, input-gradient utility or any other method change.
