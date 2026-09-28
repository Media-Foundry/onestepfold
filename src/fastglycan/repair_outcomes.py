"""Offline outcome classification; no change to the repair or locked acceptance."""
import numpy as np
from .hybrid_geometry import GeometryRules


def absolute_failures(geometry):
    rules = GeometryRules()
    if not all(np.isfinite(v) for v in geometry.values()):
        return ['nonfinite']
    upper = {'bond_rmse': rules.bond_rmse_max,
             'peptide_mae': rules.peptide_mae_max,
             'severe_pairs_per_atom': rules.severe_pairs_per_atom_max,
             'max_penetration': rules.max_penetration_max}
    failures = [k for k, v in upper.items() if geometry[k] > v]
    if geometry['chirality_fraction'] < rules.chirality_fraction_min:
        failures.append('chirality_fraction')
    return failures


def chirality_transitions(raw, repaired, centres, reference_volumes, residues, chains, sequence):
    """Describe only the archived CA-centred signed-volume check, not all stereocentres."""
    centres = np.asarray(centres, dtype=int).reshape(-1, 4)
    ref = np.asarray(reference_volumes, dtype=float)
    if len(centres) != len(ref) or np.any(np.abs(ref) <= 1e-4):
        raise ValueError('invalid archived chirality references')
    ca, n, c, cb = centres.T
    ratios = {}
    for phase, x in [('raw', raw), ('repaired', repaired)]:
        x = np.asarray(x, dtype=float).reshape(-1, 3)
        volume = (np.cross(x[n]-x[ca], x[c]-x[ca])*(x[cb]-x[ca])).sum(-1)
        ratios[phase] = volume * np.sign(ref) / np.abs(ref)
        if not np.isfinite(ratios[phase]).all():
            raise ValueError('nonfinite signed volume')
    rows = []
    for j in np.flatnonzero((ratios['raw'] <= 0) | (ratios['repaired'] <= 0)):
        residue = int(residues[ca[j]])
        before, after = float(ratios['raw'][j]), float(ratios['repaired'][j])
        kind = 'new_flip' if before > 0 else ('corrected' if after > 0 else 'persistent')
        rows.append(dict(chain=str(chains[ca[j]]), residue=residue,
                         amino_acid=sequence[residue-1], kind=kind,
                         raw_ratio=before, repaired_ratio=after))
    return dict(centres=len(ref), raw_wrong=int((ratios['raw'] <= 0).sum()),
                repaired_wrong=int((ratios['repaired'] <= 0).sum()), rows=rows)
