"""Bounded latent-only diagnostics; does not alter the original student."""
import math
import torch


def canonical_pair_factors(delta, rank=32, gap_tolerance=.01):
    """FP64 SVD, paired deterministic signs and balanced singular values.

    Return factors in the ORIGINAL student's units (UV^T / sqrt(rank)).
    Near-degenerate retained vectors may rotate jointly during supervision.
    A cut through a near-degenerate block is reported, not claimed canonical.
    """
    if delta.ndim != 4 or delta.shape[1] != delta.shape[2]:
        raise ValueError('expected [candidate,L,L,channel]')
    a, length, _, channels = delta.shape
    rank = min(rank, length)
    p, sigma, vh = torch.linalg.svd(delta.double().permute(0, 3, 1, 2), full_matrices=False)
    p = p[..., :rank]; q = vh[..., :rank, :].transpose(-1, -2)
    pivot = p.abs().argmax(dim=-2, keepdim=True)
    sign = p.gather(-2, pivot).sign(); sign = torch.where(sign == 0, 1., sign)
    p = p * sign; q = q * sign
    scale = sigma[..., :rank].sqrt().unsqueeze(-2) * rank**.25
    u = (p * scale).permute(0, 2, 1, 3).float()
    v = (q * scale).permute(0, 2, 1, 3).float()
    gaps = (sigma[..., :-1] - sigma[..., 1:]) / sigma[..., :-1].clamp_min(1e-30)
    grouped = {}
    for index, row in enumerate(gaps[..., :rank-1].reshape(a*channels, rank-1).cpu().tolist()):
        start = 0
        for end in range(1, rank+1):
            if end == rank or row[end-1] >= gap_tolerance:
                if end-start > 1:
                    grouped.setdefault((start, end), []).append(index)
                start = end
    groups = [(lo, hi, torch.tensor(ids, device=delta.device)) for (lo, hi), ids in grouped.items()]
    evidence = dict(rank=rank, relative_gap_tolerance=gap_tolerance,
                    clustered_blocks=sum(len(x[2]) for x in groups),
                    clustered_vectors=sum((hi-lo)*len(ids) for lo, hi, ids in groups),
                    boundary_near_degenerate=int((gaps[..., rank-1] < gap_tolerance).sum()) if rank < length else 0,
                    channels=channels, candidates=a)
    return u, v, groups, evidence


def aligned_factor_loss(u, v, target_u, target_v, groups):
    """Normalized balanced-factor regression, orthogonal Procrustes in clusters.

    Target rotations are detached solutions of the local least-squares problem;
    both factors rotate together, preserving their reconstructed matrix.
    """
    a, length, channels, rank = u.shape
    with torch.no_grad():
        tu = target_u.permute(0, 2, 1, 3).reshape(a*channels, length, rank).clone()
        tv = target_v.permute(0, 2, 1, 3).reshape(a*channels, length, rank).clone()
        pu = u.detach().permute(0, 2, 1, 3).reshape_as(tu)
        pv = v.detach().permute(0, 2, 1, 3).reshape_as(tv)
        for lo, hi, ids in groups:
            left = torch.cat([tu[ids, :, lo:hi], tv[ids, :, lo:hi]], dim=1)
            right = torch.cat([pu[ids, :, lo:hi], pv[ids, :, lo:hi]], dim=1)
            p, _, qh = torch.linalg.svd(left.transpose(-1, -2) @ right, full_matrices=False)
            rotation = p @ qh
            tu[ids, :, lo:hi] = tu[ids, :, lo:hi] @ rotation
            tv[ids, :, lo:hi] = tv[ids, :, lo:hi] @ rotation
        tu = tu.reshape(a, channels, length, rank).permute(0, 2, 1, 3)
        tv = tv.reshape(a, channels, length, rank).permute(0, 2, 1, 3)
    axes = (1, 2, 3)
    denominator = (tu.square().mean(axes)+tv.square().mean(axes)).clamp_min(1e-12)
    return (((u-tu).square().mean(axes)+(v-tv).square().mean(axes))/denominator).mean()


def response_nmse(prediction, target):
    axes = tuple(range(1, target.ndim))
    return (prediction-target).square().mean(axes)/target.square().mean(axes).clamp_min(1e-6)


def sparse_response_masks(residual, position, wt_ca, contact_radius=8.):
    """Oracle masks, never selected from decoded geometry or candidate score.

    top-magnitude uses teacher residual: a storage upper bound, NOT deployable.
    Contact-local means both endpoints in the WT CA neighbourhood (plus i±2).
    Entries are directed; each selected pair stores all channels plus indices.
    """
    length = residual.shape[0]
    if residual.shape[:2] != (length, length) or wt_ca.shape != (length, 3):
        raise ValueError('inconsistent residue indexing')
    ids = torch.arange(length, device=residual.device)
    rowcol = (ids[:, None] == position) | (ids[None, :] == position)
    near = (torch.linalg.vector_norm(wt_ca-wt_ca[position], dim=-1) <= contact_radius) | ((ids-position).abs() <= 2)
    contact = near[:, None] & near[None, :]
    energy = residual.double().square().sum(-1).flatten()
    order = torch.argsort(energy, descending=True, stable=True)
    def top(count):
        mask = torch.zeros(length*length, dtype=torch.bool, device=residual.device)
        mask[order[:count]] = True
        return mask.reshape(length, length)
    return dict(rowcol=rowcol, contact=contact,
                top_row_budget=top(int(rowcol.sum())), top_contact_budget=top(int(contact.sum())))
