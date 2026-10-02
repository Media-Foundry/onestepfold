"""Fixed context accounting and score/chemical diagnostics, without model gates."""
import numpy as np

from fastglycan.functional_response_rank import ranking_fidelity

TRAIN_CONTEXTS = ((3, 36), (3, 83), (4, 1), (5, 64))
HELD_CONTEXTS = ((4, 24), (5, 33), (6, 9), (6, 16))
ALL_CONTEXTS = TRAIN_CONTEXTS + HELD_CONTEXTS
SNAPSHOTS = (8192, 16384, 32768)
NOISES = (230201, 230211, 270101, 270103)


def context_role(parent, position):
    key = (parent, position)
    if key in TRAIN_CONTEXTS:
        return 'train'
    if key in HELD_CONTEXTS:
        return 'unseen_site' if parent in (4, 5) else 'unseen_protein'
    raise ValueError('context is outside the locked panel')


def exposure_counts(updates):
    if not 0 <= updates <= SNAPSHOTS[-1]:
        raise ValueError('outside the fixed update budget')
    return [updates // 4 + (index < updates % 4) for index in range(4)]


def score_fidelity(reference, prediction, names):
    """Ranking and score scale are separate; never infer a calibrated distribution."""
    y, x = np.asarray(reference, float), np.asarray(prediction, float)
    if len(names) != len(y):
        raise ValueError('AA labels do not match scores')
    result = ranking_fidelity(y, x)
    order_y, order_x = np.argsort(y, kind='stable'), np.argsort(x, kind='stable')
    yc, xc = y-y.mean(), x-x.mean()
    den = float(yc @ yc)
    result.update(task_rmse=float(np.sqrt(np.mean((x-y)**2))),
                  task_bias=float((x-y).mean()),
                  centered_scale_ratio=float(np.linalg.norm(xc)/np.linalg.norm(yc)) if den > 1e-16 else None,
                  affine_slope=float(yc @ xc/den) if den > 1e-16 else None,
                  teacher_choice=names[int(order_y[0])], student_choice=names[int(order_x[0])],
                  teacher_best_in_top3=bool(order_y[0] in order_x[:3]),
                  teacher_best_in_top5=bool(order_y[0] in order_x[:5]))
    return result


def noise_selection(reference, prediction, names):
    """Four rows in locked old/old/new/new order; old-only selection stays fixed."""
    y, x = np.asarray(reference, float), np.asarray(prediction, float)
    if y.shape != x.shape or y.shape != (4, len(names)) or not np.isfinite([y, x]).all():
        raise ValueError('expected four aligned noise rows')
    groups = {'old': [0, 1], 'new': [2, 3], 'all': [0, 1, 2, 3]}
    aggregate = {key: score_fidelity(y[ids].mean(0), x[ids].mean(0), names)
                 for key, ids in groups.items()}
    chosen = int(np.argmin(x[:2].mean(0)))
    teacher_chosen = int(np.argmin(y[:2].mean(0)))
    target = y[2:].mean(0)
    cross = dict(student_old_choice=names[chosen], teacher_old_choice=names[teacher_chosen],
                 teacher_new_choice=names[int(np.argmin(target))],
                 new_teacher_score_at_student_choice=float(target[chosen]),
                 new_teacher_score_at_teacher_old_choice=float(target[teacher_chosen]),
                 regret_to_new_best=float(target[chosen]-target.min()),
                 teacher_old_regret_to_new_best=float(target[teacher_chosen]-target.min()),
                 extra_regret_vs_teacher_old_choice=float(target[chosen]-target[teacher_chosen]))
    return dict(aggregate=aggregate, cross_noise=cross)


def chirality_trace(coordinates, labels, inventory, *, keep_all=False):
    """Same volume-sign predicate as response_geometry, with centre identities."""
    x = np.asarray(coordinates, float)
    centres = np.asarray(labels['centres'], dtype=int)
    reference = np.asarray(labels['volumes'], float)
    a, b, c, d = centres.T
    ab, ac, ad = x[b]-x[a], x[c]-x[a], x[d]-x[a]
    volume = np.sum(np.cross(ab, ac)*ad, axis=1)
    scale = np.linalg.norm(ab, axis=1)*np.linalg.norm(ac, axis=1)*np.linalg.norm(ad, axis=1)
    oriented = volume*np.sign(reference)
    normalized = oriented/np.maximum(scale, 1e-30)
    ratio = volume/reference
    wrong = volume*reference <= 0
    names, residues = inventory['atom_names'], inventory['residue_ids']
    chains = inventory.get('chain_ids', np.repeat('A', len(x)))
    def record(index):
        atoms = centres[index]
        return dict(indices=atoms.tolist(),
                    atoms=[dict(chain=str(chains[j]), residue=int(residues[j]), atom=str(names[j])) for j in atoms],
                    signed_volume=float(volume[index]), reference_volume=float(reference[index]),
                    reference_oriented_normalized_volume=float(normalized[index]),
                    reference_volume_ratio=float(ratio[index]), wrong=bool(wrong[index]))
    result = dict(wrong=[record(int(i)) for i in np.flatnonzero(wrong)],
                  minimum_oriented_normalized=float(normalized.min()) if len(centres) else None,
                  minimum_reference_ratio=float(ratio.min()) if len(centres) else None)
    if keep_all:
        result['all_centres'] = [record(i) for i in range(len(centres))]
    return result
