"""Development-only connection dead zones; original chemistry gates are unchanged."""
import math

import torch

from .anchored_tail import TailObjective
from .connection_audit import TOLERANCES


class CalibratedConnectionObjective(TailObjective):
    """Replace trans penalty onset only, retaining old outside-window curvature.

    Raw-selected cis branches keep the old window. This does not certify or fix
    branch selection and does not turn empirical intervals into acceptance gates.
    """
    def __init__(self, raw, anchors, sequence, pairs, radii, calibration):
        super().__init__(raw, anchors, sequence, pairs, radii)
        windows = calibration['windows']
        onsets = []
        for term, tolerance in TOLERANCES.items():
            values = []
            for aa in sequence[1:]:
                entry = windows['Pro' if aa == 'P' else 'other']
                if not entry['supported']:
                    raise ValueError('unsupported calibration class')
                value = float(entry['windows'][term]['q95']['pooled'])
                if not math.isfinite(value) or value <= 0:
                    raise ValueError('invalid empirical onset')
                values.append(value)
            proposed = raw.new_tensor(values)
            onsets.append(torch.where(self.omega_target[:, 0] < 0, proposed,
                                      torch.full_like(proposed, .5 * tolerance)))
        self.register_buffer('connection_onsets', torch.stack(onsets))

    def forward(self, x, values, rho):
        original_loss, terms = super().forward(x, values, rho)
        residuals = self.residuals(x)
        connection = x.sum() * 0
        for index, (term, tolerance) in enumerate(TOLERANCES.items()):
            residual = residuals[term]
            if residual.numel():
                # Keep the old denominator so only onset, not outside curvature,
                # changes. At the original onsets this is exactly the old formula.
                scale = .5 * tolerance
                connection = connection + torch.relu(
                    residual.abs() / scale - self.connection_onsets[index] / scale).square().mean()
        return original_loss + rho * (connection - terms['connection']), dict(
            terms, original_connection=terms['connection'], connection=connection)
