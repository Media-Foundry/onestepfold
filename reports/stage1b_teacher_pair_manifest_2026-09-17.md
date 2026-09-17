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

## hpc3 training mirror

Per the compute policy for the next stage, training uses hpc3 exclusively. The
accepted teacher corpus was copied without transient `work` directories to
`/data/user/shuang886/Folding/stage1b/teacher_pairs_v3`. The destination has
64,094 files and 7,608,200,910 bytes, and its relative-path/size digest matches
DiamondHill. A local hpc3 validator found all 16,000 c2 and 16,000 c4
predictions.

The existing hpc3 ESMC-600M cache was reused rather than recomputed. Its
38,400-row manifest covers all 16,000 teacher groups with zero missing groups,
missing shards, or sequence-length mismatches. A joint read smoke loaded a
517-residue teacher pair, 4,070 aligned atoms, and a finite `[517,1152]` BF16
ESMC slice. The durable hpc3 acceptance record is
`output_diamondhill/control/hpc3_training_data_acceptance.json`; the pass marker
is `hpc3_training_data.PASSED`.
