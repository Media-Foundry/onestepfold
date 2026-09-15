"""Biopython-based pairwise sequence-identity policy for split generation.

The 100% identity policy is deliberately stricter than a substring or
coverage match: global alignment columns, including gap columns, are included
in the denominator. Exact sequence digests can be used to index candidates,
but this module remains the authoritative identity calculator.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class PairwiseIdentity:
    """Summary of one global pairwise alignment."""

    matches: int
    alignment_length: int
    gap_columns: int
    first_length: int
    second_length: int
    aligned_residue_count: int

    @property
    def identity(self) -> float:
        if self.alignment_length <= 0:
            return 0.0
        return self.matches / self.alignment_length

    @property
    def alignment_identity(self) -> float:
        """Identity among all global alignment columns, including gaps."""
        return self.identity

    @property
    def residue_identity(self) -> float:
        """Identity among aligned residue-residue columns only."""
        if self.aligned_residue_count <= 0:
            return 0.0
        return self.matches / self.aligned_residue_count

    @property
    def shorter_sequence_coverage(self) -> float:
        """Fraction of the shorter sequence aligned to residues in the other."""
        shorter = min(self.first_length, self.second_length)
        return self.aligned_residue_count / shorter if shorter else 0.0

    @property
    def full_length_identity(self) -> float:
        """Identical residue count normalized by the longer input sequence."""
        longer = max(self.first_length, self.second_length)
        return self.matches / longer if longer else 0.0


def _new_aligner():
    try:
        from Bio.Align import PairwiseAligner
    except ImportError as exc:  # pragma: no cover - depends on optional split extra
        raise RuntimeError(
            "sequence-identity grouping requires the 'biopython' package"
        ) from exc
    aligner = PairwiseAligner()
    aligner.mode = "global"
    # A simple symmetric scoring policy makes the identity denominator explicit.
    aligner.match_score = 1.0
    aligner.mismatch_score = -1.0
    aligner.open_gap_score = -1.0
    aligner.extend_gap_score = -1.0
    return aligner


def _new_homology_aligner():
    """Build a global aligner whose gap cost does not create motif-only hits."""
    aligner = _new_aligner()
    aligner.match_score = 2.0
    aligner.mismatch_score = -1.0
    aligner.open_gap_score = -8.0
    aligner.extend_gap_score = -1.0
    return aligner


def calculate_pairwise_identity(
    first: str,
    second: str,
    *,
    aligner=None,
) -> PairwiseIdentity:
    """Calculate identity from a Biopython global alignment.

    ``first`` and ``second`` are expected to be already normalized PDB
    construct sequences. Empty sequences are rejected because they cannot be
    valid protein-chain split keys.
    """
    if not first or not second:
        raise ValueError("pairwise identity requires non-empty sequences")
    aligner = aligner or _new_aligner()
    alignment = aligner.align(first, second)[0]
    coordinates = alignment.coordinates
    matches = alignment_length = gap_columns = aligned_residue_count = 0
    for column in range(1, len(coordinates[0])):
        first_start = int(coordinates[0, column - 1])
        first_end = int(coordinates[0, column])
        second_start = int(coordinates[1, column - 1])
        second_end = int(coordinates[1, column])
        first_step = first_end - first_start
        second_step = second_end - second_start
        if first_step and second_step:
            if first_step != second_step:
                raise ValueError("unexpected non-unit pairwise alignment segment")
            matches += sum(
                left == right
                for left, right in zip(
                    first[first_start:first_end],
                    second[second_start:second_end],
                    strict=True,
                )
            )
            alignment_length += first_step
            aligned_residue_count += first_step
        elif first_step:
            alignment_length += first_step
            gap_columns += first_step
        elif second_step:
            alignment_length += second_step
            gap_columns += second_step
    return PairwiseIdentity(
        matches,
        alignment_length,
        gap_columns,
        len(first),
        len(second),
        aligned_residue_count,
    )


def exact_sequence_digest(sequence: str) -> str:
    """Return a stable digest used only as a lossless candidate index."""
    if not sequence:
        raise ValueError("sequence digest requires a non-empty sequence")
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


def group_exact_identity(
    records: Mapping[str, str],
    *,
    verify_pairwise: bool = True,
) -> dict[str, tuple[str, ...]]:
    """Group record IDs by strict 100% identity.

    The digest index avoids comparing unrelated sequences. Within each digest
    bucket, Biopython pairwise identity is optionally verified for every record
    against the deterministic first representative. Since the digest is over
    the full normalized sequence, this optimization cannot merge distinct
    sequences unless SHA-256 collides.
    """
    buckets: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for record_id, sequence in records.items():
        buckets[exact_sequence_digest(sequence)].append((record_id, sequence))
    groups: dict[str, tuple[str, ...]] = {}
    for digest, bucket in sorted(buckets.items()):
        ordered = sorted(bucket, key=lambda item: item[0])
        representative_id, representative_sequence = ordered[0]
        if verify_pairwise:
            for _, sequence in ordered[1:]:
                result = calculate_pairwise_identity(representative_sequence, sequence)
                if result.identity != 1.0 or result.gap_columns:
                    raise ValueError(f"digest bucket {digest} failed 100% pairwise verification")
        groups[representative_id] = tuple(record_id for record_id, _ in ordered)
    return groups


__all__ = [
    "PairwiseIdentity",
    "calculate_pairwise_identity",
    "exact_sequence_digest",
    "group_exact_identity",
]
