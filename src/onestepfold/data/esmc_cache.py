"""Versioned ESMC residue-embedding cache primitives."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ESMCFeatureSpec:
    """Identity of an ESMC feature artifact and its token policy."""

    model_id: str
    hf_revision: str
    code_revision: str
    feature_variant: str
    hidden_dim: int
    num_layers: int
    dtype: str = "bfloat16"
    bos_removed: bool = True
    eos_removed: bool = True

    def __post_init__(self) -> None:
        if not self.hf_revision or self.hf_revision in {"main", "master", "latest"}:
            raise ValueError("ESMC cache requires a pinned Hugging Face revision")
        if not self.code_revision or self.code_revision in {"main", "master", "latest"}:
            raise ValueError("ESMC cache requires a pinned Biohub/esm code revision")
        if self.feature_variant not in {"final", "layers_12_24_36", "all"}:
            raise ValueError(f"unsupported ESMC feature variant: {self.feature_variant}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "hf_revision": self.hf_revision,
            "code_revision": self.code_revision,
            "feature_variant": self.feature_variant,
            "hidden_dim": self.hidden_dim,
            "num_layers": self.num_layers,
            "dtype": self.dtype,
            "bos_removed": self.bos_removed,
            "eos_removed": self.eos_removed,
        }


def sequence_sha256(sequence: str) -> str:
    if not sequence or any(ord(letter) > 127 for letter in sequence):
        raise ValueError("sequence must be a non-empty ASCII string")
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


def strip_special_tokens(hidden: Any, sequence_length: int) -> Any:
    """Strip exactly one BOS and EOS and assert residue alignment.

    ``hidden`` is a tensor with shape ``[tokens, hidden_dim]``. Padding is not
    accepted here: the caller must pass each sequence's unpadded token slice.
    """
    if sequence_length < 1:
        raise ValueError("sequence length must be positive")
    if len(hidden.shape) != 2 or hidden.shape[0] != sequence_length + 2:
        raise ValueError(
            f"expected BOS/EOS token length {sequence_length + 2}, got {tuple(hidden.shape)}"
        )
    residue = hidden[1:-1]
    if residue.shape[0] != sequence_length:
        raise AssertionError("ESMC BOS/EOS stripping changed residue count")
    return residue


def _hidden_state_count(hidden_states: Any) -> int:
    """Return the number of entries in tuple or stacked ESMC hidden states."""
    if hasattr(hidden_states, "ndim") and int(hidden_states.ndim) == 4:
        return int(hidden_states.shape[0])
    return len(hidden_states)


def _hidden_state_at(hidden_states: Any, index: int) -> Any:
    return hidden_states[index]


def select_feature_layers(hidden_states: Any, variant: str) -> dict[str, Any]:
    """Select final, fixed intermediate, or all hidden-state tensors."""
    state_count = _hidden_state_count(hidden_states)
    if state_count == 0:
        raise ValueError("ESMC returned no hidden states")
    if variant == "all":
        return {
            f"layer_{index:02d}": _hidden_state_at(hidden_states, index)
            for index in range(state_count)
        }
    if variant == "final":
        return {"final": _hidden_state_at(hidden_states, state_count - 1)}
    if variant == "layers_12_24_36":
        if state_count >= 37:
            # Current ESMC includes the embedding state at index zero.
            indices = (12, 24, 36)
        elif state_count >= 36:
            # Legacy wrappers may expose transformer outputs only.
            indices = (11, 23, 35)
        else:
            raise ValueError(f"expected at least 36 ESMC layers, got {state_count}")
        return {
            f"layer_{layer_number:02d}": _hidden_state_at(hidden_states, index)
            for layer_number, index in zip((12, 24, 36), indices, strict=True)
        }
    raise ValueError(f"unsupported ESMC feature variant: {variant}")


def assert_finite_residue_tensor(tensor: Any, sequence_length: int) -> None:
    if tuple(tensor.shape[:1]) != (sequence_length,):
        raise ValueError(
            f"residue tensor length {tuple(tensor.shape)} does not match {sequence_length}"
        )
    if not bool(tensor.is_floating_point()):
        raise ValueError("ESMC residue representations must be floating point")
    if not bool(tensor.isfinite().all()):
        raise ValueError("ESMC residue representations contain non-finite values")


__all__ = [
    "ESMCFeatureSpec",
    "assert_finite_residue_tensor",
    "select_feature_layers",
    "sequence_sha256",
    "strip_special_tokens",
]
