"""Train the native pair suffix relative to its own WT reference execution."""
from dataclasses import dataclass, replace

import torch

from fastglycan.models.stage_pair_recovery import StagePairRecovery


def _reference_signature(pair):
    return (pair.data_ptr(), pair._version, tuple(pair.shape), pair.device, pair.dtype)


@dataclass(frozen=True)
class ReferencePairAnchor:
    drift: torch.Tensor
    position: int
    original: int
    owner: int
    parameter_versions: tuple
    reference_signature: tuple
    drift_version: int


class ReferenceAnchoredPairRecovery(StagePairRecovery):
    """A shared WT branch removes the trainable function's WT drift.

    The anchor uses reference inputs and reference states only. Candidate
    conditioning retains its own inputs/single. Fixed-parameter AA-centered
    predictions are unchanged in real arithmetic; this is a training-graph
    intervention, not a postprocessing claim of AA-response recovery.
    """

    def prepare_reference(self, base, boundary, reference_pair, position, original):
        result, _ = self.run_pair_suffix(base, boundary, reference_pair,
                                         position, original, original)
        drift = result[2] - base[2]
        return ReferencePairAnchor(drift, position, original, id(self),
            tuple(p._version for p in self.parameters()),
            _reference_signature(reference_pair), drift._version)

    def forward(self, base, boundary, reference_pair, position, old, target, *, anchor):
        if old == target:
            return base
        if (anchor.owner != id(self) or anchor.position != position or anchor.original != old
                or anchor.parameter_versions != tuple(p._version for p in self.parameters())
                or anchor.reference_signature != _reference_signature(reference_pair)
                or anchor.drift_version != anchor.drift._version):
            raise ValueError('stale, mutated or unrelated reference anchor')
        if anchor.drift.shape != base[2].shape:
            raise ValueError('reference/candidate shape mismatch')
        result, _ = super().forward(base, boundary, reference_pair, position, old, target)
        return (result[0], result[1], result[2] - anchor.drift)


def reference_gradient_proxy(anchor):
    """Accumulate all candidate gradients into one reference-branch pullback.

    This saves retaining/replaying the reference graph for each candidate.
    Call backward_reference_proxy exactly once after all candidate backwards,
    before clipping or stepping. Detaching without that pullback is incorrect.
    """
    if not anchor.drift.requires_grad:
        raise ValueError('reference must have a live gradient graph')
    leaf = anchor.drift.detach().clone().requires_grad_(True)
    return replace(anchor, drift=leaf, drift_version=leaf._version)


def backward_reference_proxy(anchor, proxy):
    if (anchor.owner != proxy.owner or anchor.parameter_versions != proxy.parameter_versions
            or proxy.drift.grad is None or not proxy.drift.is_leaf):
        raise ValueError('missing or incompatible reference gradient')
    anchor.drift.backward(proxy.drift.grad)
