# Raw Snapshot Acceptance Report

Status: accepted as the immutable first-version raw input layer. This report
contains the hpc2 snapshot inventory and a bounded sample audit; it is not a
replacement for the full Stage A catalog.

## Scope

The first-version entry universe is the `244,406` SIFTS-linked PDB entries
staged at `/hpc2hdd/home/shuang886/Folding/Dataset` on hpc2. No PDB coordinate
files are committed to this repository.

## Inventory

| Artifact | Count/status |
| --- | ---: |
| compressed PDB mmCIF entries | 244,406 |
| incomplete `.part` PDB files | 0 |
| SIFTS `pdb_chain_uniprot` rows | 1,031,850 |
| SIFTS `uniprot_segments_observed` rows | 1,557,033 |
| unique PDB-chain pairs in SIFTS | 992,086 |
| PDB-chain pairs with multiple accessions | 9,927 |
| mapped UniProt FASTA records | 76,273 |
| FASTA records with empty sequence | 0 |
| full PDB gzip integrity check | passed |

The FASTA accession set exactly matches the accession set in the SIFTS mapping
table. UniProt/SIFTS is retained for provenance; the GT input sequence and
coordinates are extracted from PDB mmCIF.

## Bounded sample audit

The random seed `20260914` was used for the structure sample. In 200 entries,
the observed experimental methods were 165 X-ray, 28 electron microscopy, and
7 solution NMR entries. Protein entity sequence lengths ranged from 11 to
3,159 residues in the sample. A separate 50-entry atom-site audit found 48
single-model entries and 2 multi-model entries.

All 890 sampled SIFTS rows resolved through
`_entity_poly.pdbx_strand_id -> entity_id -> _struct_asym.id`; a direct lookup
of SIFTS `CHAIN` as `_struct_asym.id` is therefore rejected by the protocol.
The sample also contains missing residues/atoms, alternate locations, and
non-protein entities, so these are catalog metadata rather than reasons to
modify the raw layer.

## Current boundary

The raw layer is complete, but no `catalog_v1`, `processed_v1`, split, or ESMC
cache has been generated. The next command is the Stage A Gemmi catalog scan;
quality thresholds, assembly view selection, and PDBFixer-derived branches are
not frozen by this report.
