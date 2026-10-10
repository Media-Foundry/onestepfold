"""Full-TRAIN stage fitting and transactional, work-bounded L-BFGS steps."""
import copy
import hashlib

import numpy as np
import torch

from fastglycan.models.stage_pair_recovery import aligned_pair_loss


def parameter_digest(parameters):
    digest = hashlib.sha256()
    for parameter in parameters:
        digest.update(parameter.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


class FullBatchStageTrainer:
    """Keep site weights independent of length; labels only reach the loss.

    fetch(site, aa) returns (candidate conditioning, candidate boundary, label).
    Each site's nineteen gradients accumulate in native FP32; site gradients
    are then averaged in CPU FP64, matching the preceding update audit.
    """

    def __init__(self, model, sites, fetch, reference_pairs, alphabet, scales):
        self.model, self.sites, self.fetch = model, sites, fetch
        self.references, self.alphabet, self.scales = reference_pairs, alphabet, scales
        self.parameters = list(model.parameters())
        self.counts = dict(forwards=0, backwards=0, gradient_passes=0)
        self.last_gradient = None
        self.last_result = None

    def objective(self, backward=True):
        site_rows = []
        gradient_sum = None
        for site in self.sites:
            self.model.zero_grad(set_to_none=True)
            error_sum = None
            energy = 0.
            losses = []
            choices = site['candidates']
            scale = self.scales[site['site_key']]
            with torch.enable_grad() if backward else torch.no_grad():
                for aa in choices:
                    base, boundary, target = self.fetch(site, aa)
                    result, outputs = self.model(
                        base, boundary, self.references[site['parent_index']],
                        site['position_zero_based'], self.alphabet.index(site['original_aa']),
                        self.alphabet.index(aa))
                    assert result[0] is base[0] and result[1] is base[1]
                    loss, _ = aligned_pair_loss(outputs, target, None, scale, 'final')
                    if not torch.isfinite(loss):
                        raise FloatingPointError('nonfinite full-TRAIN loss')
                    losses.append(float(loss.detach()))
                    error = outputs[-1].detach().double() - target.detach().double()
                    energy += float(error.square().sum())
                    error_sum = error if error_sum is None else error_sum + error
                    if backward:
                        (loss / len(choices)).backward()
                        self.counts['backwards'] += 1
                    self.counts['forwards'] += 1
            raw = energy / len(choices) / error_sum.numel() / scale
            common = float((error_sum / len(choices)).square().mean()) / scale
            centered = raw - common
            assert centered >= -1e-10
            assert np.isclose(raw, np.mean(losses), rtol=2e-5, atol=1e-7)
            site_rows.append(dict(site=site['site_key'], raw=raw, common=common, centered=centered))
            if backward:
                if any(p.grad is None for p in self.parameters):
                    raise RuntimeError('missing full-TRAIN parameter gradient')
                g = torch.cat([p.grad.detach().cpu().double().flatten() for p in self.parameters])
                gradient_sum = g if gradient_sum is None else gradient_sum + g
        result = {key: float(np.mean([row[key] for row in site_rows]))
                  for key in ('raw', 'common', 'centered')}
        result['sites'] = site_rows
        if backward:
            gradient = gradient_sum / len(self.sites)
            if not torch.isfinite(gradient).all():
                raise FloatingPointError('nonfinite full-TRAIN gradient')
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


class _ClosureBudgetReached(RuntimeError):
    pass


class BoundedLBFGS:
    """Standard PyTorch L-BFGS with exact rollback at a closure-budget boundary.

    The library may make an extra trial beyond max_eval. The hard callback
    guard prevents this. An interrupted transaction restores BOTH parameters
    and curvature history. All already evaluated trials remain charged.
    """

    def __init__(self, parameters):
        self.parameters = list(parameters)
        self.optimizer = torch.optim.LBFGS(
            self.parameters, lr=1., max_iter=1, max_eval=16, history_size=20,
            tolerance_grad=1e-7, tolerance_change=1e-9, line_search_fn='strong_wolfe')

    def step(self, closure, max_calls):
        if max_calls < 1:
            raise ValueError('at least one full-gradient evaluation required')
        origin = [p.detach().clone() for p in self.parameters]
        state = copy.deepcopy(self.optimizer.state_dict())
        observations = []

        def restore():
            with torch.no_grad():
                for parameter, value in zip(self.parameters, origin):
                    parameter.copy_(value)
            self.optimizer.load_state_dict(state)
            self.optimizer.zero_grad(set_to_none=True)

        def measured():
            if len(observations) >= max_calls:
                raise _ClosureBudgetReached()
            result = closure()
            observation = dict(result)
            observation['parameter_sha256'] = parameter_digest(self.parameters)
            observations.append(observation)
            return result['raw']

        try:
            self.optimizer.param_groups[0]['max_eval'] = min(16, max_calls)
            self.optimizer.step(measured)
        except _ClosureBudgetReached:
            restore()
            return dict(status='budget_rollback', calls=len(observations), observations=observations,
                        changed=False, before=observations[0]['raw'], after=observations[0]['raw'])
        except BaseException:
            restore()
            raise
        digest = parameter_digest(self.parameters)
        matches = [r for r in observations if r['parameter_sha256'] == digest]
        if not matches:
            restore()
            raise RuntimeError('L-BFGS accepted a state without an exact full-TRAIN measurement')
        before, after = observations[0]['raw'], matches[-1]['raw']
        if after > before + 1e-10:
            restore()
            return dict(status='ascent_rollback', calls=len(observations), observations=observations,
                        changed=False, before=before, after=before, rejected_objective=after)
        changed = any(not torch.equal(p, value) for p, value in zip(self.parameters, origin))
        return dict(status='accepted' if changed else 'unchanged', calls=len(observations),
                    observations=observations, changed=changed, before=before, after=after)
