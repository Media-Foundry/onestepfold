# ESMC cache v1

The first sequence-conditioner artifact is a residue-aligned ESMC-600M cache
for the 38,400 quality-valid exact-sequence groups in
`splits_v1/groups.jsonl.gz`. The cache is representation data, not a structure
teacher: its only input is the PDB-derived construct sequence and its revision
is recorded in every manifest.

## Pinned contract

- model: `biohub/ESMC-600M`
- Hugging Face revision: `28aed46fcaf217dfa59f78a589bb449aa3ae5d98`
- Biohub/esm revision: `bf343ba264b650dff7a073643725f9aaa1fdbe8d`
- sequence context: v1 groups, length 20--1024, ASCII amino-acid tokens
- special tokens: exactly one BOS and EOS are removed; the resulting length
  must equal the construct sequence length
- storage dtype: `bfloat16`
- storage format: sharded safetensors, with a JSONL manifest and feature spec

The all-layer probe stores stacked ESMC hidden states as separate feature arrays
(`layer_00` through `layer_36`). The full cache is deferred until the probe
chooses between `final`, `layers_12_24_36`, and a learned scalar mix. The
all-layer cache is deliberately a larger diagnostic artifact.

## Identity and QA

Every row is keyed by `sequence_sha256`, model ID, both pinned revisions, and
feature variant. The builder sorts groups by `group_id`, checks finite residue
tensors, verifies residue lengths and hidden dimensions, and records a SHA256
checksum for each safetensors shard. The cache universe is split-independent:
train and temporal-test groups are stored together so future split revisions do
not require recomputation.

The ESMC pretraining corpus is not structure-label clean by construction. The
PDB release cutoff therefore describes coordinate-label separation only; any
sequence-pretraining overlap is a separate, explicitly reported risk.
