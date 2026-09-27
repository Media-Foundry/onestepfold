"""Observed experimental supervision in proper local backbone frames.

All neighbor indices and target coordinates in this module are labels, never
model inputs. Chemical inventory, atom identities and missing masks are unchanged.
"""
from __future__ import annotations

import hashlib

import numpy as np
import torch
from scipy.spatial import cKDTree


def backbone_frames(coordinate, atom_indices, *, epsilon=1e-4):
    """CA origin, C-directed first axis, N-plane second axis, proper cross axis.

    Epsilon bounds inverse vector lengths for degenerate predictions. Such a
    stabilized degenerate frame is not claimed to be an orthonormal frame.
    """
    n, ca, c = coordinate[atom_indices].unbind(dim=1)
    e1 = c - ca
    e1 = e1 / torch.linalg.vector_norm(e1, dim=-1, keepdim=True).clamp_min(epsilon)
    e2 = n - ca
    e2 = e2 - (e2 * e1).sum(-1, keepdim=True) * e1
    e2 = e2 / torch.linalg.vector_norm(e2, dim=-1, keepdim=True).clamp_min(epsilon)
    e3 = torch.linalg.cross(e1, e2, dim=-1)
    return ca, torch.stack((e1, e2, e3), dim=-2)


def build_frame_labels(labels, inventory, *, radius=15.0, epsilon=1e-4):
    """CPU preparation of observed N/CA/C frames and nearby observed atom targets.

    Frames with absent or degenerate GT anchors are excluded. Each retained
    frame supervises observed atoms within radius of its GT CA, except that CA
    itself (which would always have zero local coordinates). Atom names are fixed.
    """
    coordinate = labels["coordinate"].detach().cpu().double()
    mask = labels["coordinate_mask"].detach().cpu()
    if coordinate.ndim != 2 or coordinate.shape[-1] != 3:
        raise ValueError("expected [atom,3] label coordinates")
    if mask.dtype != torch.bool or mask.shape != coordinate.shape[:1]:
        raise ValueError("invalid observed mask")
    if not torch.isfinite(coordinate[mask]).all() or not 0 < epsilon < radius:
        raise ValueError("invalid observed coordinates or frame scale")
    names, residues = np.asarray(inventory["atom_name"]), np.asarray(inventory["residue_id"])
    if names.shape != residues.shape or names.shape != (len(coordinate),):
        raise ValueError("inventory shape mismatch")
    if not np.issubdtype(residues.dtype, np.integer) or np.any(residues < 1):
        raise ValueError("residue IDs must be positive integers")
    lookup = {(int(r), str(n)): i for i, (r, n) in enumerate(zip(residues, names, strict=True))}
    if len(lookup) != len(names):
        raise ValueError("duplicate atom identity")
    frames = []
    for residue in np.unique(residues):
        keys = [(int(residue), n) for n in ("N", "CA", "C")]
        if not all(k in lookup for k in keys):
            continue
        indices = [lookup[k] for k in keys]
        if not mask[indices].all():
            continue
        n, ca, c = coordinate[indices]
        first = c - ca
        norm = first.norm()
        if norm <= epsilon:
            continue
        first = first / norm
        second = n - ca - torch.dot(n - ca, first) * first
        if second.norm() > epsilon:
            frames.append(indices)
    if not frames:
        raise ValueError("no nondegenerate observed backbone frames")
    frame_atoms = torch.tensor(frames, dtype=torch.long)
    origins, axes = backbone_frames(coordinate, frame_atoms, epsilon=epsilon)
    observed = torch.nonzero(mask).flatten().numpy()
    tree = cKDTree(coordinate[mask].numpy())
    frame_rows, points = [], []
    neighborhoods = tree.query_ball_point(origins.numpy(), radius, return_sorted=True)
    for frame, members in enumerate(neighborhoods):
        point = observed[members]
        point = point[point != int(frame_atoms[frame, 1])]
        frame_rows.extend([frame] * len(point))
        points.extend(point.tolist())
    if not points:
        raise ValueError("no observed frame-point pairs")
    frame_rows, points = torch.tensor(frame_rows), torch.tensor(points)
    delta = coordinate[points] - origins[frame_rows]
    local = (axes[frame_rows] * delta[:, None, :]).sum(-1)
    return {"frame_atoms": frame_atoms, "frame_rows": frame_rows, "point_indices": points,
            "target_local": local, "epsilon": float(epsilon), "radius": float(radius),
            "observed_atom_count": int(mask.sum()),
            "excluded_frame_count": len(np.unique(residues)) - len(frames)}


def local_frame_mse(prediction, supervision):
    """Mean squared Euclidean frame-point error in A², no clamping or alignment.

    Proper-frame coordinates remove whole-protein pose and retain handedness.
    Degenerate predicted frames are stabilized rather than silently excluded.
    """
    if prediction.ndim != 2 or prediction.shape[-1] != 3:
        raise ValueError("expected [atom,3] prediction")
    prediction = prediction if prediction.dtype == torch.float64 else prediction.float()
    device = prediction.device
    indices = supervision["frame_atoms"].to(device)
    rows = supervision["frame_rows"].to(device)
    points = supervision["point_indices"].to(device)
    target = supervision["target_local"].to(device=device, dtype=prediction.dtype).detach()
    origins, axes = backbone_frames(prediction, indices, epsilon=supervision["epsilon"])
    delta = prediction[points] - origins[rows]
    local = (axes[rows] * delta[:, None, :]).sum(-1)
    return (local - target).square().sum(-1).mean()


def training_sampler_seed(group_id, epoch, *, repeat=0, base_seed=101):
    """Stateless per-group/epoch sampler RNG, disjoint from low diagnostic seeds."""
    if len(group_id) != 64 or any(c not in "0123456789abcdef" for c in group_id):
        raise ValueError("expected SHA256 group identity")
    if epoch < 1 or repeat < 0:
        raise ValueError("invalid epoch/repeat")
    key = f"esmc-geometry-sampler-v1:{base_seed}:{group_id}:{epoch}:{repeat}".encode()
    value = int.from_bytes(hashlib.sha256(key).digest()[:4], "little")
    return 1_000_000 + value % (2**31 - 1 - 1_000_000)
