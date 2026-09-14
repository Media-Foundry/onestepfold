# Stage A Catalog Pilot

Date: 2026-09-14

This is a parser and scanner pilot only. It is not the full 244,406-entry
catalog and it does not create coordinates, splits, or ESMC embeddings.

## Scope

The pilot used three real compressed mmCIF entries from the frozen raw layer:

| PDB ID | Protein chains | Nucleic-acid chains | Assembly protein instances | Method |
| --- | ---: | ---: | ---: | --- |
| `101m` | 1 | 0 | 1 | X-ray |
| `6xu7` | 76 | 7 | 76 | electron microscopy |
| `7wxm` | 1 | 0 | 1 | X-ray |

The scanner read construct sequences and entity/chain metadata from mmCIF.
SIFTS was attached only as provenance. The `6xu7` result exercised the
multi-chain resolver; each sampled SIFTS chain was assigned to its mapped
label asym rather than every asym sharing the same entity.

## Classification and metadata checks

The observed ASU atom summaries were:

| PDB ID | Non-protein atoms | Nucleic acid | Small molecule | Water | Ion |
| --- | ---: | ---: | ---: | ---: | ---: |
| `101m` | 192 | 0 | 54 | 138 | 0 |
| `6xu7` | 124,204 | 124,204 | 0 | 0 | 0 |
| `7wxm` | 276 | 0 | 12 | 263 | 1 |

Deposition, initial-release, and latest-revision dates were present in all
three records. Gemmi generator composition was present for the declared
assembly in all three records. In particular, `6xu7` was counted as 76 protein
and 7 nucleic-acid generated chain instances.

## Reproducibility checks

The same three-entry scan was run twice with the same manifest and two worker
processes. The compressed JSONL SHA256 was identical in both runs:

```text
5197f43699052078689609e6a2b4002c56579a4a1cdf63a6c5b36ce6228dcde7
```

The `--resume` flag skipped the completed output. A three-way deterministic
shard run produced 1, 0, and 2 records with zero errors and three unique PDB
IDs.

## Gate

The three-entry pilot supported proceeding to 1,000-entry and then 10,000-entry
audits. At both larger scales the full scan remained gated on reviewing failure
taxonomy, date coverage, assembly composition outliers, and resolver ambiguity.
No split, coordinate materialization, or ESMC cache should start before the
catalog gate is accepted.

## 1,000-entry throughput pilot

The hardened scanner then processed the first 1,000 entries in sorted raw-file
order using eight workers. It completed in approximately 46 seconds with
`1000/1000` successful records, zero errors, 1,000 unique PDB IDs, zero
unresolved SIFTS rows, and assembly composition present for all entries. All
three date fields were populated for all 1,000 records.

The experimental-method counts were 643 X-ray, 353 electron microscopy, 2
neutron diffraction, 2 solution NMR, and 2 solid-state NMR entries. Exactly one
entry was multi-model in this pilot. The scan produced a stable gzip JSONL
artifact with SHA256:

```text
900b712803f30c255f7dd9f5dfbd9c68c602ee8472594a599032aee55784b96f
```

This establishes a practical full-scan throughput baseline, but it is not a
quality-filter decision. The next action remains a 10,000-entry audit with
failure and composition distribution review before scheduling the full job
array.

## 10,000-entry audit

The next audit processed 10,000 entries with eight workers. It completed with
`10000/10000` successful records, zero errors, 10,000 unique PDB IDs, zero
unresolved SIFTS rows, and full coverage for dates and Gemmi assembly
composition. The compressed JSONL artifact was 4.8 MiB with SHA256:

```text
52a424f6eb7ec079b01e14081aedc3c63f22f676f7fca5822e626a63490a378f
```

Experimental methods included 8,420 X-ray, 1,191 solution-NMR, 365 electron
microscopy, and smaller numbers of electron-crystallography, neutron,
solid-state NMR, diffraction, scattering, infrared, and theoretical-model
records. There were 9,094 single-model entries; the remainder included common
NMR multi-model counts such as 20, 10, and 30 models. Non-protein context was
common: water, small molecules, ions, other non-protein categories, and nucleic
acid atoms appeared in 7,866, 5,875, 3,346, 466, and 389 entries respectively.

This confirms the scanner contract and throughput are ready for a full job
array, subject to a separate decision on quality filters and the monomer
training view. NMR/multi-model and theoretical/scattering records must remain
explicitly stratified rather than silently treated as ordinary single-model
experimental labels.
