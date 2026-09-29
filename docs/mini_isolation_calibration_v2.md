# Sequence isolation v2: predeclared BLAST calibration

2026-09-30. Geometry remains frozen at `2aa87043`; v1 screening and its zero-selected
result stay immutable. This is a new sequence-only calibration, before any new
folding/repair outputs. Do not optimize isolation thresholds to obtain32 candidates.

Use NCBI BLAST+2.17.0 downloaded from the official archive, verify distributed MD5
and record SHA256/executable versions. Local install only. Protein search: task
blastp, word_size3, BLOSUM62, gapopen11/gapextend1, SEG=yes, comp_based_stats=2,
evalue=.001, max_target_seqs=database record count, no max_hsps truncation.
Archive qseq/sseq, lengths, coordinates, identity, score and E-value. Database is
the same21,070 development references; no public remote search or GT coordinates.

The new operational exclusion rule is either:

1. HSP E<=.001, >=50 residue-residue aligned columns, identity>=.30 among those
   columns, and residue-residue columns/min(full query length,full subject length)
   >=.70; or
2. HSP E<=1e-5 and >=50 residue-residue aligned columns, regardless of coverage or
   identity (conservative significant-domain safeguard).

Compute columns explicitly from gapped qseq/sseq, not by counting gap columns or
using query-only coverage. Rule2 can exclude strong local family/domain similarity
missed by whole-chain coverage. This is a defined search-based isolation policy,
not proof of evolutionary independence or absence of all remote homology.

## Calibration, frozen before search

From development references, select eight hash-ranked parents in each length bin
50–127,128–255,256–511,512–1024. For each parent create exact, central80% crop
(at least50 residues),20% substitutions at sampled positions to a different residue,
and60% substitutions (diagnostic sensitivity only). Also create ten independently
shuffled copies preserving composition and length. All deterministic seeds use
SHA256 tags prefixed `isolation-v2:20260930:`; store all actual sequences.

Include up to32 distinct-accession natural positive pairs: two distinct historical
development constructs mapped to a PDB with only one SIFTS accession, old global
alignment identity>=80%, shorter coverage>=90%, length ratio>=.8. Pick by fixed hash
order. Their intended reference must exist in the database; score recovery of that
reference specifically, not a different/self hit. Report available pair count.

Gate: recover all exact and crop intended parents, >=31/32 mutation20 parents,
and all natural intended parents (require >=16 natural pairs); at most3/320 shuffled
queries may meet the exclusion rule against any reference. Mutation60 is reported
without a pass threshold; no claim of certified detection at30% identity. Calibration
is a small engineering check; sequence shuffling is not a natural nonhomolog panel.
If this gate fails, stop without changing parameters in this version.

If it passes, apply the same fixed rule to the archived217 candidate pool, preserving
all earlier PDB/accession/source filters, hash order and length strata. Also perform
an all-versus-all candidate search and exclude a pair if either search direction
meets the rule; use `-dbsize` equal to the development database residue count for
this small-database search so E-values use the same reference search-space length.
Retain one shared-accession representative. Select first8 per stratum.
If fewer than8 remain in any stratum, stop; no pool extension or threshold change.
The resulting list is provisional until native chemical scope checks. Reserve it
from future correction training; no geometry inference before a separate immutable
input/runtime lock. Future isolation against reserved sequences must reuse this rule.

BLAST is heuristic; calibration does not establish exhaustive homology recall.
No candidate quality metrics enter this stage. Geometric validation protocol and
stopping criteria remain those in `mini_anchored_independent_v1.md`; only this
explicitly versioned sequence-isolation component differs.

Primary documentation: [NCBI BLAST+ options](https://www.ncbi.nlm.nih.gov/books/NBK279684/)
and [custom tabular outputs](https://www.ncbi.nlm.nih.gov/books/NBK569862/).
