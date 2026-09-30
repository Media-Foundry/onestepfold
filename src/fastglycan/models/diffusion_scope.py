"""Explicit dense training scopes; selecting a scope never changes parameter values."""
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
