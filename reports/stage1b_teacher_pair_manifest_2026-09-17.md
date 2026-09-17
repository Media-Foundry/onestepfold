# Stage 1B teacher-pair manifest acceptance

Date: 2026-09-17

The accepted DiamondHill c2/c4 corpus is frozen as
`teacher_pair_manifest_v1`. Its 16,000 records are already one-per-exact-
sequence-group and come only from the pre-cutoff teacher-selection pool. A
seeded SHA256 rank over group IDs assigns exactly 14,400 groups to training and
1,600 to validation. This split does not read or modify the frozen temporal
test.

The manifest preserves mixed-backend provenance: c2 contains 12,030 hpc2
records and 3,970 hpc3 records, while all 16,000 c4 records come from
DiamondHill. Artifact integrity was established separately by the accepted
pair-presence and deep-QA files; mixed-backend acceptance is not a claim of
numerical equivalence.

The training loader was then run exhaustively over all 16,000 pairs on
DiamondHill. It verified the sequence declared by each manifest row, parsed
both CIF files, required identical c2/c4 atom keys, retained explicit backbone
masks without imputation, and checked the c2/c4 recycle counts. All records
passed. The loader aligned 37,321,433 atoms and found zero missing N/CA/C/O
backbone atoms in either setting.

The frozen data artifacts live below
`/media/PM982/onestepfold/stage1b/teacher_pairs_v3/output_diamondhill/control`:

- `teacher_pair_manifest_v1.jsonl.gz`, SHA256
  `084fbc88f8302eb770a021e593ff94b47a76e48cc38b079c96f00c58e7188325`
- `teacher_pair_manifest_v1.summary.json`, SHA256
  `619de7418decb4330281ece5669da54fb9bf373890f460f9c445b1d412dd79ac`
- `teacher_pair_manifest_v1.loader_qa.json`, SHA256
  `8b3f2d542261f3d8a5fcc3f7412c36ebae35a9ddc0f24a7e420eba9bb0ac8a71`

This acceptance establishes a reproducible coordinate-refiner input contract.
It does not establish thermodynamic truth, model quality, or backend
equivalence; those require calibrated held-out evaluation.
