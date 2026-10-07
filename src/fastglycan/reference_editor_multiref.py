"""Matched direct control and deterministic multi-reference experiment schedule."""
import hashlib

import torch
from torch import nn

from fastglycan.reference_editor import ReferenceEditModel


class DirectReferenceEditModel(ReferenceEditModel):
    """Broadcast hard edits globally, then use pointwise residual node MLPs.

    Cache validation, late full-pair writeout and no-edit anchoring are inherited
    unchanged. There are no learned workspace tokens or attention blocks.
    """

    def __init__(self, input_channels, single_channels, pair_channels=128,
                 width=256, workspace=32, blocks=4, heads=8, pair_width=128,
                 pair_chunk=16, direct_hidden=4096):
        super().__init__(input_channels, single_channels, pair_channels, width,
                         workspace, 0, heads, pair_width, pair_chunk)
        del self.workspace
        self.config.update(blocks=blocks, direct_hidden=direct_hidden)
        self.node_blocks = nn.ModuleList([
            nn.Sequential(nn.LayerNorm(width), nn.Linear(width, direct_hidden),
                          nn.SiLU(), nn.Linear(direct_hidden, width))
            for _ in range(blocks)
        ])

    def propagate(self, memory, kv, sequence, edits):
        if kv:
            raise ValueError('direct control has no workspace K/V')
        delta = memory.new_zeros(len(edits), len(sequence), memory.shape[-1])
        for b, candidate in enumerate(edits):
            for position, original, target in candidate:
                ids = torch.tensor([original, target], device=memory.device)
                old, new = self.aa(ids).unbind(0)
                delta[b, position] = self.edit(torch.cat((memory[position], old, new)))
        denominator = memory.new_tensor([max(len(e), 1) for e in edits])[:, None]
        summary = delta.sum(1) / denominator
        nodes = memory[None] + delta + summary[:, None]
        for block in self.node_blocks:
            nodes = nodes + block(nodes)
        # pair_write consumes work.mean(1); one global summary is sufficient.
        return nodes, nodes.mean(1, keepdim=True)


def shared_parameter_name(name):
    return name != 'workspace' and not name.startswith(('blocks.', 'node_blocks.'))


def editor_state_digest(model, shared_only=False):
    h = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        if shared_only and not shared_parameter_name(name):
            continue
        array = value.detach().cpu().contiguous().numpy()
        h.update(str((name, array.shape, array.dtype)).encode())
        h.update(array.tobytes())
    return h.hexdigest()


def paired_reference_editor(architecture, seed, config=None):
    """Construct on CPU without advancing the caller's RNG.

    Common tensors derive from a seed-only template; architecture-specific
    tensors derive from an independent stream. Dataset size is not an input.
    """
    config = dict(config or dict(input_channels=449, single_channels=384))
    if architecture not in ('workspace', 'direct_global'):
        raise ValueError('unknown editor architecture')
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        common_config = {k: v for k, v in config.items() if k != 'direct_hidden'}
        template = ReferenceEditModel(**common_config)
        common = {k: v for k, v in template.state_dict().items() if shared_parameter_name(k)}
        torch.manual_seed(seed + (1000003 if architecture == 'workspace' else 2000003))
        model = (ReferenceEditModel(**common_config) if architecture == 'workspace'
                 else DirectReferenceEditModel(**config))
        state = model.state_dict()
        if any(k not in state or state[k].shape != v.shape for k, v in common.items()):
            raise ValueError('shared parameter schemas differ')
        state.update(common)
        model.load_state_dict(state, strict=True)
    return model


def validate_multiref_plan(plan):
    """Reject leakage, changed AA inventories and budget/schedule drift."""
    sites = {s['site_key']: s for s in plan['sites']}
    if len(sites) != 48 or len(plan['parents']) != 24:
        raise ValueError('expected fixed 24-parent / 48-site archive')
    alphabet = set('ACDEFGHIKLMNPQRSTVWY')
    for site in sites.values():
        if (set(site['candidates']) != alphabet - {site['original_aa']}
                or len(site['candidates']) != 19
                or site['position_zero_based'] + 1 != site['position_one_based']):
            raise ValueError('invalid candidate inventory or position')
    protected = {'p3_s84', 'p4_s25', 'p5_s34'}
    all_train = {k for k, s in sites.items() if s['role_n15'] == 'train'}
    small_train = {k for k, s in sites.items() if s['role_n3'] == 'train'}
    if len(all_train) != 27 or len(small_train) != 5 or not small_train < all_train:
        raise ValueError('invalid nested training sets')
    if protected & all_train or any(sites[k]['parent_index'] == 6 for k in all_train):
        raise ValueError('historical holdout leaked into training')
    if {sites[k]['parent_index'] for k in small_train} != {3, 11, 18}:
        raise ValueError('n3 selection rule changed')
    seen = set()
    for run in plan['runs']:
        if run['run_id'] in seen:
            raise ValueError('duplicate run')
        seen.add(run['run_id'])
        keys = run['train_site_keys']
        expected = small_train if run['run_id'].startswith('n3_') else all_train
        if len(keys) != len(expected) or set(keys) != expected:
            raise ValueError('training membership mismatch')
        ordered = sorted(keys, key=lambda k: (sites[k]['parent_index'], sites[k]['position_zero_based']))
        if keys != ordered:
            raise ValueError('training site order changed')
        if run['updates'] != 608 * len(keys) or run['training_candidate_decodes'] != 2 * run['updates']:
            raise ValueError('training exposure budget changed')
        if run['checkpoints'] != [x * len(keys) for x in (0, 152, 304, 608)]:
            raise ValueError('checkpoint schedule changed')
        if run['seed'] not in (272001, 272003) or run['architecture'] not in ('workspace', 'direct_global'):
            raise ValueError('run design changed')
    if len(seen) != 8 or sum(r['updates'] for r in plan['runs']) != 77824:
        raise ValueError('incomplete run grid')
    return sites


def multiref_update(run, sites, step):
    if not 0 <= step < run['updates']:
        raise ValueError('step outside fixed budget')
    key = run['train_site_keys'][step % len(run['train_site_keys'])]
    visit = step // len(run['train_site_keys'])
    site = sites[key]
    return site, [site['candidates'][(2 * visit + j) % 19] for j in range(2)]
