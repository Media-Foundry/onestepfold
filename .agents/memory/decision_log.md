# Decision log

## 2026-09-08: Adopt joint-distribution framing

Decision: frame the project as `Fast Joint Glycan Ensemble Models for
Conformational Design`, with one-step generation as an implementation axis.

Reason: GlyContact explicitly reports that its von Mises model does not learn
angle-angle dependencies, while GlycoShape preserves weighted MD conformers.
The scientific test is whether those dependencies change geometric-event and
edit-ranking decisions.

## 2026-09-08: Keep the first chemical graph fixed

Decision: fix residue count, linkage positions, branch topology, and anomeric
state; allow only an allow-listed set of monosaccharide substitutions.

Reason: changing linkage changes the atom graph and degrees of freedom. A
continuous soft sequence is an optimization relaxation, not a physical molecule,
so every final candidate must be evaluated as a discrete legal edit.

## 2026-09-08: Require weighted reference records

Decision: every conformer record carries population weight, simulation condition,
and effective sample-size metadata.

Reason: equal-weight cluster representatives can distort rare-event probabilities;
MD frames also have autocorrelation and cannot be counted as independent samples
without qualification.

## 2026-09-08: Use the GlycoShape ZIP as the import authority

Decision: import through `GET /api/download/<identifier>`, preserve the raw ZIP
and `data.json`, split `PDB/alpha.pdb` and `PDB/beta.pdb` into individual models,
and map `archetype.cluster_levels` weights only when the count exactly matches
the PDB model count.

Reason: the live API returns representative multi-model PDBs plus cluster
percentages, while cached GlyContact mirrors can have a different current cluster
count. The archive's metadata and models are therefore treated as an atomic pair.
The requested lookup ID may differ from the alpha/beta structure-specific
GlyTouCan IDs, so both identifiers are retained.

## 2026-09-13: Pivot to one-step protein monomer folding

Decision: make protein monomer folding the active project. Target
`protenix_mini_esm_v0.5.0`, MSA disabled, one Pairformer cycle, one structure NFE,
one sample. Preserve the glycan importer as a historical prototype rather than
delete it.

Reason: the new objective removes the need for mutation-pair data and gives a
clean Stage 0 quality/cost experiment. However, DCFold already publishes a
Protenix-derived all-atom one-recycle/one-step model, so the contribution cannot
be “one-step folding” alone. The proposed distinction is a training-efficient,
teacher-optional Clean-Structure MeanFlow adaptation, tested against native
Protenix and consistency baselines.

## 2026-09-13: Require a six-point Stage 0 matrix before training

Decision: evaluate `(cycles, steps)` = `(4,5)`, `(4,2)`, `(4,1)`, `(2,2)`,
`(1,2)`, `(1,1)` with `N_sample=1`, MSA off, fixed seed, and end-to-end timing.

Reason: Protenix exposes cycle/step overrides, but its docs require
`--use_default_params false` for manual overrides. The matrix separates diffusion
collapse from recycle collapse and prevents a new loss from being chosen before
the actual bottleneck is measured.

## 2026-09-13: Treat Mini-ESM training as an explicit integration task

Decision: use Mini-ESM for Stage 0 inference, but do not assume its training
path is turnkey. Before Stage 1, either add a local dataset loader for cached
ESM2-3B embeddings with a versioned cache contract, or begin with the Mini
non-ESM model and add ESM later.

Reason: the current Protenix training dataset does not attach ESM features by
default, and the maintainer describes Mini-ESM support as inference-first. The
embedding cache, tokenizer, alignment, and backend therefore affect both
reproducibility and the MSA-off claim.

## 2026-09-13: Separate matched monomer evaluation from DCFold headlines

Decision: compare DCFold only on matched monomer, MSA-off subsets and report
protocol differences. Keep a five-seed variance subset in Stage 0 even though
the deployment contract is one sample.

Reason: DCFold's published evaluation spans broader all-atom tasks, while this
project intentionally narrows the first target to monomers. A single headline
number would conflate task, data, MSA, and sampling differences.

## 2026-09-13: Replace ESM2 with ESMC as the active sequence conditioner

Decision: use frozen ESMC-600M with cached per-residue embeddings as the active
conditioner for a randomly initialized folding core. Use ESMC-300M as a memory
baseline, ESMC-6B as an upper-bound ablation, and keep the official Protenix
Mini-ESM checkpoint as a separate ESM2 compatibility baseline.

Reason: ESMC is the representation-learning branch of the current Biohub ESM
release and exposes sequence embeddings directly. ESM3 is a multimodal,
iterative sequence/structure/function generator; its structure track is not
allowed in the main input path because it would introduce an unstated folding
teacher. Changing from ESM2 to ESMC also changes embedding dimensions and
requires a learned adapter plus a separately trained folding core.

## 2026-09-13: Use UniProt for sequence coverage, experimental PDB for labels

Decision: build the sequence universe and self-supervised corpus from a pinned
UniProt release, but use only experimentally resolved PDB chain coordinates for
the main all-atom structure labels. Join the two through residue-level SIFTS
mapping and retain construct, mutation, missing-residue, isoform, and release
metadata. Do not use AlphaFold/ESMFold/ESM Atlas coordinates in the main target
set.

Reason: UniProt is a sequence and annotation database, not an all-atom
structure-label source. This removes coordinate-teacher bias while retaining
the unavoidable inductive bias of the chosen pretrained ESMC representation.
The release identifier and mapping snapshot are part of the reproducibility
contract.

## 2026-09-13: Treat ESMC/ESM3 as representation priors, not teacher-free truth

Decision: keep ESMC frozen and sequence-only in the main path. Report the exact
model revision and test for sequence overlap with the ESMC pretraining corpus
when that corpus is available. Use ESM3-open only as a sequence-hidden-state
ablation; never feed its structure-track outputs to the folding model.

Reason: ESMC is explicitly trained to represent protein biology from billions of
sequences, while ESM3 jointly models sequence, structure, and function and uses
iterative masked generation. Removing AF/ESMFold coordinates avoids a coordinate
teacher, but neither model is an unbiased representation source.

## 2026-09-13: Use exact-identity de-duplication for experimental GT

Decision: de-duplicate only at 100% sequence identity. Preserve near-identical
sequences, engineered constructs, and small mutations when they have valid
experimental PDB/SIFTS records. Multiple experimental structures for the same
exact sequence remain separate structure records unless a later ablation shows
that a single-label protocol is required.

Reason: the dataset should expose local sequence-to-structure changes instead
of erasing them with family-level clustering. Exact-sequence groups are still
assigned to one split so repeated labels for the same sequence cannot leak
across train, validation, and test.

## 2026-09-14: Start the experimental GT raw snapshot on hpc2

Decision: use the 2026-09-08 SIFTS CSV snapshot as the first raw manifest,
  with complete `pdb_chain_uniprot` and `uniprot_pdb` files. The observed
  segment file is currently a clearly marked partial download pending resume.
  Download all 244,406 PDB entries having a chain-level UniProt mapping as
  compressed mmCIF, plus UniProt FASTA for the 76,273 mapped accessions. Keep
  the PDB entry files and accession-batched FASTA files in separate raw
  directories under `/hpc2hdd/home/shuang886/Folding/Dataset`.

Reason: this preserves all experimentally mapped structures before monomer
filtering and exact-identity de-duplication. Near-identical constructs and
small mutations remain available for the later GT builder; no predicted
coordinates are downloaded.

## 2026-09-14: Re-estimate storage for the mapped coordinate-only GT

Decision: do not provision another 100 TB machine for the current raw GT
download. The active scope is compressed mmCIF for SIFTS-linked PDB entries plus
mapped UniProt FASTA, not a mirror of the complete PDB Core archive or its
experimental attachments. Based on the live download rate, the final raw
mmCIF layer is expected to be roughly 90--100 GiB; reserve 0.5--1 TB for
decompression, parsed shards, indexes, and temporary copies.

Reason: the previously mentioned TB-scale figure referred to a full PDB Core
snapshot and broader archival/working copies. It is not the size of this
coordinate-only, UniProt-linked subset. Additional storage may be revisited
for full-UniProt ESMC embedding caches or archival backups, neither of which is
required for the first GT build.

## 2026-09-14: Validate the initial mapped PDB raw layer

Status: all `244,406` manifest entries are present as `.cif.gz`, with no
remaining partial files. A full parallel `gzip -t` pass reported zero errors.
Gemmi parsing of a random 200-entry sample also succeeded; every sampled entry
contained at least one protein chain, while many contained multiple protein
chains/entities.

Implication: the raw layer is usable, but an entry is not yet a training
example. The GT builder must select SIFTS-mapped protein chains, apply the
monomer/length/quality policy, and only then perform 100% sequence-identity
grouping while retaining near-identical constructs and small mutations.

## 2026-09-14: Complete the SIFTS-linked raw snapshot before split work

Status: the observed-segment SIFTS file has finished its resumable download and
passes `gzip -t`. The raw snapshot now contains the three pinned SIFTS flatfiles,
`244,406` complete compressed mmCIF entries, and `76,273` UniProt FASTA records.
The FASTA accession set exactly matches the accession set in
`pdb_chain_uniprot.csv.gz`; no empty FASTA records were found. No sequence-
identity grouping or train/validation/test split has been performed yet.

Implication: subsequent work should treat these files as the immutable raw
input layer and build chain-level metadata/quality tables separately. Exact
100% SI grouping remains a later split-stage operation, with its alignment
method and denominator frozen before any partition is generated.

## 2026-09-14: Raw-layer acceptance and GT-builder gates

Acceptance: the raw snapshot is complete and internally consistent for the
current scope. It contains `244,406` PDB mmCIF files, `1,031,850` SIFTS mapping
rows, `1,557,033` observed-segment rows, and `76,273` non-empty UniProt FASTA
records whose accession set exactly matches the SIFTS accession set. The PDB
gzip layer passes a full integrity check.

The raw layer is not yet a trainable GT set. A sample of 200 entries showed
X-ray, electron-microscopy, and solution-NMR records, canonical protein chain
lengths from 11 to 3,159 residues (median 371 in that sample), multiple-model
NMR entries, and substantial residue/atom incompleteness. These require an
explicit quality and monomer policy.

Critical parser rule: SIFTS `CHAIN` must be resolved through
`_entity_poly.pdbx_strand_id` to an entity, then to one or more
`_struct_asym.id` label chains. It must not be looked up directly as a
`_struct_asym.id`, and `auth_asym_id` alone is not unique. In a 200-entry audit,
all 890 sampled SIFTS rows matched `pdbx_strand_id`; direct label-chain lookup
would have missed 338 of them. The global SIFTS table has `992,086` unique
PDB-chain pairs, with `9,927` pairs linked to multiple UniProt accessions; all
accessions must be retained as provenance until a later ambiguity policy is
declared.

Training is gated on a processed chain table and structure shards containing
the PDB polymer sequence, residue/atom coordinates, atom masks, residue index
mapping, experimental method/resolution/model metadata, and explicit missing-
residue/alternate-location handling. The UniProt sequence remains annotation
and coverage metadata; the folding input sequence should be the construct
sequence represented by the experimental PDB chain so that coordinates and
tokens align. SI grouping and split generation occur only after this GT layer
is built and audited.

## 2026-09-14: Structure-first GT and non-imputing primary branch

Decision: make the PDB mmCIF the authoritative source for the training sample.
The construct sequence, residue identifiers, coordinates, atom masks, and
residue masks are all derived from the resolved PDB entity/label chain. UniProt
accessions and SIFTS residue mappings remain attached only for provenance,
traceability, and later analysis; they do not define the model input sequence
or replace PDB coordinates.

Missing atoms are kept as missing in the primary branch and represented by atom
masks for the loss. Do not silently repair or overwrite observed coordinates.
PDBFixer may be evaluated as a separately versioned derived branch for missing
residues, but every imputed residue/atom must carry an `imputed_mask`, and the
default experimental GT loss must exclude imputed targets. The raw mmCIF files
remain immutable.

Reason: using PDB-derived sequence and coordinates keeps the sequence-to-label
alignment exact for constructs, engineered mutations, truncations, and
noncanonical experimental designs, while preventing structure completion from
being mistaken for experimental evidence.

Scope note: the current raw manifest still discovers entries through the pinned
SIFTS chain-to-UniProt table. Thus the sample content is structure-derived but
the inclusion universe is currently SIFTS-linked. An all-experimental-PDB
universe, including entries without a UniProt mapping, would require a new
entry manifest and a separate download decision.

## 2026-09-14: Lock the first-version entry universe

Decision: use the staged `244,406` SIFTS-linked PDB entries as the complete
first-version entry universe. Do not add PDB entries that lack a SIFTS-UniProt
link in this version. SIFTS is an inclusion/provenance index only; all model
inputs and experimental targets continue to be extracted from the PDB mmCIF
files.

Reason: fixing the entry universe now keeps the raw snapshot reproducible and
avoids expanding download and quality-policy scope before the chain-level GT
builder is audited.

## 2026-09-14: Switch the training unit to jointly modeled protein chains

Decision: the first model will not be single-chain-only. A training example is
a selected PDB structure instance containing a jointly modeled set of protein
chains. Each chain keeps its own PDB-derived sequence, residue/atom coordinates,
and masks; the instance additionally carries chain indices and inter-chain
geometry. Ligand and RNA entities remain provenance/context metadata and are
not model inputs in the first version.

The GT builder must explicitly distinguish asymmetric-unit coordinates from a
declared biological assembly using the mmCIF assembly categories. It must not
silently concatenate chains from unrelated entities or apply crystallographic
copies as if they were an observed biological complex. Total residues, chain
count, and interface coverage become dataset strata and evaluation dimensions.

Reason: the intended folding task is joint multi-chain structure prediction;
single-chain filtering would remove the inter-chain geometry and interface
supervision that the model is expected to learn.

## 2026-09-14: Harden Stage A before the full scan

Decision: do not start the 244,406-entry catalog scan until the Stage A scanner
has the corrected chain resolver, entity-aware atom classification, date
metadata, assembly composition summaries, and deterministic shard execution.
The authoritative SIFTS chain mapping is now
`_pdbx_poly_seq_scheme.pdb_strand_id -> asym_id`, with conservative
`auth_asym_id -> label_asym_id` and unambiguous entity-only fallbacks. Entity
categories and component IDs distinguish protein, nucleic acid, water, ions,
small molecules, other polymers, and unknown non-protein atoms; only protein
entities contribute observed-residue summaries.

The scanner writes ordered, deterministic gzip JSONL shards using SHA256 PDB-ID
assignment, atomic `.part` files, and a resume check. Stage A also records
deposition/release/revision dates and uses Gemmi generator metadata to count
generated assembly chain instances without materializing coordinates. The
active import path is `onestepfold.data`; `fastglycan.gt_catalog` is only a
compatibility shim.

This supersedes the earlier wording that made jointly modeled multi-chain
structures the first training view: the universal catalog and GT contract stay
multi-chain-aware, while the first materialized training/evaluation view is a
monomer pool.

Validation: a real HPC pilot over `101m`, `6xu7`, and `7wxm` had zero errors,
corrected `6xu7` composition (76 protein plus 7 nucleic-acid chains), separate
water/ion/small-molecule counts, complete date fields, identical repeated
output SHA256, and successful resume/shard checks. The next gates are 1,000
and 10,000-entry audits. Coordinate materialization, SI grouping, split
generation, and ESMC caching remain blocked until the catalog audit is accepted.

The subsequent 1,000-entry HPC pilot (eight workers) completed in about 46
seconds with 1,000 successes, zero errors, zero unresolved SIFTS rows, complete
date coverage, and Gemmi assembly composition for every record. This is a
throughput baseline only; a 10,000-entry distribution audit is still required
before the full job array.

The 10,000-entry audit then completed with 10,000 successes, zero errors, zero
unresolved SIFTS rows, complete date/composition coverage, and an approximately
4.8 MiB catalog shard. Its distribution included 1,191 solution-NMR entries,
324 entries with 20 models, and smaller theoretical/scattering categories;
water, small molecules, ions, other non-protein atoms, and nucleic acid atoms
were present in 7,866, 5,875, 3,346, 466, and 389 entries respectively. The
scanner is therefore ready for a full job array, but the quality policy must
stratify these categories before selecting the monomer training view.

## 2026-09-15: Freeze structural monomer eligibility and launch full catalog

Decision: the v1 monomer view is selected from biological assembly composition,
not ASU chain count. A candidate has exactly one generated protein chain
instance, zero generated nucleic-acid chain instances, and zero generated other
polymer chain instances. It also has a primary X-ray, electron-microscopy, or
neutron method, one coordinate model, and a 20--1024 residue construct.
Water, ions, and small molecules remain allowed in the primary `monomer_clean`
view; entries with zero small-molecule atoms are marked `monomer_apo_like`,
while polymer-context cases remain `contextual`.

Resolution, residue/backbone/heavy-atom completeness, chain breaks, and geometry
thresholds are intentionally deferred until the full Stage A catalog and Stage
B materialization distributions are available. The 244,406-entry Stage A scan
is launched as deterministic 256-shard jobs; only the catalog is generated at
this stage.

## 2026-09-15: Use Biopython pairwise identity for split construction

Decision: use Biopython `Bio.Align.PairwiseAligner` as the authoritative
sequence-identity calculator for the later split stage. The mode is global with
match `+1`, mismatch `-1`, gap-open `-1`, and gap-extend `-1`; identity is
identical residues divided by all global alignment columns, including gaps.
Exact sequence SHA256 is only a lossless candidate index, and same-digest
buckets are still pairwise-verified. CPU job-array parallelism is acceptable
for this offline construction step. No split is generated until the catalog
and Stage B GT are accepted.

## 2026-09-15: Accept full Stage A catalog and exact-SI candidate manifest

Status: the complete 256-shard Stage A scan contains 244,406 entries and
244,406 unique PDB IDs, with zero non-empty error files, zero partial outputs,
zero unresolved SIFTS rows, and zero missing assembly-composition records. The
catalog aggregate shard-manifest hash is
`8e62a4bdf1ee1ba4967e7b35fb2f3fd7f2de067055dbde9d81f10a113d581cf0`.

The frozen catalog-only monomer policy selects 84,232 `monomer_clean` entries;
64,674 have initial release on or before 2021-09-30 and 19,558 are later.
18,427 are also eligible for the zero-small-molecule `monomer_apo_like`
subset. Full-catalog resolution and sequence-length medians are 2.15 A and
225 aa; candidate-view medians are 1.90 A and 283 aa. These are descriptive
statistics only; Stage B completeness and geometry thresholds remain pending.

Strict 100% identity processing has completed on the candidate table. The
Biopython 1.87 global calculator verified 42,640 same-sequence member pairs,
forming 41,592 exact sequence groups from 84,232 records. The manifest is an
exact-sequence grouping artifact, not a near-homology split; all exact groups
must remain atomic in a later split.

## 2026-09-15: Run and accept the Stage B 10k materialization pilot

Decision: use an 8,000-record stratified sample plus 2,000 deterministic stress
cases for the first Stage B audit. Materialize fixed atom37 heavy-atom tensors
in NPZ tar shards and keep compact chain/residue/provenance/QA metadata in JSON;
do not duplicate coordinate arrays in the metadata file. The multi-chain-aware
materializer uses Gemmi assembly operators, while the current candidate view
contains one selected protein chain per biological assembly.

Validation: 32/32 workers completed 10,000/10,000 records with 64 tar shards,
20,000 paired tar members, zero index/member mismatches, zero shape errors,
zero metadata length errors, zero non-finite valid coordinates, zero mask
inconsistencies, and zero materialization errors. Missing sequence positions
retain sequence/residue metadata but have `residue_mask=false`; no PDBFixer
coordinates are used. After correcting the canonical three-letter fallback for
missing residues, 1,845 records contain at least one modified/noncanonical
component and are retained as a side-chain masking stratum; the earlier 8,721
count was a fallback-token QA false positive.

The pilot coverage medians are 0.943 observed-residue, 0.942 N/CA/C frame,
0.942 N/CA/C/O backbone, and 0.934 canonical-heavy-atom coverage. Same-sequence
variance found 3,373 pilot records in 911 exact groups, with 2,462
representative comparisons and 190 (7.72%) above the fixed RMSD/TM disagreement
threshold. This supports exact-group-aware record sampling rather than uniform
PDB-record sampling, but does not by itself freeze quality cutoffs.

## 2026-09-15: Accept full Stage B and freeze split views

Full materialization succeeded for all 84,232 `monomer_clean` records in 348
tar shards with 168,464 members, zero errors, zero shape/mask/finite-coordinate
violations, and zero missing member pairs. The frozen quality policy produced
78,259 Train-valid records, 45,815 HQ-Eval-valid records, and 5,973 rejects.

Quality-filtered exact groups and the initial-release cutoff (2021-09-30) now
define the split artifacts: 31,689 train-seen groups / 59,959 records, 6,711
unseen temporal test groups / 12,940 records, and 932 leakage-excluded
post-cutoff same-sequence groups / 5,360 records. The near-homology audit uses
Biopython `PairwiseAligner` with a separate high-gap-cost global scoring policy,
residue identity, shorter-sequence coverage >=0.70, and at least 50 aligned
residues. Only 15 groups / 18 records pass the strict <0.30 identity boundary;
the temporal test remains the primary held-out benchmark. ESMC embeddings are
not yet cached; they are the next data-layer operation and will be keyed by
exact sequence SHA256 plus model revision.

## 2026-09-15: Freeze GT quality v1 and launch full Stage B

Decision: apply a two-tier coordinate policy after full materialization. Train
v1 requires resolution <=4.5 A, N/CA/C frame coverage >=0.80, canonical
heavy-atom coverage >=0.75, internal missing fraction <=0.15, finite valid
coordinates, zero unexplained CA breaks, zero chirality violations, and zero
configured bond/peptide outliers. HQ-Eval v1 tightens these to <=3.0 A,
0.95/0.90 coverage, and <=0.02 internal missingness. Terminal missingness is
allowed and remains masked; modified residues are retained with unmapped side
chains masked. Clash counts and density are recorded only, not hard filters in
v1.

The 84,232 `monomer_clean` candidates are materialized in full Stage B tar
shards. The resulting per-record quality index is the authoritative input for
rebuilding exact-sequence groups and the 2021-09-30 time split. A group is
train-seen if it has a valid pre/on-cutoff member; later records of such a group
are leakage-excluded rather than test records. Only groups whose valid members
are all post-cutoff are test candidates. ESMC caching remains downstream of
this quality/split stage.

## 2026-09-15: Pin ESMC representation cache contract

Decision: use `biohub/ESMC-600M` at HF revision
`28aed46fcaf217dfa59f78a589bb449aa3ae5d98` with Biohub/esm revision
`bf343ba264b650dff7a073643725f9aaa1fdbe8d`. Build a 2,000-group all-layer
probe first, compare final/intermediate/all-layer representations with a small
structure-aware contact probe, and only then materialize the full 38,400-group
cache. Store residue-aligned BF16 features in sharded safetensors keyed by
sequence SHA256 and pinned model revisions.

Reason: Biohub ESMC exposes 36 transformer layers plus an embedding state, and
the folding representation may not be optimal at the final MLM layer alone.
Caching all layers for the full corpus would multiply storage by roughly 37, so
the probe is a cheap, reversible decision gate. ESMC remains a frozen sequence
representation prior; it is not treated as a structure-coordinate teacher.

The local 2,000-group all-layer smoke completed 2,000/2,000 groups and 594,600
residues in 37 BF16 safetensors shards. A preliminary 500-group,
group-held-out CA-contact probe (32,000 balanced pairs) scored layer 36 at
AUROC 0.706, versus 0.635 for layer 34 and 0.615 for a simple 12/24/36
concatenation. This is a representation diagnostic rather than a folding claim;
the final-layer result supports using `feature_variant=final` for the full
cache while retaining the all-layer probe as an auditable artifact.

## 2026-09-15: Accept the ESMC-600M final-layer cache

The pinned final-layer cache completed on one A800 in 33m47s using local-only
Hugging Face files. It contains 38,400/38,400 quality-valid exact sequence
groups, 11,615,845 residue rows, 178 sharded safetensors, and 26.8 GB of
BF16 feature data. The independent Slurm validator completed successfully in
1m11s with exact group coverage, unique manifest IDs, model/revision checks,
BF16 shape checks, and per-shard SHA256 checks. The cache is stored under
`/hpc2hdd/home/shuang886/Folding/esmc_600m_final_v1`; ESMC all-layer features
remain available only in the 2,000-group probe artifact to avoid multiplying
the production cache by 37. A pinned-model recomputation of one 327-residue
sequence matched its cached slice at cosine 0.999992 (maximum absolute error
0.00387 in float32 comparison after BF16 storage), and eight random cached
slices were finite with exact residue-by-hidden shape.

## 2026-09-15: Freeze Stage 0A dev/test views and factorial protocol

The Stage 0 compatibility baseline remains official
`protenix_mini_esm_v0.5.0` with its native ESM2 conditioner; the ESMC cache is
not used in this baseline. The protocol is now the complete 3x3 factorial over
cycles `{1,2,4}` and structure steps `{1,2,5}`, one sample, BF16, MSA/template
off, and maximum length 1024. The anchor is `(4,5)` and the variance seeds are
`101,103,107,109,113`.

From the 6,711 post-cutoff temporal candidate groups, 3,464 have HQ-valid
targets. A deterministic joint-stratified selector (length, resolution,
apo-like, method) froze 1,024 `temporal_dev_v1` groups, a nested 128-group
`temporal_variance_v1` subset, and 2,440 remaining HQ groups as
`frozen_temporal_test_v1`. All 15 strict low-homology groups are excluded from
dev sampling and listed in `frozen_temporal_low_homology_groups_v1`; eight have
HQ targets and seven remain group-only exclusions because no HQ target exists.
Repeated generation with the same seed produced identical manifest SHA256s.

The first Protenix runner targets the `i64m1tga800ue` partition with one A800
per independent factorial-point job and records command/environment plus
`/usr/bin/time -v` output. The modern `protenix==1.1.0` CLI is used to load the
`protenix_mini_esm_v0.5.0` checkpoint; the package wheel and checkpoint SHA256
are pinned separately. A compute-node smoke test and fixed kernel/backend
metadata are required before the sweep; no Stage 0 accuracy result is claimed
yet.

## 2026-09-15: Submit Stage 0 points as independent A800 jobs

Decision: do not request all eight A800s on one `i64m1tga800ue` job. Submit
each of the nine `(cycle, step)` settings as its own one-GPU job with 8 CPUs,
64G RAM, and a default 12-hour walltime. This matches observed scheduler
placement and makes a failed setting independently restartable without
repeating the other eight points.

The staged ESM2 conditioner is `esm2_t36_3B_UR50D.pt` with SHA256
`7de8b4082ba15891959ab368b77ce3886697af1efb16d3c9e9e7b0c5d3f07500`; it is
stored beside the Mini checkpoint under the pinned Protenix runtime root.

The functional gate and full 3x3 sweep were submitted on hpc2 as independent
one-GPU jobs. The smoke gate is job `12754884`, the one-target functional gate
is `12755045`, and the nine factorial jobs are `12755102` through `12755110`.
All full jobs depend on `afterok:12755045`; pending scheduler state is not an
inference result.

## 2026-09-16: Complete Stage 0A A800 sweep and preserve lightweight results

All nine independent `i64m1tga800ue` jobs completed with exit status 0. Each
of the 1,024 frozen temporal-dev targets produced one CIF and one confidence
summary for every `(cycle, step)` setting, for 9,216 predictions total. The
confidence summaries had zero parse errors and zero `has_clash` flags; peak RSS
was approximately 17.2 GiB per job. The full machine-readable summary is
tracked in `reports/stage0_runtime_summary_2026-09-16.{json,csv}` and the
reproducible parser is `scripts/summarize_stage0_runs.py`.

This result is explicitly a runtime/output-yield checkpoint, not a folding
accuracy result. Raw multi-gigabyte CIF/JSON outputs remain on HPC at
`/hpc2hdd/home/shuang886/Folding/stage0_v1/protenix_runs`; GT-backed TM-score,
lDDT, RMSD, and geometry evaluation must happen before interpreting the
factorial quality surface.

## 2026-09-16: Complete Stage 0B GT-backed collapse-surface scoring

All 9,216 Stage 0 predictions were evaluated against their exact sequence-group
Stage B GT targets. The evaluator reported 9/9 settings with 1,024/1,024
successful records and no parse or alignment errors. It computes fixed-residue
Kabsch Cα TM-style score, Cα lDDT, all-heavy-atom lDDT, Kabsch backbone RMSD,
and sidechain RMSD; the aggregate definition and caveat are documented in
`reports/stage0_eval_summary_2026-09-16.md`.

The mean Cα TM-style surface was:

```text
             step=1  step=2  step=5
cycle=1       0.8809  0.8816  0.8794
cycle=2       0.8933  0.8944  0.8894
cycle=4       0.9029  0.9009  0.8990
```

All-atom lDDT showed the same broad cycle effect but non-monotonic step effect.
Against the paired `c4_s5` anchor, `c1_s1` had median Delta TM -0.0051 and
11.5% of targets below -0.05; `c2_s2` was effectively tied (median +0.0002),
and `c4_s1`/`c4_s2` were slightly above the anchor on this dev view. This is
evidence to prioritize recycle/trunk collapse and internal structure timing;
it is not a final temporal-test result and does not yet justify a MeanFlow
method claim.

## 2026-09-16: Add paired bootstrap and hard-tail diagnostics

The 1,024-target paired analysis uses `c4_s5` as an anchor and 5,000
target-level bootstrap resamples. For `c1_s1`, mean Delta TM-style score was
`-0.0181` (95% bootstrap CI `[-0.0222,-0.0142]`), median Delta was `-0.0051`,
and 11.5% of targets fell below `-0.05`. For `c2_s2`, mean Delta TM-style
score was `-0.0047` (CI `[-0.0080,-0.0016]`) and mean Delta all-atom lDDT was
`-0.0012` (CI `[-0.0023,-0.0002]`). `c4_s2` was above the anchor on mean
all-atom lDDT by `+0.0071` (CI `[+0.0065,+0.0077]`) on this dev view.

The `c1_s1` Delta-TM `< -0.05` tail contains 118/1,024 targets. Its median
length was 369.5 residues versus 281.0 outside the tail, and median resolution
was 2.00 A versus 1.80 A. These are descriptive signals, not causal evidence;
the next experiment profiles internal model stages and tests representation/
confidence-based adaptive recycling.

## 2026-09-16: Profile internal Stage 0 model timing

Four independent A800 profiling jobs (`c1_s1`, `c1_s5`, `c4_s1`, `c4_s5`)
ran on the same 128-target prefix with a runtime-only `sitecustomize` overlay.
The overlay GPU-synchronizes wrappers around pairformer, diffusion, and the
confidence head and writes one record per target without changing model code or
outputs. On the shared-node comparisons, `c1_s5 -> c4_s5` increased median
pairformer time by approximately `0.585 s` and median model-forward time by
`0.587 s`; `c4_s1 -> c4_s5` increased median diffusion time by `0.053 s` while
median pairformer time changed by `0.002 s`. The timing scope excludes model
load, preprocessing, and output serialization. These results support treating
recycle/trunk collapse as the primary efficiency target and structure-step
collapse as a secondary optimization.

## 2026-09-16: Advance to predictive, risk-aware recycling

Stage 0D uses only `temporal_dev_v1`; the frozen temporal test remains unread.
GT oracle routing confirms meaningful target-dependent recycle demand. On the
practical `c1_s1 -> c2_s2 -> c4_s5` path, jointly requiring TM-style score and
all-atom lDDT within 0.01 of `c4_s5` needs 2.231 mean cycles, a 44.2% reduction
from fixed four-cycle inference. The fixed-`s1` joint oracle needs 2.568 mean
cycles under the same tolerance. These are unattainable upper bounds that
assume reusable intermediate cycle states, not router results.

The first predictive audit defines hard targets as `c1_s1` TM-style degradation
below -0.05 versus `c4_s1` (126/1,024 targets). Five-fold out-of-fold evaluation
groups 784 closest-pre-cutoff-train sequence proxies. Cycle-1 confidence raises
AUROC from about 0.63 for sequence-only features to 0.87--0.89. At TM
catastrophic risk <=1%, the best simple learned router uses 2.066 mean cycles,
versus 2.102 for a pTM threshold and 2.465 for the reactive cycle-1-to-cycle-2
distance-map convergence baseline. However, joint TM/all-atom risk is harder:
the learned router needs 3.177 cycles at <=1% joint risk, while the reactive
baseline needs 2.920. Therefore a generic classifier is not yet the method;
future work must test joint-risk targets and genuinely cycle-1 internal state
features before making a novelty claim.

## 2026-09-16: Complete cycle-1 internal-state router audit

The pinned Protenix cycle-1 hook completed on A800 job `12759723` with
1,024/1,024 records, one Pairformer-cycle state per target, and zero feature
errors. It records compact single/pair representation statistics without
persisting model tensors. The analysis is in
`reports/stage0d_router_analysis_internal_2026-09-16.{json,md}`; the JSON
records the feature-file SHA256 for provenance.

Adding these internal statistics to cycle-1 confidence features changes the
TM-catastrophe (risk <=1%) HGB policy from 2.066 to 2.031 mean cycles. For the
joint TM/all-atom risk <=1% constraint it changes 3.177 to 3.156 mean cycles;
the geometry-plus-internal variant is not consistently better. These are
small, dev-only, out-of-fold diagnostic gains on `temporal_dev_v1`, not a
method claim. The frozen temporal test remains unread. Stage 0D therefore
continues to treat predictive risk-aware recycling as the research question,
with `c2_s2` and reactive convergence retained as strong non-learned baselines.

For sidework, use the two Precision W7900 cards for the pinned ESMC-300M scale
ablation. Hash-partition the 38,400 exact sequence groups across two independent
cache writers, merge only manifests, and validate full coverage/checksums. Do
not recompute the already accepted ESMC-600M cache or use ESM3 structure-track
outputs as teacher labels.

## 2026-09-16: Accept the Precision ESMC-300M scale-ablation cache

The two W7900 partitions completed in 840.2 and 847.4 seconds. Their merged
cache contains 38,400/38,400 groups, 11,615,845 residues, and 719 BF16
safetensors shards occupying 21 GB. The independent validator checked every
shard checksum, feature shape, model/revision field, sequence length, and exact
group coverage. The pinned model revision is
`f0d413606442e6b433d5e75e9aae3285ca9b137f`; the Biohub/esm revision remains
`bf343ba264b650dff7a073643725f9aaa1fdbe8d`. Use this cache only for the 300M
conditioner ablation; ESMC-600M remains primary. An independent recomputation
of one 125-residue sequence matched its cached `[125,960]` BF16 slice at cosine
0.9999932 with maximum absolute error 0.0009766.

## 2026-09-16: Complete Stage 0E c2-to-c4 routing audit

An independent two-cycle `c2_s2` Protenix run completed on A800 job
`12761522` in 29:56 with 1,024 predictions and zero hook errors. Stage 0E
labels a target hard when `c2_s2` is worse than `c4_s5` by more than 0.05 in
TM-style score or all-atom lDDT; 76/1,024 dev targets are hard under this
joint label. The feature artifact and input checksums are recorded in the
Stage 0E JSON report.

At joint catastrophe risk <=1%, the GT oracle needs 2.129 mean cycles. The
best current family-proxy grouped OOF learned policy is HGB with c2 confidence
and c1-to-c2 trajectory features at 2.477 cycles; c2 confidence plus deltas is
2.475. The existing reactive c1-to-c2 distance baseline is 2.551 cycles, so
the learned policy closes only a small part of the oracle gap. A matched-setting
`c1_s1` to `c2_s2` coordinate-change proxy is weaker at 2.729 cycles and is not
an in-forward intermediate structure.

This is a positive but diagnostic result, not yet a method claim. Thresholds
are swept on the same OOF predictions, so the next methodological gate is
nested calibration or a held-out dev split before any frozen-test evaluation.
The current default remains fixed `c2_s2`; recycle emulation is not started
until this calibration is complete.

## 2026-09-16: Start Stage 1A recycle residual characterization

The router line is frozen as a diagnostic; Stage 1A asks whether the c2-to-c4
refinement itself is cheap to approximate. A residual hook was added in
`scripts/protenix_residual_sitecustomize.py`; it keeps only the previous cycle
tensor and emits compact single/pair residual norms, sequence-distance
locality, and pooled spatial/channel low-rank energy. It never serializes full
`L^2 x d` pair tensors.

Before the hidden-state hook completed, the existing standalone c2_s2 and
c4_s2 predictions were compared as a coordinate proxy. Across 1,024
temporal-dev records, median Kabsch C-alpha RMSD was 1.076 A and median
pair-distance RMSD was 0.752 A. The 76 joint-hard records had medians 5.234 A
and 3.422 A, with median residue-displacement p90 7.068 A and active-residue
fraction 0.908, versus 0.747 A and 0.064 for nonhard records. This is strong
evidence that late recycle correction is concentrated in a small hard tail,
but it is explicitly a cross-setting coordinate proxy rather than an
in-forward hidden-state residual.

The expanded coordinate audit adds residual concentration/locality diagnostics.
For joint-hard targets, the median top-10-residue displacement-energy fraction
is 0.275 versus 0.676 for nonhard targets, while median pair-distance residual
energy within sequence distance <=8 is 0.0027 versus 0.0126. Thus the hard
tail is not simply a few local side-chain edits; its c2-to-c4 coordinate proxy
is a broader rearrangement. Hidden-state residual measurements are still
pending the A800 smoke/full hook.

## 2026-09-16: Fix residual hook shape and failure handling

The first A800 residual smoke reached the model output successfully but exposed
two hook-only bugs: Protenix's Pairformer hook emits unbatched `[L,C]` and
`[L,L,C]` tensors, and an exception while summarizing one transition removed
the previous-cycle tensor before later transitions could use it. The hook now
normalizes optional batch dimensions and only releases the previous tensor after
the residual summary succeeds. The original model prediction was unaffected;
the residual full run remains gated on a clean replacement smoke.

The replacement A40 smoke confirmed the shape fix but found a second
diagnostic-only backend issue: CUDA `linalg_eigh` does not support BF16 on that
GPU. Channel covariance is now explicitly accumulated in FP32 before the
eigendecomposition; model inference remains BF16 and unchanged. A clean smoke
is required again before the full residual run.

The subsequent A40 run showed the same BF16 limitation inside pooled spatial
SVD (it dispatches through CUDA eigendecomposition). The pooled spatial
diagnostic is now also cast to FP32; all residual summaries are analysis-only
and do not alter Protenix inference.

## 2026-09-17: Pass the Stage 1A residual smoke gate

The final single-target smoke (`12767861`) ran on an A40 debug node in 1:27
with the pinned Mini-ESM runtime and produced one `cycle_count=4` JSONL row with
all three transitions (`c1_to_c2`, `c2_to_c3`, `c3_to_c4`) and zero
`feature_error` fields. The diagnostic hook performs its linear algebra on
detached CPU FP32 tensors for cross-GPU determinism; Protenix inference remains
BF16. The short emergency smoke was cancelled after the debug smoke passed.
Full `c4_s2` residual characterization over `temporal_dev_v1` is submitted as
A800 job `12767871` with 8 CPUs and 64G RAM.

## 2026-09-17: Close Stage 1A and start parallel residual-emulation branches

The full Stage 1A job `12767871` completed with 1,024/1,024 valid rows and all
three transitions. The corrected analyzer now recovers sequence length from
the Stage 0E `features.log_length` field and reports length bands plus partial
correlations. Pair residual mean remains correlated with c2 all-atom
degradation after length control (approximately -0.40 for c2-to-c3 and
c3-to-c4), so raw Frobenius scaling is not the sole explanation. The pooled
rank-8 result is explicitly interpreted as low-rank spatial magnitude
structure, not a claim about the signed `L x L x d` residual tensor.

The next work is parallel rather than serial. `select_teacher_pairs.py`
selects one deterministic quality-valid pre-cutoff train record per exact
sequence group; a 32-group end-to-end teacher smoke passed on two debug A40
jobs (`12769064`/`12769065`) with 32/32 predictions for both settings and
validator coverage 64/64. The 16-shard, 16,000-group
`c2_s2` and `c4_s2` arrays are queued as Slurm jobs `12768989` and `12768990`
on `i64m1tga800ue`. The first queue attempt exposed and fixed zero-padded
array-shard and Protenix environment propagation issues before any inference
ran. The input selector accepts the frozen train-only manifest
which omits an explicit `split` field, while still filtering a combined
manifest when one is supplied.

The residual overlay now has an opt-in `ONESTEPFOLD_SIGNED_SKETCH=1` path that
writes deterministic FP16 spatially pooled signed pair sketches and records
cosines between adjacent residual directions. A one-target A40 debug smoke
(`12768912`) passed with all three transition sketches and direction cosines;
the corrected 256-target `c4_s2` diagnostic is queued as `12769005` on the
debug partition and is a diagnostic artifact only. It does not read the frozen
temporal test. Coordinate-refiner training remains gated on
successful teacher-pair QA; no new model claim is made yet.

The first 1B implementation is now in `src/onestepfold/models/coordinate_refiner.py`.
`GlobalCoordinateRefiner` is deliberately a C-alpha-only baseline: a small
global Transformer predicts a bounded correction in a residue-local N/CA/C
frame and returns the correction in Cartesian coordinates. Unit tests verify
rigid-transform consistency and residue/frame masking. It is a benchmark
component, not an all-atom replacement or a claim that the late residual is
local.

The 256-target signed-sketch diagnostic (`12769005`) completed on the debug
A40 node with 256/256 rows and 1,280 sketches. Adjacent residual directions
are not aligned: pair cosine medians are -0.086 (`c2->c3`) and -0.131
(`c3->c4`), while single cosine medians are -0.122 and -0.289. The signed
random-projection spatial sketch has median rank-8 energy about 0.82 for the
late transitions, substantially below the nonnegative magnitude-map rank-8
energy around 0.99. Therefore the simple scalar fixed-point extrapolation is
not promoted as the primary emulator; keep it only as a cheap negative
baseline, and prioritize a learned global coordinate residual or a richer
signed latent probe.

## 2026-09-17: Isolate Protenix teacher-shard working directories

Decision: every Slurm teacher-pair shard must run Protenix from a private
working directory under its output directory, and the wrapper must return a
non-zero status when Protenix logs per-target `Data error` messages.

Reason: Protenix's ESM2 featurizer writes a relative `./esm_embeddings`
directory. Concurrent c2/c4 array tasks sharing a process working directory
overwrote each other's temporary sequence-to-embedding index. The Protenix
runner can still exit zero after skipping data-error targets, so Slurm's
`COMPLETED` state is not sufficient evidence of a complete teacher shard.
Teacher-pair validation must require matching c2/c4 artifacts and empty data
error logs. The corrected wrapper is committed as `79da1e8`; formal isolated
arrays are `12770049` and `12770050`.

## 2026-09-17: Restrict teacher pairs to Protenix-supported sequences

Decision: teacher-pair generation uses only sequences in the canonical
20-amino-acid alphabet `ACDEFGHIKLMNPQRSTVWY`. Groups containing `X`, `U`,
`B`, or `Z` remain in an explicit exclusion manifest and are not silently
canonicalized.

Reason: the accepted PDB GT contains 171 unsupported-symbol groups in the
initial 16,000-group input (320 rows were excluded when selecting the corrected
v3 pool because the selector operates on the full pre-cutoff group table).
Protenix Mini's `PROTEIN_1to3` parser raises `KeyError` for these symbols.
This is a teacher compatibility filter only; the observed GT dataset remains
unchanged. The corrected v3 input has 16,000 valid groups across 16 shards,
and arrays `12771048`/`12771049` are the only current formal submissions.

## 2026-09-17: Accept the mixed-source c2/c4 teacher corpus

Decision: accept the consolidated DiamondHill teacher corpus for downstream
paired analysis. c2 shards 0--11 come from hpc2 array `12771048`, c2 shards
12--15 come from hpc3 ACD jobs `628767--628770`, and c4 shards 0--15 come from
DiamondHill. Preserve this mapping in the corpus provenance rather than
treating the c2 setting as single-backend output.

Reason: uniform validation on DiamondHill found all 16,000 expected group IDs
in both settings. Exhaustive QA parsed all 32,000 CIF files, checked every
confidence JSON and expected recycle count, and matched every shard log to its
expected successes with zero data errors. This establishes completeness and
artifact integrity; it does not establish numerical equivalence between GPU
backends. Consolidation was copy-only and did not move or modify EngramFold,
shared protein data, or Protenix checkpoints.

## 2026-09-17: Freeze the exact-group teacher split and loader contract

Decision: freeze `teacher_pair_manifest_v1` with 14,400 train groups and 1,600
validation groups. Assignment uses seed 101 and a versioned SHA256 rank over
the exact-sequence group ID. The 16,000-row teacher pool already contains one
record per pre-cutoff exact group; the frozen temporal test is not read or
modified by this split.

The paired loader resolves artifact paths relative to the accepted output
root, parses c2/c4 lazily, verifies the declared sequence, requires identical
atom keys, preserves missing backbone atoms as masks, and performs no
coordinate imputation. It also requires `num_recycles=2` for c2 and 4 for c4.
An exhaustive DiamondHill pass loaded all 16,000 pairs, aligned 37,321,433
atoms, and found zero failures or missing N/CA/C/O atoms. This freezes the
input contract for the first coordinate-refiner baseline; it does not imply
backend equivalence or model-quality calibration.

## 2026-09-17: Use hpc3 as the sole OneStepFold training host

Decision: all subsequent OneStepFold training runs on hpc3. DiamondHill keeps
the accepted source/archive copy of the c2/c4 teacher corpus, while hpc3 uses
the copy rooted at `/data/user/shuang886/Folding/stage1b/teacher_pairs_v3` and
the existing `/data/user/shuang886/Folding/esmc_600m_final_v1` cache.

The transfer was copy-only, excluded transient Protenix `work` directories,
and did not delete or modify the source. The compact teacher output on both
systems has 64,094 files and 7,608,200,910 bytes with the same relative-path
and size digest. hpc3 independently found 16,000/16,000 c2 and c4 predictions.
Its ESMC manifest contains 38,400 exact groups and covers every teacher group
with zero missing records or sequence-length mismatches. A joint smoke loaded
one paired CIF example and its `[L,1152]` BF16 ESMC slice successfully. This is
an infrastructure acceptance, not a coordinate-refiner quality result.

## 2026-09-17: Pass the 32-target coordinate-refiner overfit gate

Decision: use frozen ESMC-600M final-layer residue features, c2 backbone
coordinates, and a c4 C-alpha target rigidly Kabsch-aligned into the c2 frame
for the first coordinate-refiner training path. Load ESMC ranges lazily from
their safetensors shards, keep atom/padding masks explicit, and batch by length.

hpc3 H100 job `629419` trained on the 32 shortest records in the frozen train
split. The aggregate uncorrected c2 baseline C-alpha RMSD was 1.2432 A; the
best training RMSD was 0.1712 A at epoch 255. The final-to-baseline RMSD ratio
was 0.1377 and the final-to-initial coordinate-MSE ratio was 0.000612, passing
the predeclared 0.50 and 0.10 gates. This establishes implementation integrity
and small-set capacity only. It is not validation evidence and does not justify
an all-atom or thermodynamic claim. The next gate must select checkpoints only
with the frozen 1,600-group validation split.
