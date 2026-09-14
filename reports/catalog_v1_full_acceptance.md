# Full Stage A Catalog Acceptance

Date: 2026-09-15

This report records the first complete Stage A scan of the fixed SIFTS-linked
entry universe. It is a catalog and eligibility report, not a processed
coordinate GT release: no Stage B atom materialization, quality threshold, or
train/validation/test split is implied here.

## Acceptance

| Check | Result |
| --- | ---: |
| finalized catalog shards | 256 / 256 |
| catalog entries | 244,406 |
| unique PDB IDs | 244,406 |
| duplicate PDB IDs | 0 |
| non-empty scanner error files | 0 |
| unresolved SIFTS rows | 0 |
| missing assembly composition | 0 |
| partial `.part` files | 0 |

The catalog is stored on hpc2 at
`/hpc2hdd/home/shuang886/Folding/catalog_v1`. The aggregate SHA256 over the
sorted shard checksum listing is:

```text
8e62a4bdf1ee1ba4967e7b35fb2f3fd7f2de067055dbde9d81f10a113d581cf0
```

The run used scanner commit `9275c5e` and the pinned Gemmi/SIFTS raw snapshot
described in the project memory. The per-shard error files are retained for
audit even though all are empty.

## Full-catalog distributions

Experimental method counts are metadata occurrences and are not forced to be
mutually exclusive when an entry records more than one method.

| Method | Entries |
| --- | ---: |
| X-RAY DIFFRACTION | 196,806 |
| ELECTRON MICROSCOPY | 34,884 |
| SOLUTION NMR | 12,127 |
| NEUTRON DIFFRACTION | 248 |
| ELECTRON CRYSTALLOGRAPHY | 261 |
| SOLID-STATE NMR | 185 |
| SOLUTION SCATTERING | 72 |
| FIBER DIFFRACTION | 29 |
| POWDER DIFFRACTION | 20 |
| EPR | 8 |
| THEORETICAL MODEL | 6 |
| INFRARED SPECTROSCOPY | 4 |

Resolution quantiles over the 232,062 entries with a reported resolution are:

```text
p05 1.33 A   p25 1.80 A   p50 2.15 A   p75 2.70 A   p95 3.70 A
```

There are 12,344 entries without a reported resolution. Across protein chains,
sequence-length quantiles are:

```text
p05 48 aa   p25 130 aa   p50 225 aa   p75 368 aa   p95 743 aa
```

Non-protein context is common in the raw catalog: water occurs in 186,260
entries, small molecules in 167,047, ions in 94,487, nucleic-acid atoms in
16,537, and other non-protein atoms in 14,391. These are retained as metadata;
the first model input remains protein sequence only.

## Monomer candidate view

The frozen catalog-only policy selects a biological assembly with exactly one
generated protein chain instance, zero generated nucleic-acid/other-polymer
instances, a primary X-ray/EM/neutron method, one coordinate model, and a
20--1024 residue construct. Water, ions, and small molecules are allowed in
`monomer_clean`; zero-small-molecule records are marked `monomer_apo_like`.

| Classification | Entries |
| --- | ---: |
| `monomer_clean` | 84,232 |
| `contextual` | 5,448 |
| `auxiliary` | 9,971 |
| `ineligible` | 144,755 |

The candidate table has no duplicate PDB IDs. Of the 84,232 clean candidates,
18,427 are eligible for the apo-like subset. Initial-release date counts are:

| Release bucket | Entries |
| --- | ---: |
| `<= 2021-09-30` | 64,674 |
| `> 2021-09-30` | 19,558 |
| missing | 0 |

Candidate sequence-length quantiles are:

```text
p05 112 aa   p25 175 aa   p50 283 aa   p75 382 aa   p95 628 aa
```

Candidate resolution quantiles (one candidate lacks a resolution) are:

```text
p05 1.17 A   p25 1.60 A   p50 1.90 A   p75 2.295 A   p95 2.913 A
```

Candidate method metadata occurrences are X-ray 83,132, electron microscopy
1,039, neutron 160, EPR 5, solution NMR 2, and solution scattering 4. The
small non-primary method occurrences reflect entries whose metadata contains a
primary method as well; the selector itself requires an intersection with the
primary method set.

## Strict 100% SI manifest

The candidate table was processed with Biopython `Bio.Align.PairwiseAligner`
1.87 in global mode using match `+1`, mismatch `-1`, gap-open `-1`, and
gap-extend `-1`. Exact sequence SHA256 was used only as a lossless candidate
index; every non-singleton bucket was verified by the pairwise calculator.

```text
candidate records             84,232
100% identity groups          41,592
duplicate records in groups   42,640
pairwise verifications        42,640
```

The manifest and summary are:

```text
/hpc2hdd/home/shuang886/Folding/catalog_v1/sequence_identity_100_manifest.jsonl.gz
/hpc2hdd/home/shuang886/Folding/catalog_v1/sequence_identity_100_summary.json
```

This is an exact-sequence grouping artifact, not yet a homology-level split.
Near-identical constructs and engineered/small-variation records remain
available. A later split stage must assign each exact group atomically and
must keep all derived coordinate views for a PDB together.

## Next gate

The next operation is Stage B multi-chain-aware coordinate materialization on a
small audit set (5k--10k candidates), followed by residue/backbone/heavy-atom
coverage and geometry QA. Numeric resolution/completeness thresholds remain
deferred until that audit. ESMC embedding cache generation remains after the GT
schema and quality branch are accepted.
