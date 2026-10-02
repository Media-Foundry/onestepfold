"""Fixed-WT-chart tangent plus oracle hard-endpoint residual reconstruction."""
import torch
from contextlib import contextmanager
from .global_response_rank import GlobalResponseBasis


def archived_reference_coordinates(packet, *, is_wt):
    """WT packets have noise/atom/xyz axes; mutants additionally have an arm axis."""
    if is_wt:
        if packet.ndim != 3 or packet.shape[0] != 2 or packet.shape[-1] != 3:
            raise ValueError('WT packet must have shape [2,atoms,3]')
        return packet, packet
    if packet.ndim != 4 or packet.shape[0] < 2 or packet.shape[1] != 2 or packet.shape[-1] != 3:
        raise ValueError('mutant packet must have shape [arms,2,atoms,3]')
    return packet[0], packet[1]


@contextmanager
def checkpointed_reverse(model):
    """Bound reverse-mode memory; restore the uncheckpointed JVP configuration."""
    from .models import soft_sequence_chart as chart_module
    from .models.soft_esm import soft_esm2
    original = chart_module.soft_esm2
    saved = [(m, m.blocks_per_ckpt) for m in model.modules() if hasattr(m, 'blocks_per_ckpt')]
    try:
        chart_module.soft_esm2 = soft_esm2
        for m, _ in saved:m.blocks_per_ckpt = 1
        yield
    finally:
        chart_module.soft_esm2 = original
        for m, value in saved:m.blocks_per_ckpt = value


def hard_replacement_direction(probabilities, position, amino_acid):
    """Probability-space e_target-e_WT, not a saturated-logit direction."""
    if probabilities.ndim != 2 or probabilities.shape[1] != 20:
        raise ValueError('expected L by 20 one-hot probabilities')
    if not torch.equal(probabilities, torch.nn.functional.one_hot(
            probabilities.argmax(-1), 20).to(probabilities)):
        raise ValueError('the tangent base must be exactly hard WT')
    result = torch.zeros_like(probabilities)
    result[position, probabilities[position].argmax()] = -1
    result[position, amino_acid] += 1
    return result


class JacobianResidualBasis:
    """All differences in FP64; only the final decoder state is cast to FP32.

    T is the complete probability-space JVP on the fixed WT chemical chart.
    R=hard-WT-T also includes atom-graph changes; it is not pure curvature.
    """
    def __init__(self, wt_s, wt_z, hard_s, hard_z, tangent_s, tangent_z):
        self.wt = (wt_s, wt_z)
        self.hard = (hard_s, hard_z)
        self.tangent = (tangent_s, tangent_z)
        residuals = []
        self.errors = {}
        for name, wt, hard, tangent in zip(('s', 'z'), self.wt, self.hard, self.tangent):
            if hard.shape != tangent.shape or not torch.isfinite(tangent).all():
                raise ValueError('invalid tangent shape or value')
            delta = hard.double() - wt.double()
            residual = delta - tangent.double()
            residuals.append(residual)
            self.errors[name] = dict(hard_response_energy=float(delta.square().sum()),
                tangent_energy=float(tangent.double().square().sum()),
                residual_energy=float(residual.square().sum()),
                inner_product=float((delta*tangent.double()).sum()))
        self.basis = GlobalResponseBasis(torch.zeros_like(wt_s, dtype=torch.float64),
            torch.zeros_like(wt_z, dtype=torch.float64), *residuals)

    def reconstruct(self, row, metric, rank):
        if metric not in ('raw', 'balanced'):
            raise ValueError('only predeclared joint metrics allowed')
        residual = self.basis.reconstruct(row, metric, rank)
        return tuple((wt.double()+tangent[row].double()+value).to(hard.dtype)
            for wt, tangent, value, hard in zip(self.wt, self.tangent, residual, self.hard))

    def tangent_only(self, row):
        return tuple((wt.double()+tangent[row].double()).to(hard.dtype)
            for wt, tangent, hard in zip(self.wt, self.tangent, self.hard))

    def evidence(self):
        return dict(tangent_fit=self.errors, residual_basis=self.basis.evidence())
