"""Conditional local rank interventions, not a complete trunk compressor."""
import numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree


def reconstruct_local_responses(endpoints, wt_index, ranks):
    """Centered 19-mutant PCA in the original, unscaled, duplicated-diagonal metric.

    Rows are AA endpoints. WT is kept exactly, not projected as a twentieth sample.
    The small AA Gram eigensystem implements the equivalent feature-space SVD.
    """
    keys = ('s_site', 'z_row', 'z_col')
    shapes = [endpoints[k].shape[1:] for k in keys]
    sizes = [int(np.prod(s)) for s in shapes]
    x = np.concatenate([np.asarray(endpoints[k], dtype=np.float64).reshape(20, -1) for k in keys], axis=1)
    if not np.isfinite(x).all() or not 0 <= wt_index < 20:
        raise ValueError('invalid endpoint array')
    ids = np.delete(np.arange(20), wt_index)
    delta = x[ids] - x[wt_index]
    mean = delta.mean(0)
    centered = delta - mean
    values, vectors = np.linalg.eigh(centered @ centered.T)
    order = np.argsort(values)[::-1]
    values, vectors = np.maximum(values[order], 0), vectors[:, order]
    outputs = {}
    for k in ranks:
        if not 0 <= k <= 18:
            raise ValueError('centered nineteen-mutant rank is at most eighteen')
        approximate = x.copy()
        approximate[ids] = x[wt_index] + mean + vectors[:, :k] @ (vectors[:, :k].T @ centered)
        blocks = np.split(approximate, np.cumsum(sizes)[:-1], axis=1)
        outputs[k] = {key: b.reshape(20, *shape).astype(np.float32) for key, b, shape in zip(keys, blocks, shapes)}
    energy = [float(values[:k].sum() / values.sum()) if values.sum() else None for k in ranks]
    return outputs, dict(ranks=list(ranks), energy=energy, total_centered_energy=float(values.sum()))


def local_conditioning_intervention(conditioning, slices, position):
    """Replace only one s token and its two z strips, keep all other target inputs."""
    import torch
    inputs, s, z = conditioning
    s, z = s.clone(), z.clone()
    row = torch.as_tensor(slices['z_row'], device=z.device, dtype=z.dtype)
    col = torch.as_tensor(slices['z_col'], device=z.device, dtype=z.dtype)
    if not torch.allclose(row[position], col[position], atol=1e-6, rtol=1e-6):
        raise ValueError('duplicated pair diagonal reconstruction disagrees')
    s[position] = torch.as_tensor(slices['s_site'], device=s.device, dtype=s.dtype)
    z[position] = row
    z[:, position] = col
    z[position, position] = (row[position] + col[position]) * .5
    return inputs, s, z


def pack_conditioning(conditioning):
    """Identical contiguous layout for exact, sham and truncated paths."""
    import torch
    sizes = [x.numel() for x in conditioning]
    flat = torch.cat([x.reshape(-1) for x in conditioning])
    return tuple(x.reshape(t.shape) for x, t in zip(flat.split(sizes), conditioning))


def ranking_fidelity(exact, approximate):
    """Lower-is-better task; AA order breaks exact ties, Spearman uses average ties."""
    y, x = np.asarray(exact, float), np.asarray(approximate, float)
    if y.shape != x.shape or y.ndim != 1 or not np.isfinite([y, x]).all():
        raise ValueError('invalid ranking arrays')
    yr, xr = rankdata(y), rankdata(x)
    rho = float(np.corrcoef(yr, xr)[0, 1]) if np.ptp(yr) and np.ptp(xr) else None
    true_order, pred_order = np.argsort(y, kind='stable'), np.argsort(x, kind='stable')
    regret = float(y[pred_order[0]] - y[true_order[0]])
    spread = float(np.ptp(y))
    return dict(spearman=rho, top1_match=bool(pred_order[0] == true_order[0]), top1_regret=regret,
                normalized_regret=regret/spread if spread > 1e-8 else None,
                exact_task_range=spread, low_task_range=spread <= 1e-8,
                task_mae=float(np.mean(np.abs(x-y))),
                top3_recall=len(set(true_order[:3]) & set(pred_order[:3]))/3,
                top5_recall=len(set(true_order[:5]) & set(pred_order[:5]))/5)


def prepare_fidelity_pairs(reference, residues):
    y = np.asarray(reference, float)
    pairs = cKDTree(y).query_pairs(15., output_type='ndarray')
    d = np.linalg.norm(y[pairs[:, 0]] - y[pairs[:, 1]], axis=1)
    keep = (d < 15) & (np.asarray(residues)[pairs[:, 0]] != np.asarray(residues)[pairs[:, 1]])
    pairs, d = pairs[keep], d[keep]
    count = np.bincount(pairs.ravel(), minlength=len(y))
    return pairs, d, count


def fidelity_lddt(coordinates, cache):
    pairs, target, count = cache
    x = np.asarray(coordinates, float)
    error = np.abs(np.linalg.norm(x[pairs[:, 0]]-x[pairs[:, 1]], axis=1)-target)
    scores = (error[:, None] < np.array([.5, 1., 2., 4.])).mean(1)
    sums = np.bincount(pairs.ravel(), weights=np.repeat(scores, 2), minlength=len(x))
    return float(np.mean(sums[count > 0]/count[count > 0])) if np.any(count) else None


def response_structure_metrics(coordinates, reference, ca, local, caches):
    """Reference is exact HARD MODEL output, never called experimental GT."""
    x, y = np.asarray(coordinates, float), np.asarray(reference, float)
    xc, yc = x[ca], y[ca]
    xm, ym = xc.mean(0), yc.mean(0)
    u, _, vt = np.linalg.svd((xc-xm).T @ (yc-ym))
    rotation = u @ np.diag([1., 1., np.linalg.det(u@vt)]) @ vt
    aligned = (xc-xm) @ rotation + ym
    local_delta = aligned[local]-yc[local]
    i, j = np.triu_indices(len(ca), 3)
    dx, dy = np.linalg.norm(xc[i]-xc[j], axis=1), np.linalg.norm(yc[i]-yc[j], axis=1)
    contact_x, contact_y = dx < 8., dy < 8.
    return dict(all_atom_lddt=fidelity_lddt(x, caches[0]), ca_lddt=fidelity_lddt(xc, caches[1]),
                ca_aligned_rmsd=float(np.sqrt(np.mean(np.sum((aligned-yc)**2, axis=1)))),
                local_ca_rmsd_global_frame=float(np.sqrt(np.mean(np.sum(local_delta**2, axis=1)))),
                ca_pair_distance_rmse=float(np.sqrt(np.mean((dx-dy)**2))),
                contact_disagreement=float(np.mean(contact_x != contact_y)),
                contact_jaccard=float(np.sum(contact_x & contact_y)/np.sum(contact_x | contact_y)) if np.any(contact_x | contact_y) else 1.,
                distance_bin_disagreement=float(np.mean(np.digitize(dx, np.arange(2.,22.,2.)) != np.digitize(dy, np.arange(2.,22.,2.)))))


def response_geometry(coordinates, labels):
    """Full native heavy inventory, graph-distance<=3 exclusions, checked CA/I/T centres."""
    x = np.asarray(coordinates, float)
    pairs = cKDTree(x).query_pairs(4., output_type='ndarray')
    pairs = pairs[~np.isin(pairs[:,0]*len(x)+pairs[:,1], labels['excluded'])]
    distance = np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]], axis=1)
    radii = np.asarray(labels['radii'])
    depth = radii[pairs].sum(1)-distance
    a,b,c,d = np.asarray(labels['centres']).T
    volumes = (np.cross(x[b]-x[a], x[c]-x[a])*(x[d]-x[a])).sum(1)
    wrong = volumes*np.asarray(labels['volumes']) <= 0
    return dict(severe_pairs=int(np.sum(distance < 1.)), checked_chirality_wrong=int(wrong.sum()),
                checked_centres=len(wrong), max_penetration=max(0., float(depth.max())) if len(depth) else 0.,
                zero_severe_strict_checked_chirality=bool(not np.any(distance < 1.) and not wrong.any()))
