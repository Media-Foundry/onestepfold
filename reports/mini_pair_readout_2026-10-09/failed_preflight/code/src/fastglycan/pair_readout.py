"""Full-field, weighted frozen-feature regression without normal equations."""
import math

import torch


def site_row_weight(length, scale, sites=27, candidates=19, channels=128):
    """Match a mean over sites, candidates, spatial entries and channels."""
    if min(length, scale, sites, candidates, channels) <= 0:
        raise ValueError('positive dimensions and locked scale required')
    return 1.0 / (sites * candidates * length * length * channels * scale)


class WeightedReadoutQR:
    """Keep the QR factor of all weighted [features, targets] rows."""

    def __init__(self, features=128, outputs=128, chunk_rows=8192):
        self.features, self.outputs, self.chunk_rows = features, outputs, chunk_rows
        self.r = torch.empty(0, features + outputs, dtype=torch.float64)
        self.rows = 0

    def add(self, features, targets, weight):
        if features.ndim != 2 or targets.shape != (features.shape[0], self.outputs):
            raise ValueError('matched row matrices required')
        if features.shape[1] != self.features or not math.isfinite(weight) or weight <= 0:
            raise ValueError('invalid feature dimension or weight')
        for start in range(0, len(features), self.chunk_rows):
            x = features[start:start + self.chunk_rows].detach().to('cpu', torch.float64)
            y = targets[start:start + self.chunk_rows].detach().to('cpu', torch.float64)
            if not torch.isfinite(x).all() or not torch.isfinite(y).all():
                raise ValueError('nonfinite regression data')
            block = torch.cat((x, y), dim=1) * math.sqrt(weight)
            self.r = torch.linalg.qr(torch.cat((self.r, block)), mode='r').R
            self.rows += len(x)

    def objective(self, matrix):
        matrix = matrix.detach().to('cpu', torch.float64)
        return float((self.r[:, :self.features] @ matrix - self.r[:, self.features:]).square().sum())

    def solve(self, original, rcond):
        if not self.rows or not 0 < rcond < 1:
            raise ValueError('nonempty design and explicit relative tolerance required')
        original = original.detach().to('cpu', torch.float64)
        if original.shape != (self.features, self.outputs):
            raise ValueError('matrix convention is H @ W')
        x, y = self.r[:, :self.features], self.r[:, self.features:]
        u, singular, vh = torch.linalg.svd(x, full_matrices=False)
        keep = singular > rcond * singular[0]
        directions = vh[keep].T
        rhs = u[:, keep].T @ (y - x @ original)
        delta = directions @ (rhs / singular[keep, None])
        solution = original + delta
        residual = x @ solution - y
        projected_gradient = directions.T @ (x.T @ residual)
        before, after = self.objective(original), self.objective(solution)
        if after > before + 1e-10 * max(1., before):
            raise ArithmeticError('restricted least squares worsened the feasible original head')
        energy = float(singular.square().sum())
        audit = dict(rows=self.rows, rank=int(keep.sum()), rcond=rcond,
                     singular_values=singular.tolist(), objective_old=before,
                     objective_fit=after, objective_zero=float(y.square().sum()),
                     discarded_design_energy_fraction=float(singular[~keep].square().sum()) / max(energy, 1e-300),
                     retained_condition=float(singular[0] / singular[keep][-1]) if keep.any() else None,
                     original_weight_norm=float(original.norm()), fitted_weight_norm=float(solution.norm()),
                     correction_norm=float(delta.norm()),
                     projected_gradient_norm=float(projected_gradient.norm()),
                     discarded_update_norm=float((vh[~keep] @ delta).norm()))
        return solution, audit


def aa_center(values):
    """Candidate centering in FP64; first axis is the complete AA panel."""
    x = values.detach().double()
    return x - x.mean(dim=0, keepdim=True)
