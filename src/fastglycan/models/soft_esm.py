"""Differentiable amino-acid probabilities through the frozen native ESM2 trunk.

The last-layer representation matches fair-esm at one-hot amino acids (BOS/EOS
included, no padding/mask tokens). No ESM weights or cached features are trained.
"""
from __future__ import annotations
import torch
from torch.utils.checkpoint import checkpoint

AMINO_ACIDS = 'ACDEFGHIKLMNPQRSTVWY'


def soft_esm2(model, alphabet, probabilities, *, checkpoint_layers=True):
    if probabilities.ndim != 2 or probabilities.shape[1] != 20:
        raise ValueError('expected [length,20] probabilities')
    if model.training or any(p.requires_grad for p in model.parameters()):
        raise ValueError('ESM must be frozen and in eval mode')
    weight = model.embed_tokens.weight
    p = probabilities.to(device=weight.device, dtype=weight.dtype)
    ids = torch.tensor([alphabet.get_idx(a) for a in AMINO_ACIDS], device=weight.device)
    residues = p @ weight[ids]
    bos = weight[alphabet.cls_idx][None]
    eos = weight[alphabet.eos_idx][None]
    x = model.embed_scale * torch.cat((bos, residues, eos), dim=0)[None]
    if model.token_dropout:
        # No mask tokens in this probability domain. Match native inference scaling.
        x = x * (1 - .15 * .8)
    x = x.transpose(0, 1)
    for layer in model.layers:
        def forward(value, layer=layer):
            return layer(value, self_attn_padding_mask=None, need_head_weights=False)[0]
        if checkpoint_layers and torch.is_grad_enabled() and x.requires_grad:
            x = checkpoint(forward, x, use_reentrant=False)
        else:
            x = forward(x)
    return model.emb_layer_norm_after(x).transpose(0, 1)[0, 1:-1]


def sequence_probabilities(sequence, *, device=None, dtype=torch.float32):
    indices = torch.tensor([AMINO_ACIDS.index(a) for a in sequence], device=device)
    return torch.nn.functional.one_hot(indices, 20).to(dtype)


def hard_sequence(probabilities):
    return ''.join(AMINO_ACIDS[i] for i in probabilities.detach().argmax(-1).tolist())
