"""Locked continuation schedule and fail-before-copy terminal checkpoint loading."""
import math
import torch

PARENT_SHA256 = '7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829'


def folding_scale_lr(update, settings, total_updates):
    warmup=settings['warmup_updates']
    if not 1 <= update <= total_updates or not 0 < warmup < total_updates:
        raise ValueError('update outside locked schedule')
    if update <= warmup:
        return settings['peak']*update/warmup
    phase=(update-warmup)/(total_updates-warmup)
    return settings['terminal']+.5*(settings['peak']-settings['terminal'])*(1+math.cos(math.pi*phase))


def load_folding_scale_terminal(model, state, *, arm, expected_names, lock_sha256):
    if any(p.requires_grad for p in model.parameters()):
        raise ValueError('freeze native inference model before loading')
    if (state.get('schema')!='folding_scale_continuation_v1' or state.get('arm')!=arm
        or state.get('update')!=2048 or state.get('exposures')!=8192
        or state.get('parent_sha256')!=PARENT_SHA256 or state.get('lock_sha256')!=lock_sha256):
        raise ValueError('wrong continuation terminal or provenance')
    params=dict(model.named_parameters());names=set(expected_names);values=state['trained']
    if not names or set(values)!=names or not names<=params.keys() or not all(n.startswith('diffusion_module.') for n in names):
        raise ValueError('wrong diffusion scope')
    for n in names:
        value=values[n]
        if value.dtype!=params[n].dtype or value.shape!=params[n].shape or not torch.isfinite(value).all():
            raise ValueError('invalid tensor: '+n)
    with torch.no_grad():
        for n in names:params[n].copy_(values[n].to(params[n].device))
