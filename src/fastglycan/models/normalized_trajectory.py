"""Candidate-first transport with a fixed, reference-derived coordinate scale."""
import math

import torch

from fastglycan.models.recycle_trajectory import transfer_reference_progress


def normalized_trajectory_transport(candidate1, reference1, reference3, epsilons):
    """Transport channel-standardized differences; no labels or fitted parameters.

Each of s/z has its own native epsilon. The result is anchored on WT3, so a
no-edit candidate is exactly WT3, without a normalizing/reconstruction roundtrip.
This approximation changes cross-depth coordinates, not the native last update.
"""
    if len(epsilons) != 2 or any(not math.isfinite(e) or e <= 0 for e in epsilons):
        raise ValueError('two positive finite native epsilons required')
    # Preserve the established shape/dtype/device/finite-state checks.
    transfer_reference_progress(candidate1, reference1, reference3)
    result = []
    for candidate, first, third, eps in zip(candidate1, reference1, reference3, epsilons):
        if not candidate.is_floating_point():
            raise ValueError('floating-point state required')
        candidate_mean = candidate.mean(dim=-1, keepdim=True)
        first_mean = first.mean(dim=-1, keepdim=True)
        third_mean = third.mean(dim=-1, keepdim=True)
        candidate_scale = ((candidate-candidate_mean).square().mean(dim=-1, keepdim=True)+eps).sqrt()
        first_scale = ((first-first_mean).square().mean(dim=-1, keepdim=True)+eps).sqrt()
        third_scale = ((third-third_mean).square().mean(dim=-1, keepdim=True)+eps).sqrt()
        delta = (candidate-candidate_mean)/candidate_scale - (first-first_mean)/first_scale
        transported = third + third_scale*delta
        if not torch.isfinite(transported).all():
            raise ValueError('nonfinite normalized transport')
        result.append(transported)
    return tuple(result)


def channel_error_decomposition(prediction, target):
    """FP64 channel-mean versus centered-channel error, not across-AA centering."""
    if prediction.shape != target.shape:
        raise ValueError('aligned state shapes required')
    error = prediction.double()-target.double()
    mean = error.mean(-1, keepdim=True)
    total = error.square().mean()
    shared = mean.square().mean()
    centered = (error-mean).square().mean()
    if not torch.allclose(total, shared+centered, rtol=1e-10, atol=1e-20):
        raise AssertionError('channel MSE decomposition failed')
    return dict(mse=float(total), channel_mean_mse=float(shared),
                centered_channel_mse=float(centered),
                channel_mean_fraction=float(shared/total) if total > 1e-24 else None)
