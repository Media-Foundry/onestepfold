# Sequence Identity Split Protocol v1

Status: method frozen; no train/validation/test partition has been generated.

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
