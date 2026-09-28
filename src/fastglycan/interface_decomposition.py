"""Fixed-graph complete conditioning cut and auditable secant projections."""
from __future__ import annotations
import torch

CONDITIONING_NAMES = ('s_inputs', 's', 'z')
CHEMISTRY_NAMES = ('ref_pos', 'ref_charge', 'ref_mask', 'ref_element', 'ref_atom_name_chars')
INTERFACE_NAMES = CONDITIONING_NAMES + CHEMISTRY_NAMES


def make_interface(conditioning, features):
    return dict(zip(CONDITIONING_NAMES, conditioning)) | {k: features[k] for k in CHEMISTRY_NAMES}


def rebuild_features(fixed_features, interface):
    # Raw chemical fields cross the cut once. d_lm is rebuilt downstream, not
    # treated as an extra independent interface variable.
    from .models.differentiable_mini import prepare_atom_pairs
    return prepare_atom_pairs(dict(fixed_features) | {k: interface[k] for k in CHEMISTRY_NAMES})


def detached_interface(interface):
    # detach preserves storage/layout; cloning a packed view could change replay.
    return {k: interface[k].detach().requires_grad_(True) for k in INTERFACE_NAMES}


def dot64(left, right):
    return (left.double() * right.double()).sum()


def decompose_response(analytic, projected_interface, projected_coordinates):
    upstream = projected_interface - analytic
    downstream = projected_coordinates - projected_interface
    return dict(a=analytic, m=projected_interface, d=projected_coordinates,
                upstream_deviation=upstream, downstream_deviation=downstream,
                total_deviation=projected_coordinates-analytic,
                identity_residual=(projected_coordinates-analytic)-(upstream+downstream))


def analytic_embedding_tangent(q, direction, weights):
    p = q.softmax(-1)
    pdot = p * (direction - (p * direction).sum(-1, keepdim=True))
    return pdot @ weights
