# Native diffusion learning pilot: source contract v1

2026-09-30, after7c6979e8, BEFORE source screening or any new prediction.
Prepare128TRAIN +32VALIDATION, each split balanced across50–255 and256–1024
residues. This is a bounded first learning trial, not the final training corpus.
No model/teacher/repair scores or connection residuals are used in selection.
No inference, teacher generation or training is authorized by this data script.

Use the full existing256-shard PDB catalog and structure-based construct sequence,
not UniProt full-length substitutions. Require X-ray resolution<=2.5Å, one model,
release<=2021-09-30, canonical50–1024 sequence, author-supported monomer or
homooligomer assembly, no nucleic-acid/other-polymer component, known SIFTS accession.
Ligands/ions/assembly context remain recorded; extraction does not imply they are
irrelevant. Within an assembly prefer the lexically first chain with all residues
observed, before coordinate/geometry measurements. Across records choose best
resolution then PDB/chain/assembly, once per full-sequence SHA256 group.

Both roles conservatively exclude the historical21k reference sequences, PDBs and
accessions, reserved32, local-fit development sources, all64geometry-calibration
sources, fresh8 and1U07. Add recent sources to the existing hashed reference pool.
Reuse the calibrated BLAST2.17.0 settings/effective-dbsize/HSP exclusion rule:
near identity>=.30 with>=50 aligned residues and>=.70 shorter coverage atE<=.001,
OR domain HSP>=50 aligned residues atE<=1e-5. This is an operational isolation
definition, not proof of unrelated folds or absence from Mini/ESM pretraining.

Rank by SHA256('diffusion-sources-v1:20260930:'+group_id), cap2048 source candidates
per length stratum. Search all candidates against references and each other, with
full target limits, recorded tool/hash/commands/stderr; stderr requires audit.
Exclude qualifying HSPs to references; greedy selection also excludes PDB/accession
sharing and qualifying HSPs between ANY selected rows, including within TRAIN.
This conservative pilot does not claim to represent the full PDB distribution.

Rebuild experimental GT twice identically from mmCIF. Require complete observed
N/CA/C/O, finite coordinates, no backbone break or modified residue. Native chemistry
preflight rejects crosslinks/disulfides unsupported by the fixed graph;
additionally retain the earlier observed-SG pair distance<2.3Å
source exclusion to catch unannotated disulfides/SG overlaps. It also verifies
atom identities, reference replay and peptide graph. Require>=90% observed native
heavy atoms; preserve a boolean per-atom GT mask, zero placeholders are NEVER labels.
This intentionally differs from the earlier full-heavy-observation repair contract.
Training/evaluation code must apply the mask before all GT arithmetic. Prediction
geometry is evaluated on the entire native inventory, including unobserved GT atoms.
No selecting by experimental geometry scores, peptide windows or teacher quality.

Visit candidates in the prelocked order, materialize bounded batches of32 using8
single-thread CPU chemistry workers. Once qualified/pair-isolated, every fifth
selection within each stratum goes to VALIDATION (positions0,5,...); the other four
go to TRAIN. Stop at80/stratum:64train+16val each. Discard no range-valid runtime
failure silently; record all source-preflight rejections. If the fixed pool cannot
fill a quota, report the shortage; do not relax chemistry/isolation or launch a
partial learning experiment. Selection freezes identities/roles/masks/hashes before
model outputs. VALIDATION must never enter gradients or teacher-label training.

Read-only independent source/sequence/mask audit is required before cache generation.
No claim of training improvement follows from successful data preparation. The
learning objective, teacher usage, budget and validation endpoints require a
separate lock. No posthoc noninferiority margins or reuse of old32 outcomes.
