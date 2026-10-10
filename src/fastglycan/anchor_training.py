"""Full-TRAIN fitting with one differentiable reference anchor per site."""
from pathlib import Path

import numpy as np
import torch

from fastglycan.models.anchored_pair_recovery import (
    backward_reference_proxy, reference_gradient_proxy)
from fastglycan.paired_teacher_protocol import sha256
from fastglycan.stage_fullbatch import FullBatchStageTrainer


def load_anchor_boundaries(lock, device):
    """Read only the hash-bound WT cache, never candidate teacher boundaries."""
    root = Path(lock['reference_cache_root'])
    result = {}
    for record in lock['reference_records']:
        path = root / record['path']
        if sha256(path) != record['sha256']:
            raise ValueError(f'changed reference cache: {path}')
        value = torch.load(path, map_location='cpu', weights_only=True)['boundary']
        result[record['parent']] = value.to(device)
    return result


class AnchoredFullBatchTrainer(FullBatchStageTrainer):
    """Same site-weighted objective; retain the WT branch's shared gradient.

    Native FP32 candidate and reference gradients accumulate within each site;
    across-site averaging is CPU FP64. The reference graph is rebuilt for every
    site on every pass. The proxy only saves graph residency, not its derivative.
    """

    def __init__(self, model, sites, fetch, reference_pairs, alphabet, scales,
                 reference_bases, reference_boundaries):
        super().__init__(model, sites, fetch, reference_pairs, alphabet, scales)
        self.reference_bases = reference_bases
        self.reference_boundaries = reference_boundaries
        self.counts.update(reference_forwards=0, reference_backwards=0)

    def objective(self, backward=True):
        rows, gradient_sum = [], None
        for site in self.sites:
            self.model.zero_grad(set_to_none=True)
            pi, pos = site['parent_index'], site['position_zero_based']
            old = self.alphabet.index(site['original_aa'])
            choices, scale = site['candidates'], self.scales[site['site_key']]
            error_sum, energy, losses = None, 0., []
            with torch.enable_grad() if backward else torch.no_grad():
                anchor = self.model.prepare_reference(self.reference_bases[pi],
                    self.reference_boundaries[pi], self.references[pi], pos, old)
                proxy = reference_gradient_proxy(anchor) if backward else anchor
                self.counts['reference_forwards'] += 1
                for aa in choices:
                    base, boundary, target = self.fetch(site, aa)
                    result = self.model(base, boundary, self.references[pi], pos,
                        old, self.alphabet.index(aa), anchor=proxy)
                    assert result[0] is base[0] and result[1] is base[1]
                    loss = (result[2]-target).square().mean()/scale
                    if not torch.isfinite(loss):
                        raise FloatingPointError('nonfinite anchored full-TRAIN loss')
                    losses.append(float(loss.detach()))
                    error = result[2].detach().double()-target.detach().double()
                    energy += float(error.square().sum())
                    error_sum = error if error_sum is None else error_sum+error
                    if backward:
                        (loss/len(choices)).backward()
                        self.counts['backwards'] += 1
                    self.counts['forwards'] += 1
                if backward:
                    backward_reference_proxy(anchor, proxy)
                    self.counts['reference_backwards'] += 1
            raw = energy/len(choices)/error_sum.numel()/scale
            common = float((error_sum/len(choices)).square().mean())/scale
            centered = raw-common
            assert centered >= -1e-10
            assert np.isclose(raw, np.mean(losses), rtol=2e-5, atol=1e-7)
            rows.append(dict(site=site['site_key'], raw=raw, common=common, centered=centered))
            if backward:
                if any(p.grad is None for p in self.parameters):
                    raise RuntimeError('missing anchored parameter gradient')
                gradient = torch.cat([p.grad.detach().cpu().double().flatten() for p in self.parameters])
                gradient_sum = gradient if gradient_sum is None else gradient_sum+gradient
            del anchor, proxy, result, loss
        result = {key: float(np.mean([r[key] for r in rows])) for key in ('raw','common','centered')}
        result['sites'] = rows
        if backward:
            gradient = gradient_sum/len(self.sites)
            if not torch.isfinite(gradient).all():
                raise FloatingPointError('nonfinite anchored full-TRAIN gradient')
            offset = 0
            for parameter in self.parameters:
                size = parameter.numel()
                parameter.grad = gradient[offset:offset+size].reshape(parameter.shape).to(parameter).clone()
                offset += size
            self.last_gradient = gradient
            result['gradient_norm'] = float(gradient.norm())
            self.counts['gradient_passes'] += 1
        self.last_result = result
        return result
