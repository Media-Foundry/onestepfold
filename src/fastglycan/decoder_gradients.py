"""Differentiable frozen-decoder calls with freshly connected pair-dependent caches."""

from __future__ import annotations

import copy

import torch
import torch.utils.checkpoint  # Register the submodule used by Protenix's gradient path.

from fastglycan.teacher_pairing import feature_digest, tensor_digest


def select_gradient_records(records):
    from onestepfold.training.coordinate_refiner import select_length_stratified

    train = sorted(
        (r for r in records if r.split == "train"), key=lambda r: (r.sequence_length, r.group_id)
    )
    if len(train) != 128:
        raise ValueError("expected the accepted 128 training groups")
    chosen = [train[0], train[-1]] + select_length_stratified(train[1:-1], 2, seed=107)
    return sorted(chosen, key=lambda r: (r.sequence_length, r.group_id))


def detached_tree(value, device="cpu"):
    if isinstance(value, torch.Tensor):
        return value.detach().to(device).clone()
    if isinstance(value, dict):
        return {key: detached_tree(child, device) for key, child in value.items()}
    if isinstance(value, list):
        return [detached_tree(child, device) for child in value]
    if isinstance(value, tuple):
        return tuple(detached_tree(child, device) for child in value)
    return copy.deepcopy(value)


class FirstDiffusionCall:
    """Capture the real first response, preserving mutable features before subsequent steps."""

    def __init__(self, module):
        self.module = module
        self.calls = 0
        self.packet = self.response = self.cache_sha256 = None

    def __enter__(self):
        def before(module, args, kwargs):
            self.calls += 1
            if self.calls == 1:
                self.cache_sha256 = {
                    key: tensor_digest(kwargs[key]) if kwargs[key] is not None else None
                    for key in ("pair_z", "p_lm", "c_l")
                }
                self.packet = detached_tree(
                    {
                        key: value
                        for key, value in kwargs.items()
                        if key not in ("z_trunk", "pair_z", "p_lm", "c_l")
                    }
                )

        def after(module, args, kwargs, result):
            if self.calls == 1:
                self.response = result.detach().cpu().clone()

        self.handles = [
            self.module.register_forward_pre_hook(before, with_kwargs=True),
            self.module.register_forward_hook(after, with_kwargs=True),
        ]
        return self

    def __exit__(self, *exc):
        for handle in self.handles:
            handle.remove()


def decoder_response(module, packet, pair):
    """Packet already resides on the pair's device; all pair paths remain differentiable.

    c_l contains atom-reference features only and is correctly independent of z.
    Both the direct pair_z path and the atom-pair p_lm path depend on z.
    Caller controls autocast, grad mode, teacher freezing and input-state precision.
    """
    features = packet["input_feature_dict"]
    pair_z = module.diffusion_conditioning.prepare_cache(features["relp"], pair, False)
    fields = (
        "ref_pos",
        "ref_charge",
        "ref_mask",
        "ref_element",
        "ref_atom_name_chars",
        "atom_to_token_idx",
        "d_lm",
        "v_lm",
        "pad_info",
    )
    p_lm, c_l = module.atom_attention_encoder.prepare_cache(
        **{key: features[key] for key in fields}, r_l=True, z=pair_z, inplace_safe=False
    )
    kwargs = dict(packet)
    kwargs.update(z_trunk=None, pair_z=pair_z, p_lm=p_lm, c_l=c_l, inplace_safe=False)
    response = module(**kwargs)
    return response, {"pair_z": pair_z, "p_lm": p_lm, "c_l": c_l}


def coordinate_mse(response, target):
    return (response.double() - target.double()).square().mean()


def direction_statistics(gradient, delta):
    g, d = gradient.double(), delta.double()
    dot = float((g * d).sum())
    gnorm, dnorm = float(g.norm()), float(d.norm())
    return {
        "directional_derivative": dot,
        "update_norm": dnorm,
        "cosine_with_negative_gradient": -dot / (gnorm * dnorm) if gnorm * dnorm else None,
    }


def packet_digest(packet):
    return feature_digest(packet)
