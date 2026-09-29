# Full-source and alternative-record audit v4

2026-09-30. User explicitly requests continuing the search and checking the full
HPC3 dataset. Preserve the28 qualified proteins and all previous exclusions.
No model outputs, repair changes or threshold changes in this source audit.

1. Compare HPC3/DiamondHill catalog and PDB-ID manifests. Inventory full catalog
   coverage; do not call the SIFTS-linked collection all UniProt or all PDB.
2. For pre-2021-10-01 standard512–1024-residue single-model X-ray/EM/neutron
   constructs in the existing monomer catalog, inspect ALL alternative records,
   not only the lowest-resolution representative. Historical development group,
   PDB and SIFTS accession exclusions and retained-panel accession isolation stay
   fixed. A previously examined sequence may have another usable structure; a
   source failure excludes that record, not automatically every identical sequence.
3. Order records per sequence by resolution,PDB,source-chain,assembly. Freeze the
   list before materialization. Use unchanged calibrated BLAST exclusions versus
   all21070 development sequences and symmetric comparisons with retained28.
   Choose the first fully source- and chemistry-qualified variant per group, then
   hash-rank groups with `anchored-variants-v4:20260930:`. First4 pairwise-isolated
   groups fill the remaining slots. No selection on prediction/repair quality.
4. Complete backbone, zero modifications/chain breaks, no SG<2.3A or unsupported
   explicit covalent links; exact original atom37 mapping and repeated raw rebuild;
   same native chemistry preflight. No trimming, imputation or temporal-test CIFs.
5. Also inventory pre-cutoff complete-looking protein chains in the full244406-entry
   catalog, including those outside the monomer subset. This second census is
   source discovery only: record assembly context and do not silently admit an
   oligomer-derived chain into the monomer validation panel. Report separately if
   only this broader source offers candidates.

Native input/GT checking is CPU only.32x3 GPU validation requires completed panel
and runtime locks. Independent here means separate from correction-method development,
not absence from Mini/ESM pretraining. Existing scoring/geometry rules remain frozen.
