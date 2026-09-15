# Sequence Identity Split Protocol v1

Status: method and v1 split manifests generated on the quality-filtered Stage B
corpus.

## Authoritative SI calculator

Strict 100% sequence identity is calculated with Biopython
`Bio.Align.PairwiseAligner` in `global` mode. The scoring policy is symmetric:

```text
match    = +1
mismatch = -1
gap open = -1
gap extend = -1
```

The reported identity is the number of identical residue-residue alignment
columns divided by all global alignment columns, including gap columns. An
insertion, deletion, or residue substitution therefore cannot enter a 100%
identity group. Empty sequences are invalid split keys. The implementation is
`onestepfold.data.sequence_identity.calculate_pairwise_identity`.

`Bio.Align.PairwiseAligner` is used instead of the deprecated `pairwise2`
interface. The Biopython version is recorded with the split manifest.

For the separate near-homology audit, identity is calculated among aligned
residue-residue columns, with shorter-sequence coverage and a minimum of 50
aligned residues. That audit uses a distinct global scoring policy (match +2,
mismatch -1, gap open -8, gap extend -1) so unrelated sequences cannot be
represented as many tiny gap-separated motif matches. The exact-100% manifest
continues to use the strict scoring policy above.

## Scaling and CPU execution

The identity criterion remains pairwise even when the implementation uses
parallel workers. An exact SHA256 digest of the normalized full sequence is a
lossless candidate index: only records in the same digest bucket can satisfy
100% identity. Every bucket is still verified with the Biopython calculator
against a deterministic representative. This removes unrelated comparisons
without changing the strict criterion; it does not perform near-identity
clustering.

For the complete run, partition digest buckets across CPU job-array workers,
write sorted per-worker manifests, and merge them by representative ID. Record
worker count, Biopython version, sequence normalization version, and the input
catalog checksum. A rerun with the same inputs must produce the same group
membership and manifest checksum.

## Leakage rule

Exact-sequence groups are assigned atomically to one split. Near-identical
sequences, engineered constructs, and small mutations remain eligible records
and are not removed by this policy. The 100% SI grouping itself does not claim
family-level separation; any stricter homology boundary is a separate analysis.

## v1 generated views

The quality-filtered exact groups contain 38,400 groups. The 2021-09-30 initial
release cutoff gives 31,689 train-seen groups (59,959 pre-cutoff records) and
6,711 unseen temporal test groups (12,940 post-cutoff records). Later records
whose exact group has a valid pre-cutoff member are written to
`post_cutoff_same_sequence` (932 groups, 5,360 records), not to test.

The strict low-homology audit compares every temporal test group with all
31,689 train groups. With residue identity <30%, shorter-sequence coverage
>=70%, and >=50 aligned residues, 15 groups (18 records) pass. The full
temporal test remains the primary held-out view; the low-homology subset is a
small additional stress test rather than a replacement for it.
