"""Isolated parameter-space probes; no optimizer trajectory is continued."""
import copy
import torch


class StageUpdateProbe:
    def __init__(self, model, optimizer_state):
        self.model = model
        self.named = list(model.named_parameters())
        self.state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        self.optimizer_state = copy.deepcopy(optimizer_state)
        self.origin = self.vector()
        self.groups = {}
        offset = 0
        for name, parameter in self.named:
            group = '.'.join(name.split('.')[:2]) if name.startswith('blocks.') else name.split('.')[0]
            self.groups.setdefault(group, []).append((offset, offset + parameter.numel()))
            offset += parameter.numel()

    def vector(self, gradients=False):
        values = []
        for _, parameter in self.named:
            value = parameter.grad if gradients else parameter
            if value is None:
                raise ValueError('missing parameter gradient')
            values.append(value.detach().cpu().double().reshape(-1))
        result = torch.cat(values)
        if not torch.isfinite(result).all():
            raise ValueError('nonfinite parameter/gradient vector')
        return result

    def reset(self):
        self.model.load_state_dict(self.state, strict=True)
        self.model.zero_grad(set_to_none=True)

    def assign(self, direction, fraction=1.):
        """Always perturb the original parameters, never the previous probe."""
        if direction.shape != self.origin.shape or not torch.isfinite(direction).all():
            raise ValueError('invalid probe direction')
        self.reset()
        target = self.origin + direction.detach().cpu().double() * fraction
        offset = 0
        with torch.no_grad():
            for _, parameter in self.named:
                n = parameter.numel()
                parameter.copy_(target[offset:offset+n].reshape(parameter.shape))
                offset += n
        return self.vector() - self.origin

    def adam_direction(self, gradient, clip):
        """Clone saved moments for each one-step counterfactual."""
        self.reset()
        if gradient.shape != self.origin.shape or not torch.isfinite(gradient).all():
            raise ValueError('invalid AdamW gradient')
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=1e-4, weight_decay=1e-4, eps=1e-8)
        optimizer.load_state_dict(copy.deepcopy(self.optimizer_state))
        offset = 0
        for _, parameter in self.named:
            n = parameter.numel()
            parameter.grad = gradient[offset:offset+n].reshape(parameter.shape).to(parameter).clone()
            offset += n
        if clip:
            norm = torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1., error_if_nonfinite=True)
            norm = float(norm)
        else:
            norm = float(gradient.norm())
        applied_gradient = self.vector(gradients=True)
        optimizer.step()
        delta = self.vector() - self.origin
        self.reset()
        return delta, applied_gradient, norm

    def comparison(self, gradient, displacement):
        """G dot delta is the first-order loss change, not its negative."""
        dot = float(gradient @ displacement)
        gn, dn = float(gradient.norm()), float(displacement.norm())
        groups = {}
        for group, slices in self.groups.items():
            groups[group] = sum(float(gradient[a:b] @ displacement[a:b]) for a, b in slices)
        return dict(dot=dot, gradient_norm=gn, displacement_norm=dn,
                    cosine=dot/(gn*dn) if gn*dn else None, groups=groups)

