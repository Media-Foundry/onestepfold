"""Move the trainable pair computation before a frozen native continuation."""
import numpy as np
import torch
from torch import nn

from fastglycan.models.anchored_pair_recovery import ReferenceAnchoredPairRecovery
from fastglycan.reference_editor_multiref import editor_state_digest


class FrozenPairContinuation:
    """Runtime-owned frozen weights, analogous to the separately owned decoder.

    This object deliberately is not an nn.Module child of the trainable model.
    Optimizer/checkpoint parameters therefore remain exactly the two adapted
    blocks and edit injection. The native checkpoint supplies these frozen
    weights; their separate digest and no-gradient checks are mandatory.
    Autograd through the input is retained: freezing weights is not no_grad.
    """
    def __init__(self, native_blocks, pair_channels=128):
        if not native_blocks:
            raise ValueError('a nonempty frozen native continuation is required')
        source_parameter = next(native_blocks[0].parameters())
        with torch.random.fork_rng(devices=[]):
            numpy_state = np.random.get_state()
            try:
                np.random.seed(701031)
                blocks = [type(block)(c_z=pair_channels, c_s=0, dropout=0.)
                          for block in native_blocks]
            finally:
                np.random.set_state(numpy_state)
        self.blocks = nn.ModuleList(blocks).to(source_parameter).eval().requires_grad_(False)
        for source, block in zip(native_blocks, self.blocks):
            original = source.state_dict()
            block.load_state_dict({key: original[key] for key in block.state_dict()}, strict=True)
        self.initial_digest = editor_state_digest(self.blocks)
        self.calls = 0

    def __call__(self, pair):
        stages = []
        for block in self.blocks:
            _, pair = block(None, pair, pair_mask=None,
                            triangle_multiplicative='torch', triangle_attention='torch',
                            inplace_safe=False, chunk_size=None)
            stages.append(pair)
        self.calls += 1
        return pair, tuple(stages)

    def check_unchanged(self):
        if (any(parameter.requires_grad or parameter.grad is not None
                for parameter in self.blocks.parameters())
                or any(block.training for block in self.blocks)
                or editor_state_digest(self.blocks) != self.initial_digest):
            raise RuntimeError('frozen native continuation changed')


class EarlyPairRecovery(ReferenceAnchoredPairRecovery):
    """Adapt native blocks0/1, then propagate through frozen blocks2..15.

    Boundary is the actual candidate's input to Pairformer block0. Candidate
    final inputs/single remain read-only. Native target intermediate/final
    states are not accepted. Both reference and candidate use the same frozen
    continuation, including its input derivative in the shared pullback.
    """
    def __init__(self, native_blocks, seed, continuation, **kwargs):
        if len(native_blocks) != 2 or len(continuation.blocks) != 14:
            raise ValueError('Mini blocks0/1 plus frozen blocks2..15 required')
        super().__init__(native_blocks, seed, **kwargs)
        self.continuation = continuation
        self.config.update(native_indices=[0, 1], frozen_indices=list(range(2, 16)),
                           boundary='candidate_pre_pairformer',
                           frozen_digest=continuation.initial_digest)

    def run_pair_suffix(self, base, boundary, reference_pair, position, old, target):
        result, stages = super().run_pair_suffix(
            base, boundary, reference_pair, position, old, target)
        pair, remaining = self.continuation(result[2])
        return (result[0], result[1], pair), stages + remaining
