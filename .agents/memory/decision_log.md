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
