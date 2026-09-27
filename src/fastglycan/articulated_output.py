"""GT-free proper-frame/dihedral extraction and chemical-coordinate reconstruction."""

from __future__ import annotations

import numpy as np
import torch
from torch import nn

from fastglycan.articulated_reference import bridge_rotations

AA = dict(
    zip(
        "ARNDCQEGHILKMFPSTWYV",
        "ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL".split(),
        strict=True,
    )
)
EPSILON = 1e-4


def _frame(x, n, ca, c):
    first = x[..., c, :] - x[..., ca, :]
    length = torch.linalg.vector_norm(first, dim=-1, keepdim=True)
    invalid_first = length < EPSILON
    fixed_first = torch.zeros_like(first)
    fixed_first[..., 0] = 1
    first = torch.where(invalid_first, fixed_first, first / length.clamp_min(EPSILON))
    second = x[..., n, :] - x[..., ca, :]
    second = second - (second * first).sum(-1, keepdim=True) * first
    length = torch.linalg.vector_norm(second, dim=-1, keepdim=True)
    invalid_second = length < EPSILON
    basis = torch.nn.functional.one_hot(first.abs().argmin(-1), 3).to(x.dtype)
    fallback = basis - (basis * first).sum(-1, keepdim=True) * first
    fallback = fallback / torch.linalg.vector_norm(fallback, dim=-1, keepdim=True)
    second = torch.where(invalid_second, fallback, second / length.clamp_min(EPSILON))
    third = torch.linalg.cross(first, second)
    return torch.stack((first, second, third), dim=-1), invalid_first, invalid_second


def _phase(x, probe):
    a, b, p, d = probe
    axis = x[..., b, :] - x[..., a, :]
    axis_norm = torch.linalg.vector_norm(axis, dim=-1, keepdim=True)
    axis = axis / axis_norm.clamp_min(EPSILON)
    u, v = x[..., p, :] - x[..., a, :], x[..., d, :] - x[..., b, :]
    u = u - (u * axis).sum(-1, keepdim=True) * axis
    v = v - (v * axis).sum(-1, keepdim=True) * axis
    un, vn = torch.linalg.vector_norm(u, dim=-1), torch.linalg.vector_norm(v, dim=-1)
    valid = (axis_norm[..., 0] >= EPSILON) & (un >= EPSILON) & (vn >= EPSILON)
    u, v = u / un.clamp_min(EPSILON)[..., None], v / vn.clamp_min(EPSILON)[..., None]
    cosine = (u * v).sum(-1)
    sine = (torch.linalg.cross(u, v) * axis).sum(-1)
    # Re-normalize the phase so FP32 roundoff cannot introduce a scale transform.
    norm = torch.sqrt(cosine.square() + sine.square() + (~valid).to(x.dtype))
    cosine = torch.where(valid, cosine / norm.clamp_min(EPSILON), torch.ones_like(cosine))
    sine = torch.where(valid, sine / norm.clamp_min(EPSILON), torch.zeros_like(sine))
    return cosine, sine, valid


class _ResidueBatch(nn.Module):
    def __init__(self, reference, indices, names, bonds):
        super().__init__()
        self.n, self.ca, self.c = [names.index(name) for name in ("N", "CA", "C")]
        reference = torch.as_tensor(reference, dtype=torch.float64)
        frame, bad1, bad2 = _frame(reference, self.n, self.ca, self.c)
        if bad1.any() or bad2.any():
            raise ValueError("Chemical reference has a degenerate N/CA/C frame")
        local = (reference - reference[:, self.ca : self.ca + 1]) @ frame
        self.register_buffer("reference", local)
        self.register_buffer("indices", torch.as_tensor(indices, dtype=torch.long))
        self.rotations = bridge_rotations(names, bonds)
        neighbors = [set() for _ in names]
        for a, b, _ in bonds:
            neighbors[a].add(b)
            neighbors[b].add(a)
        probes, moving = [], []
        for rotation in self.rotations:
            a, b = rotation.parent, rotation.child
            proximal = sorted(
                set(range(len(names))) - set(rotation.moving) - {a},
                key=lambda i: (i not in neighbors[a], i),
            )
            distal = sorted(set(rotation.moving) - {b}, key=lambda i: (i not in neighbors[b], i))
            probe = next(
                (
                    (a, b, p, d)
                    for p in proximal
                    for d in distal
                    if _phase(local, (a, b, p, d))[2].all()
                ),
                None,
            )
            if probe is None:
                raise ValueError("No nondegenerate chemical dihedral probe")
            probes.append(probe)
            moving.append([i in rotation.moving for i in range(len(names))])
        self.probes = tuple(probes)
        self.register_buffer("moving", torch.tensor(moving, dtype=torch.bool))

    def forward(self, raw):
        predicted = raw[..., self.indices, :]
        frame, bad1, bad2 = _frame(predicted, self.n, self.ca, self.c)
        x = self.reference.expand_as(predicted)
        bad_torsions = torch.zeros((), dtype=torch.long, device=raw.device)
        for j, (rotation, probe) in enumerate(zip(self.rotations, self.probes, strict=True)):
            desired_c, desired_s, valid = _phase(predicted, probe)
            old_c, old_s, _ = _phase(x, probe)
            c = desired_c * old_c + desired_s * old_s
            s = desired_s * old_c - desired_c * old_s
            c, s = (
                torch.where(valid, c, torch.ones_like(c)),
                torch.where(valid, s, torch.zeros_like(s)),
            )
            # Normalize composed phase too, preserving rigid distances in FP32.
            norm = torch.sqrt(c.square() + s.square())
            c, s = (c / norm)[..., None, None], (s / norm)[..., None, None]
            origin = x[..., rotation.parent : rotation.parent + 1, :]
            axis = x[..., rotation.child : rotation.child + 1, :] - origin
            axis = axis / torch.linalg.vector_norm(axis, dim=-1, keepdim=True)
            relative = x - origin
            rotated = (
                x
                + relative * (c - 1)
                + torch.linalg.cross(axis.expand_as(x), relative) * s
                + (relative * axis).sum(-1, keepdim=True) * axis * (1 - c)
            )
            x = torch.where(self.moving[j, :, None], rotated, x)
            bad_torsions = bad_torsions + (~valid).sum()
        result = x @ frame.transpose(-1, -2) + predicted[..., self.ca : self.ca + 1, :]
        return result, torch.stack((bad1.sum(), bad2.sum(), bad_torsions))


class ArticulatedOutput(nn.Module):
    """Input-specific parameter-free adapter; constructor accepts chemical inputs only."""

    def __init__(self, reference, atom_names, residue_ids, sequence, variants):
        super().__init__()
        reference = np.asarray(reference, dtype=np.float64)
        names, residues = np.asarray(atom_names), np.asarray(residue_ids)
        if reference.shape != (len(names), 3) or residues.shape != names.shape:
            raise ValueError("Chemical reference/inventory shape mismatch")
        if not np.isfinite(reference).all():
            raise ValueError("Nonfinite chemical reference")
        if not np.array_equal(np.unique(residues), np.arange(1, len(sequence) + 1)):
            raise ValueError("Expected every sequence residue in the chemical inventory")
        groups = {}
        for residue in range(1, len(sequence) + 1):
            indices = np.flatnonzero(residues == residue)
            local_names = names[indices].tolist()
            if not {"N", "CA", "C"}.issubset(local_names):
                raise ValueError("Chemical inventory lacks pose anchors")
            key = AA[sequence[residue - 1]] + ":" + ",".join(local_names)
            if key not in variants or variants[key]["atom_names"] != local_names:
                raise ValueError("Unsupported fixed chemical inventory")
            groups.setdefault(key, []).append(indices)
        modules, order = [], []
        for key, indices in groups.items():
            indices = np.array(indices)
            variant = variants[key]
            modules.append(
                _ResidueBatch(reference[indices], indices, variant["atom_names"], variant["bonds"])
            )
            order.extend(indices.ravel().tolist())
        if sorted(order) != list(range(len(names))):
            raise ValueError("Chemical groups do not cover atom inventory exactly once")
        self.groups = nn.ModuleList(modules)
        self.register_buffer("restore_order", torch.argsort(torch.tensor(order, dtype=torch.long)))
        self.atom_count = len(names)

    def forward(self, raw):
        if raw.shape[-2:] != (self.atom_count, 3) or raw.dtype not in (
            torch.float32,
            torch.float64,
        ):
            raise ValueError(
                "Expected FP32/FP64 predicted coordinates in fixed chemical atom order"
            )
        if (
            self.groups[0].reference.device != raw.device
            or self.groups[0].reference.dtype != raw.dtype
        ):
            raise ValueError("Move adapter buffers to the prediction device/dtype before execution")
        pieces, counters = [], []
        for group in self.groups:
            result, counts = group(raw)
            pieces.append(result.reshape(*raw.shape[:-2], -1, 3))
            counters.append(counts)
        result = torch.cat(pieces, dim=-2)[..., self.restore_order, :]
        return {"coordinate": result, "fallback_counts": torch.stack(counters).sum(0)}
