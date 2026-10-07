"""Student-only conditioning interventions; actual candidate chemistry stays outside."""
import hashlib

import torch


BLOCKS = ('s_inputs', 's', 'z')
ARMS = ('correct', 'common', 'shuffled')


def fixed_candidate_derangement(site_key, candidates):
    """One hash-ordered cycle, independent of weights, predictions and teacher."""
    if len(candidates) != 19 or len(set(candidates)) != 19:
        raise ValueError('expected nineteen distinct non-WT candidates')
    order = sorted(range(19), key=lambda i: hashlib.sha256(
        f'mini-editor-intervention-v1|{site_key}|{candidates[i]}'.encode()).digest())
    donors = [None] * 19
    for receiver, donor in zip(order, order[1:] + order[:1]):
        donors[receiver] = donor
    return donors


def mean_candidate_conditioning(reference, predictions):
    """Compute C0 + mean(Ca-C0) in CPU FP64, cast once to native FP32.

    Return student-only energy diagnostics. Correct/permuted arms must use the
    original Ca tensors directly, avoiding reassociation through mean+residual.
    """
    if len(reference) != 3 or len(predictions) != 19:
        raise ValueError('expected three blocks and nineteen predictions')
    common, stats = [], {}
    for bi, name in enumerate(BLOCKS):
        base = reference[bi]
        if base.device.type != 'cpu' or base.dtype != torch.float32:
            raise ValueError('reference must be CPU FP32')
        delta = []
        for candidate in predictions:
            if len(candidate) != 3:
                raise ValueError('candidate has missing conditioning blocks')
            value = candidate[bi]
            if value.device.type != 'cpu' or value.dtype != base.dtype or value.shape != base.shape:
                raise ValueError('candidate block shape/device/dtype mismatch')
            if not torch.isfinite(value).all() or not torch.isfinite(base).all():
                raise ValueError('nonfinite conditioning')
            delta.append(value.double() - base.double())
        stack = torch.stack(delta)
        mean = stack.mean(0)
        centered = stack - mean
        raw_energy = float(stack.square().mean())
        mean_energy = float(mean.square().mean())
        centered_energy = float(centered.square().mean())
        result = (base.double() + mean).to(base.dtype)
        common.append(result)
        stats[name] = dict(delta_mse=raw_energy, mean_delta_mse=mean_energy,
                           centered_delta_mse=centered_energy,
                           centered_energy_fraction=centered_energy/raw_energy if raw_energy else None,
                           decomposition_residual=raw_energy-mean_energy-centered_energy,
                           common_max_abs_delta=float((result-base).abs().max()))
    return tuple(common), stats


def intervention_conditioning(predictions, common, donors, arm, index):
    """Permute all three blocks together; no chemistry or decoder packet input."""
    if (len(predictions) != 19 or len(donors) != 19 or sorted(donors) != list(range(19))
            or any(i == j for i, j in enumerate(donors))):
        raise ValueError('invalid fixed derangement')
    if not 0 <= index < 19:
        raise ValueError('candidate outside saturation panel')
    if arm == 'correct':
        return predictions[index]
    if arm == 'common':
        return common
    if arm == 'shuffled':
        return predictions[donors[index]]
    raise ValueError('unknown intervention')
