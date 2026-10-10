"""Adapt an aligned native pair suffix; candidate final single stays frozen."""
import numpy as np
import torch
from torch import nn


class StagePairRecovery(nn.Module):
    """Inputs include the candidate's own block13 pair, never a target state.

    Native blocks14/15 start at their actual execution depth. Zero edit injection
    preserves the original suffix function at initialization; there is no new
    final projection that initially cuts gradients to the pair blocks.
    """
    def __init__(self, native_blocks, seed, input_channels=449, single_channels=384,
                 pair_channels=128, width=128):
        super().__init__()
        if len(native_blocks) != 2:
            raise ValueError('exactly native blocks14/15 required')
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            self.aa = nn.Embedding(20, 16)
            n = input_channels + single_channels + 2 * pair_channels + 33
            self.node = nn.Sequential(nn.LayerNorm(n), nn.Linear(n, width), nn.SiLU(), nn.Linear(width, width))
            self.left = nn.Linear(width, pair_channels, bias=False)
            self.right = nn.Linear(width, pair_channels, bias=False)
            nn.init.zeros_(self.left.weight); nn.init.zeros_(self.right.weight)
            state = np.random.get_state()
            try:
                np.random.seed(seed + 100003)
                self.blocks = nn.ModuleList([type(b)(c_z=pair_channels, c_s=0, dropout=0.) for b in native_blocks])
            finally:
                np.random.set_state(state)
            for source, block in zip(native_blocks, self.blocks):
                original = source.state_dict()
                block.load_state_dict({k: original[k] for k in block.state_dict()}, strict=True)
        self.config = dict(seed=seed, input_channels=input_channels, single_channels=single_channels,
                           pair_channels=pair_channels, width=width, native_indices=[14,15])

    def forward(self, base, boundary, reference_pair, position, old, target):
        if old == target:
            return base, ()
        return self.run_pair_suffix(base, boundary, reference_pair, position, old, target)

    def run_pair_suffix(self, base, boundary, reference_pair, position, old, target):
        """Execute the same suffix even for a reference identity query.

        The public no-edit bypass and all existing parameter/state names remain
        unchanged. A paired reference branch needs the actual trainable function,
        not that bypass, to differentiate through reference drift.
        """
        inputs, single, pair = base
        length = len(single)
        if not 0 <= position < length or boundary.shape != pair.shape or reference_pair.shape != pair.shape:
            raise ValueError('aligned boundary/reference mismatch')
        aa = self.aa(torch.tensor([old,target],device=pair.device)).flatten().expand(length,-1)
        flag = pair.new_zeros(length,1); flag[position] = 1
        h = self.node(torch.cat((inputs,single,reference_pair[position],reference_pair[:,position],aa,flag),-1))
        z = boundary + self.left(h)[:,None,:] + self.right(h)[None,:,:]
        stages = []
        for block in self.blocks:
            _, z = block(None,z,pair_mask=None,triangle_multiplicative='torch',
                         triangle_attention='torch',inplace_safe=False,chunk_size=None)
            stages.append(z)
        return (inputs,single,z), tuple(stages)


def aligned_pair_loss(stages, target_final, target_hint, scale, objective):
    final = (stages[-1] - target_final).square().mean() / scale
    if objective == 'final':
        return final, dict(final=final.detach())
    if objective != 'hint' or target_hint is None:
        raise ValueError('hint objective requires TRAIN-only block14 label')
    hint = (stages[0] - target_hint).square().mean() / scale
    return (final + hint) / 2, dict(final=final.detach(),hint=hint.detach())
