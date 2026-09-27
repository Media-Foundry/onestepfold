"""Fixed-graph internal rotations; no target coordinates enter reconstruction."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch


@dataclass(frozen=True)
class BondRotation:
    parent: int
    child: int
    moving: tuple[int, ...]


def bridge_rotations(atom_names, bonds) -> tuple[BondRotation, ...]:
    """Select single-bond bridges away from CA, preserving the N/CA pose axis."""
    names = list(atom_names)
    if len(set(names)) != len(names) or "CA" not in names or "N" not in names:
        raise ValueError("Unique names including N and CA are required")
    n = len(names)
    adjacency = [set() for _ in names]
    edges = []
    seen = set()
    for a, b, order in bonds:
        a, b = int(a), int(b)
        edge = tuple(sorted((a, b)))
        if a == b or min(a, b) < 0 or max(a, b) >= n or edge in seen:
            raise ValueError("Invalid or duplicate chemical bond")
        seen.add(edge)
        edges.append((a, b, order))
        adjacency[a].add(b)
        adjacency[b].add(a)

    def component(start, cut):
        found, pending = {start}, [start]
        while pending:
            a = pending.pop()
            for b in adjacency[a]:
                if frozenset((a, b)) == cut or b in found:
                    continue
                found.add(b)
                pending.append(b)
        return found

    root = names.index("CA")
    if len(component(root, frozenset())) != n:
        raise ValueError("Disconnected chemical inventory")
    distance = {root: 0}
    pending = [root]
    for a in pending:
        for b in sorted(adjacency[a]):
            if b not in distance:
                distance[b] = distance[a] + 1
                pending.append(b)
    result = []
    for a, b, order in edges:
        if order != 1 or {names[a], names[b]} == {"N", "CA"}:
            continue
        side = component(b, frozenset((a, b)))
        if a in side:  # A ring bond is not a bridge.
            continue
        if root in side:
            a, b = b, a
            side = set(range(n)) - side
        if len(side) > 1:
            result.append(BondRotation(a, b, tuple(sorted(side))))
    return tuple(sorted(result, key=lambda r: (distance[r.parent], r.parent, r.child)))


def articulate_reference(reference, angles, rotations):
    """Apply differentiable proper bond-axis rotations in root-to-leaf order."""
    if reference.ndim != 2 or reference.shape[1] != 3:
        raise ValueError("Reference must have shape [atoms, 3]")
    if angles.shape != (len(rotations),):
        raise ValueError("Exactly one angle per selected bond is required")
    if not torch.isfinite(reference).all() or not torch.isfinite(angles).all():
        raise ValueError("Nonfinite reference or angle")
    x = reference
    for angle, rotation in zip(angles, rotations, strict=True):
        origin = x[rotation.parent]
        axis = x[rotation.child] - origin
        length = torch.linalg.vector_norm(axis)
        if length <= 1e-8:
            raise ValueError("Degenerate reference bond axis")
        axis = axis / length
        relative = x - origin
        c, s = torch.cos(angle), torch.sin(angle)
        transformed = (
            x
            + relative * (c - 1)
            + torch.linalg.cross(axis.expand_as(relative), relative) * s
            + (relative * axis).sum(-1, keepdim=True) * axis * (1 - c)
        )
        moving = torch.zeros(len(x), device=x.device, dtype=torch.bool)
        moving[list(rotation.moving)] = True
        x = torch.where(moving[:, None], transformed, x)
    return x


def geometry_invariants(coordinates, bonds):
    """Lengths and neighbor-vector cosines, independent of angle reconstruction."""
    x = np.asarray(coordinates, dtype=np.float64)
    adjacency = [set() for _ in x]
    lengths = []
    for a, b, _ in bonds:
        a, b = int(a), int(b)
        adjacency[a].add(b)
        adjacency[b].add(a)
        lengths.append(float(np.linalg.norm(x[a] - x[b])))
    cosines = []
    for center, neighbors in enumerate(adjacency):
        neighbors = sorted(neighbors)
        for j, a in enumerate(neighbors):
            for b in neighbors[j + 1 :]:
                v, w = x[a] - x[center], x[b] - x[center]
                cosines.append(float(v @ w / (np.linalg.norm(v) * np.linalg.norm(w))))
    return np.array(lengths), np.array(cosines)
