# OneStepFold GT Protocol v1

Status: frozen structure contract, catalog-first implementation.

This protocol defines the first-version representation of experimental
multi-chain protein structures. It deliberately does not freeze the final
quality thresholds or train/validation/test split. Those are selected only
after the complete Stage A catalog has been audited.

## Entry universe

The first-version universe is the staged `244,406` SIFTS-linked PDB entries
under `/hpc2hdd/home/shuang886/Folding/Dataset`. No additional PDB entries are
added in v1. This is an inclusion/provenance choice; the model input sequence
and coordinates are still read exclusively from PDB mmCIF.

## Two-stage pipeline

```text
raw mmCIF
  -> Stage A catalog scan
  -> catalog_v1 audit and filter decision
  -> Stage B coordinate materialization
  -> structure_instance GT v1
  -> QA
  -> later sequence clustering/split/embedding stages
```

Stage A must not emit full coordinate arrays. It records entry, entity, chain,
assembly, experimental, missing-observation, alternate-location, and hidden
context summaries. Stage B is the only stage that materializes coordinates.

For reproducible HPC execution, the scanner supports deterministic SHA256
PDB-ID sharding with `--shard-id` and `--num-shards`, an optional `--pdb-list`
manifest, `--limit` for pilots, and `--resume` for completed shards. Use one
output/error pair per shard; a shard is committed by atomic rename only after
all of its selected entries have been scanned.

## Structure instance and assembly views

The training unit is a jointly modeled set of protein chains from one selected
structure instance. The schema supports both `asymmetric_unit` and
`biological_assembly` views. The catalog retains all `_pdbx_struct_assembly`
and `_pdbx_struct_assembly_gen` definitions, including their raw operation
expressions and asym ID lists. It does not silently choose assembly 1 or
expand operators during Stage A.

Each assembly record stores independent `author_determined` and
`software_determined` booleans in addition to the raw details. Both may be
true for an entry. Stage A also computes a compact assembly composition using
Gemmi's parsed generators: source asym counts and generated protein,
nucleic-acid, and other-polymer chain-instance counts, together with total
polymer counts. No coordinate arrays are written at this stage.

When an assembly is materialized, each generated copy receives a unique
`assembly_chain_instance_id`, for example `A@1`, `A@2`, and so on. This ID is
distinct from `chain_index`, `entity_id`, and `source_label_asym_id`. The
materializer also records `operator_path` and `entity_instance_index`.

The assembly generator must use Gemmi's assembly implementation. It must not
hand-parse operation expressions or treat crystallographic copies as a
biological assembly without the mmCIF assembly definition.

## Sequence and residues

The authoritative input sequence is
`_entity_poly.pdbx_seq_one_letter_code_can` from the PDB entity. It is not
reconstructed from observed atoms and it is not replaced by UniProt. A residue
with no coordinates remains in the sequence and receives `residue_mask=false`
and zero atom validity. Author residue number, insertion code, label sequence
number, and component ID are retained separately.

UniProt/SIFTS rows are provenance only. All accession mappings are retained;
the materializer must not overwrite multiple accessions with an arbitrary
single value.

## Atoms and missing observations

The canonical storage representation is `atom37_heavy_v1`: 37 fixed heavy-atom
slots per residue, with `atom_positions[Nres,37,3]` and
`atom_mask[Nres,37]`. Hydrogens are not required by the PDB source and are not
part of the v1 target. An `atom14` view may be derived later, but atom37 is the
canonical serialized form.

Missing atoms are not imputed in the primary branch. PDBFixer output, if
evaluated, is a separate versioned branch with `imputed_mask`; imputed atoms
are excluded from the default experimental loss. Unknown or modified residue
components retain their raw `comp_id` and `is_modified_residue` flag. No
silent parent-residue conversion is performed in the catalog.

## Alternate locations

Alternate locations are selected coherently at residue level during Stage B:

1. blank-altloc atoms are treated as shared atoms;
2. each nonblank altloc receives the sum of its residue atom occupancies;
3. the highest total occupancy conformer is selected;
4. ties are resolved deterministically by `A`, `B`, then lexical order;
5. the selected ID and occupancy fraction are serialized.

Atoms from different conformers must never be combined by independent
per-atom occupancy maxima.

## Models and experimental metadata

Stage A records all model IDs and experimental methods. The primary v1
materializer accepts one coordinate model per structure instance. NMR or other
multi-model entries are retained in an auxiliary catalog/derived pool until a
separate ensemble policy is approved; they are not treated as independent
ground truths by default.

Resolution and method fields are descriptive at catalog time. Method-specific
quality thresholds are selected after seeing the full catalog distribution.
The catalog also records `initial_deposition_date`, `initial_release_date`, and
`latest_revision_date` from the PDB database-status and audit-revision
categories.

## Multi-chain symmetry and hidden context

The model may permute equivalent homomer chains. `entity_id`,
`homomer_group_id`, and `entity_instance_index` are biological metadata; the
training and evaluation code must use permutation-invariant matching for
equivalent chain instances and may randomize storage order.

Stage A classifies non-protein atoms using `_entity.type` and component IDs
into water, ions, small-molecule/non-polymer, nucleic acid, other polymer, and
other unknown categories. It summarizes protein-protein interfaces and protein
contacts with nucleic-acid or ligand entities. Ligands and RNA/DNA are not model
inputs in v1, so strong hidden-context cases are flagged rather than silently
discarded.

Interface residue fields are named `interface_label_seq_ids_i/j` because they
contain one-based PDB `label_seq_id` values, not zero-based tensor indices.

## Versioning and QA gates

Every materialized record stores the source mmCIF checksum, parser version, and
`gt_protocol_v1`. The gold set must include asymmetric-unit/assembly cases,
symmetry copies, homomers, heteromers, alternate locations, missing residues,
auth/label chain differences, EM, and multi-model entries.

No split or ESMC cache is created until:

- the complete catalog is generated with zero unexplained parser failures;
- Stage B round-trips sequence, chain instance IDs, masks, and assembly transforms;
- the catalog and materializer pass the gold-set validator;
- a separate decision freezes quality filters and coordinate views.
