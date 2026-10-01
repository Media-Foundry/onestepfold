"""A fixed target-backbone task; the target is NOT mutant experimental truth."""
import torch
from .hybrid_geometry import hard_accept


def backbone_target_pairs(coordinates, observed):
    """All observed CA pairs separated by >=3 residues, without contact filtering."""
    xyz = torch.as_tensor(coordinates, dtype=torch.float64)
    mask = torch.as_tensor(observed, dtype=torch.bool)
    if xyz.shape != (len(mask), 3) or not torch.isfinite(xyz[mask]).all():
        raise ValueError('invalid observed target backbone')
    pairs = torch.triu_indices(len(mask), len(mask), offset=3).T
    pairs = pairs[mask[pairs[:, 0]] & mask[pairs[:, 1]]]
    if not len(pairs):
        raise ValueError('no observed nonlocal target pairs')
    distance = (xyz[pairs[:, 0]] - xyz[pairs[:, 1]]).norm(dim=-1)
    return pairs, distance


def backbone_target_loss(coordinates, ca_indices, pairs, distances):
    """Mean Huber distance error, delta=1 Angstrom; invariant to rigid motion."""
    ca = coordinates.reshape(-1, 3)[ca_indices]
    ij = pairs.to(ca.device)
    predicted = (ca[ij[:, 0]] - ca[ij[:, 1]]).norm(dim=-1)
    error = predicted - distances.to(predicted)
    absolute = error.abs()
    return torch.where(absolute <= 1, .5 * error.square(), absolute - .5).mean()


def backbone_candidate_accept(candidate, parent):
    """Task plus existing broad guards, zero severe pairs and ALL checked centres.

    No old idealized connection maximum window is reinstated. This bounded
    operational screen is not full stereochemistry or binding validation.
    """
    c, p = candidate['chemistry'], parent['chemistry']
    decision = hard_accept(candidate['task'], parent['task'],
                           c['legacy_geometry'], p['legacy_geometry'])
    reasons = list(decision['reasons'])
    if not c['zero_severe']:
        reasons.append('severe_nonbonded_overlap')
    if not c['strict_checked_chirality']:
        reasons.append('checked_stereocentre')
    return dict(accepted=not reasons, reasons=reasons)
