"""Transport an observed candidate response along a reference recycle trajectory.

Only candidate cycle1 and reference cycle1/cycle3 are prediction inputs.
Candidate cycle3/4 are never accepted by the transport function.
"""
import numpy as np
import torch

from fastglycan.models.compensated_recycle import native_recycle_step
from fastglycan.models.prefix_recycle import capture_rng_state, restore_rng_state


def transfer_reference_progress(candidate1, reference1, reference3):
    """WT3 + (Mut1 - WT1), with exact no-edit cancellation and no in-place writes."""
    if any(len(state) != 2 for state in (candidate1, reference1, reference3)):
        raise ValueError('recycle state must contain single and pair')
    result = []
    for candidate, first, third in zip(candidate1, reference1, reference3):
        if (candidate.shape != first.shape or candidate.shape != third.shape
                or candidate.dtype != first.dtype or candidate.dtype != third.dtype
                or candidate.device != first.device or candidate.device != third.device):
            raise ValueError('aligned state shape/dtype/device required')
        if not all(torch.isfinite(x).all() for x in (candidate, first, third)):
            raise ValueError('nonfinite recycle state')
        result.append(third + (candidate - first))
    return tuple(result)


def same_rng(first, second):
    """Compare all saved RNG families, including the selected device's state."""
    if isinstance(first, torch.Tensor):
        return isinstance(second, torch.Tensor) and torch.equal(first, second)
    if isinstance(first, np.ndarray):
        return isinstance(second, np.ndarray) and np.array_equal(first, second)
    if isinstance(first, dict):
        return (isinstance(second, dict) and first.keys() == second.keys()
                and all(same_rng(first[k], second[k]) for k in first))
    if isinstance(first, (tuple, list)):
        return (type(first) is type(second) and len(first) == len(second)
                and all(same_rng(a, b) for a, b in zip(first, second)))
    return first == second


def capture_recycle_trajectory(model, features, initialization, initial_rng):
    """Audit/label construction: four exact steps with cycle states and RNGs.

This performs four candidate updates, so it is not the accelerated inference
implementation. Ambient execution RNG is restored even on failure.
"""
    ambient = capture_rng_state()
    states, rngs = {}, {}
    try:
        restore_rng_state(initial_rng)
        state = (torch.zeros_like(initialization.single),
                 torch.zeros_like(initialization.pair))
        for cycle in range(1, 5):
            state = native_recycle_step(model, features, initialization, state)
            states[cycle] = tuple(x.detach().clone() for x in state)
            rngs[cycle] = capture_rng_state()
        return states, rngs
    finally:
        restore_rng_state(ambient)


def finish_transferred_candidate(model, features, initialization, candidate1,
                                 reference1, reference3, reference_rng3):
    """One candidate update after transport; uses reference RNG, never target3 RNG."""
    predicted3 = transfer_reference_progress(candidate1, reference1, reference3)
    ambient = capture_rng_state()
    try:
        final = native_recycle_step(model, features, initialization, predicted3,
                                    rng=reference_rng3)
        return predicted3, final
    finally:
        restore_rng_state(ambient)
