"""Bounded nearest-coordinate diagnostic on the existing chemical manifold.

This does not define a differentiable solver layer or enforce chain connections.
The frozen constructor and joint geometry solver are not modified.
"""
from dataclasses import dataclass

import torch

from .anchored_geometry import PoseVariables


@dataclass
class LocalProjectionFit:
    initial: torch.Tensor
    coordinates: torch.Tensor
    values: tuple[torch.Tensor, ...]
    initial_mse: float
    final_mse: float
    closure_calls: int
    iterations: int
    final_gradient_norm: float
    improved: bool


def fit_local_projection(adapter, raw, *, max_iter=60, max_eval=90):
    """Fit all native atoms to raw, with one fixed-start L-BFGS solve.

    Input coordinates are the model prediction, never experimental labels.
    All atoms have equal weight. Optimized variables are independent residue
    proper poses and the existing bond-bridge rotations; local lengths, angles,
    ring geometry and handedness therefore remain those of the constructor.
    Final iterate is returned even if it is worse; no best-iterate selection or
    fallback output hides a failed solve. Caller must examine the diagnostics.
    """
    if raw.ndim != 2 or raw.shape != (adapter.atom_count, 3):
        raise ValueError('Expected one complete native atom coordinate array')
    if not torch.isfinite(raw).all():
        raise ValueError('Nonfinite input coordinates')
    if max_iter < 1 or max_eval < max_iter:
        raise ValueError('Require positive iteration budget and max_eval >= max_iter')
    target = raw.detach().clone()
    variables = PoseVariables(adapter, target)
    initial = variables.initial.detach().clone()
    initial_mse = float((initial - target).square().sum(-1).mean())
    optimizer = torch.optim.LBFGS(
        variables.parameters(), lr=1., max_iter=max_iter, max_eval=max_eval,
        history_size=20, line_search_fn='strong_wolfe',
        tolerance_grad=1e-8, tolerance_change=1e-12,
    )
    calls = 0

    def closure():
        nonlocal calls
        optimizer.zero_grad()
        loss = (variables() - target).square().sum(-1).mean()
        if not torch.isfinite(loss):
            raise FloatingPointError('Nonfinite local-fit objective')
        loss.backward()
        if any(p.grad is None or not torch.isfinite(p.grad).all() for p in variables.parameters()):
            raise FloatingPointError('Nonfinite or missing local-fit gradient')
        calls += 1
        return loss

    optimizer.step(closure)
    final = variables()
    loss = (final - target).square().sum(-1).mean()
    gradients = torch.autograd.grad(loss, tuple(variables.parameters()))
    if not torch.isfinite(final).all() or not all(torch.isfinite(g).all() for g in gradients):
        raise FloatingPointError('Nonfinite final local-fit state')
    gradient_norm = float(torch.cat([g.flatten() for g in gradients]).norm())
    final_mse = float(loss.detach())
    state = optimizer.state[next(variables.parameters())]
    return LocalProjectionFit(
        initial=initial, coordinates=final.detach(),
        values=tuple(p.detach().clone() for p in variables.parameters()),
        initial_mse=initial_mse, final_mse=final_mse, closure_calls=calls,
        iterations=int(state.get('n_iter', 0)), final_gradient_norm=gradient_norm,
        improved=final_mse < initial_mse,
    )
