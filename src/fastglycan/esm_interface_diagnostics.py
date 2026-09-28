"""Complete early cut: ESM output, tied token features and raw chemistry."""
from .interface_decomposition import CHEMISTRY_NAMES

EARLY_NAMES = ('esm_token_embedding', 'restype') + CHEMISTRY_NAMES


def early_interface(features):
    if features['profile'] is not features['restype']:
        raise ValueError('this fixed-chart protocol requires tied restype/profile')
    return {k: features[k] for k in EARLY_NAMES}


def early_features(fixed, interface, pair_builder=None):
    if pair_builder is None:
        from .models.differentiable_mini import prepare_atom_pairs
        pair_builder = prepare_atom_pairs
    f = dict(fixed) | {k: interface[k] for k in EARLY_NAMES}
    f['profile'] = f['restype']
    return pair_builder(f)


def nested_decomposition(a, early, late, coordinates):
    parts = dict(before_esm_output=early-a,
                 input_embedder_and_pairformer=late-early,
                 diffusion=coordinates-late)
    return dict(a=a, n=early, m=late, d=coordinates, **parts,
                total=coordinates-a, identity_residual=coordinates-a-sum(parts.values()))
