# Project context

Updated: 2026-09-14

The active project is now OneStepFold: a strict, open, MSA-off protein folding
experiment with a multi-chain-aware GT catalog and a monomer-first training
view. The model target remains one Pairformer cycle, one structure-module
network evaluation, and one output sample. The primary sequence conditioner is frozen
ESMC-600M with cached per-residue embeddings; ESMC-300M and ESMC-6B are scale
ablations. The folding core is randomly initialized and trained separately.
The official `protenix_mini_esm_v0.5.0` ESM2 path is a compatibility baseline,
not the active conditioner. Clean-Structure MeanFlow remains the proposed
method with native one-step/consistency baselines.

Current scientific boundaries:

- the catalog is multi-chain-aware, but the first training/evaluation view is a
  declared monomer pool; a future multimer view reuses the same GT schema;
  ligand/RNA entities are not model inputs in the first view;
- MSA disabled by experimental protocol, with ESMC used as the single-sequence
  conditioner;
- `N_cycle=1`, structure `N_step=1`, `N_sample=1` are the final target, not an
  assumed starting capability;
- structure-core NFE and end-to-end ESM latency are reported separately;
- a clean-structure MeanFlow loss requires a derived JVP target and geometry
  path validation; it is not a plain coordinate MSE label;
- ESMC is not a drop-in replacement for Protenix Mini-ESM: the cache, model
  revision, residue alignment, and dimensionality adapter are versioned
  artifacts, and the ESMC folding core is trained separately;
- ESM3 structure-track outputs are excluded from the main input contract; ESM3
  is sequence-hidden-state-only ablation because its multimodal generation can
  act as an unstated structure teacher;
- the primary training sample is structure-derived: the input sequence,
  residue numbering, and all-atom target come from the PDB mmCIF entity/chain;
  UniProt/SIFTS is retained for provenance and residue-level traceability only,
  not as the source of the model input sequence or target coordinates;
  AF/ESMFold/Atlas coordinates are excluded from the primary target set;
- the initial hpc2 raw snapshot uses SIFTS flatfiles dated 2026-09-08,
  yielding 244,406 chain-mapped PDB entries and 76,273 UniProt accessions;
  remote downloads are staged under `/hpc2hdd/home/shuang886/Folding/Dataset`
  with PDB mmCIF and mapped UniProt FASTA kept as separate raw layers;
- the first-version entry universe is deliberately fixed to the `244,406`
  SIFTS-linked PDB entries already staged on hpc2. This is not an all-
  experimental-PDB universe, and no unmapped entries will be added in the first
  version. SIFTS remains an entry-discovery/provenance layer only; the training
  sequence and coordinates are still extracted exclusively from PDB mmCIF;
- dataset de-duplication is restricted to exact (100% sequence identity)
  duplicates at the chain level. Near-identical proteins, construct variants,
  and small mutations remain eligible records; exact-sequence groups must still
  be kept together when making train/validation/test splits to prevent label
  leakage, while the multi-chain structure instance remains the training unit;
- a PDB time split does not establish that ESMC has not seen a held-out sequence;
  record the exact ESMC revision and audit sequence overlap when its pretraining
  corpus is available, otherwise report residual representation-contamination
  risk;
- the authoritative 100% SI calculator is Biopython
  `Bio.Align.PairwiseAligner` in global mode, with identity defined as matches
  divided by all global alignment columns including gaps. Exact sequence
  SHA256 is only a lossless candidate index; it does not replace pairwise
  verification or introduce near-identity clustering;
- CUDA-oriented Protenix kernels and unverified ROCm fallback make backend and
  kernel selection part of the benchmark record;
- existing `src/fastglycan` code is preserved as a legacy prototype and is not
  the active data contract.

GT handling constraints:

- the chain resolver must map `SIFTS CHAIN ->
  _entity_poly.pdbx_strand_id -> entity_id -> _struct_asym.id -> atom_site`;
- missing atoms are not repaired in the raw or primary GT branch. Coordinates
  and atom masks are emitted as observed, and the training loss decides which
  atom labels are valid;
- missing residues may have a separately versioned PDBFixer-derived branch,
  but imputed residues/atoms must carry an explicit `imputed_mask` and are not
  treated as experimental coordinates by default;
- the raw mmCIF layer is immutable; any PDBFixer output is a derived artifact
  with its own provenance and does not replace the observed structure.

Multi-chain GT constraints:

- the universal GT schema represents a selected PDB structure instance and can
  contain multiple jointly modeled protein chains; the first training view
  selects monomer instances from that catalog;
- the GT record stores one sequence/residue/atom/mask block per chain plus a
  stable `chain_index`, `entity_id`, and label asym ID; total-residue and
  chain-count limits are applied at the instance level;
- the builder must preserve inter-chain geometry and emit chain-pair metadata
  needed for interface/contact losses and evaluation;
- `_pdbx_struct_assembly` and `_pdbx_struct_assembly_gen` must be inspected
  before shard creation. Asymmetric-unit coordinates and biological-assembly
  coordinates are distinct derived views and must never be silently mixed.

The first implementation milestone is Stage A: a deterministic catalog scan
over the fixed entry universe. Stage 0 folding evaluation uses a declared
low-homology monomer view with a paired fixed-seed run and a five-seed variance
subset. Do not start training or make an accuracy claim until the catalog,
monomer filter, checkpoint, Protenix version, assembly policy, kernel, and
latency accounting are captured.

Stage A scanner hardening has passed 3-entry, 1,000-entry, and 10,000-entry
HPC audits with zero parser errors and zero unresolved SIFTS rows. The 10,000
entry distribution includes substantial solution-NMR/multi-model and hidden
non-protein-context strata; these remain catalog metadata pending the explicit
quality/monomer filter decision. The full 244,406-entry job array is the next
data operation, while coordinate materialization, SI grouping, and ESMC cache
generation remain gated on catalog acceptance.

The monomer training view is now structurally frozen: choose a biological
assembly with exactly one generated protein chain instance, zero generated
nucleic-acid/other-polymer chain instances, a primary X-ray/EM/neutron method,
one coordinate model, and a 20--1024 residue protein construct. Water, ions,
and small molecules remain allowed in `monomer_clean`; zero-small-molecule
records are marked as the `monomer_apo_like` subset. Resolution and coordinate
completeness thresholds remain pending the full catalog and Stage B audit.
