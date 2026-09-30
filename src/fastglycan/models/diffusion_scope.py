"""Explicit dense training scopes; selecting a scope never changes parameter values."""
import torch
from torch import nn


def select_diffusion_scope(model, scope, *, native_trainable_names):
    if any(p.requires_grad for p in model.parameters()):
        raise ValueError('freeze all model parameters before selecting a scope')
    if scope not in {'token_dense', 'diffusion_dense'}:
        raise ValueError('unknown diffusion scope')
    if len(model.diffusion_module.diffusion_transformer.blocks) != 8:
        raise ValueError('expected public Mini eight-block diffusion transformer')
    suffixes = [f'attention_pair_bias.attention.linear_{x}' for x in ['q','k','v','o']]
    suffixes += [f'conditioned_transition_block.linear_nobias_{x}' for x in ['a1','a2','b']]
    names = [f'diffusion_module.diffusion_transformer.blocks.{i}.{s}.weight'
             for i in range(8) for s in suffixes]
    for name in names:
        module = model.get_submodule(name[:-7])
        if not isinstance(module, nn.Linear) or module.weight.ndim != 2:
            raise ValueError('unexpected dense token matrix')
    parameters = dict(model.named_parameters())
    eligible = set(native_trainable_names)
    if not eligible <= parameters.keys() or not set(names) <= eligible:
        raise ValueError('capture native trainable names before freezing the model')
    selected = ({name: parameters[name] for name in names} if scope == 'token_dense'
                else {name: p for name, p in parameters.items() if name.startswith('diffusion_module.') and name in eligible})
    if not selected or len({id(p) for p in selected.values()}) != len(selected):
        raise ValueError('empty or aliased selected parameters')
    for p in selected.values():p.requires_grad_(True)
    return selected


def load_dense_diffusion_checkpoint(model, state, *, arm, expected_names):
    """Validate the whole terminal payload before copying any native weights."""
    if any(p.requires_grad for p in model.parameters()):
        raise ValueError('native inference model must be frozen')
    if (state.get('schema')!='native_dense_diffusion_v1' or state.get('arm')!=arm
            or state.get('update')!=512 or state.get('exposures')!=2048):
        raise ValueError('wrong dense terminal checkpoint contract')
    trained=state['trained'];names=set(expected_names);parameters=dict(model.named_parameters())
    if not names or set(trained)!=names or not names<=parameters.keys():
        raise ValueError('dense checkpoint scope mismatch')
    if not all(n.startswith('diffusion_module.') for n in names):
        raise ValueError('checkpoint attempts to modify the frozen trunk')
    for n in names:
        value=trained[n];parameter=parameters[n]
        if value.shape!=parameter.shape or value.dtype!=parameter.dtype or not torch.isfinite(value).all():
            raise ValueError('invalid dense tensor: '+n)
    with torch.no_grad():
        for n in names:parameters[n].copy_(trained[n].to(parameters[n].device))
