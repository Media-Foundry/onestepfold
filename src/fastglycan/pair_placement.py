"""Pinned inputs and native initialization gates for pair-block placement."""
import json
from pathlib import Path

import torch

from fastglycan.models.anchored_pair_recovery import ReferenceAnchoredPairRecovery
from fastglycan.models.early_pair_recovery import EarlyPairRecovery, FrozenPairContinuation
from fastglycan.paired_teacher_protocol import sha256


def placement_lock(root):
    root = Path(root)
    lock = json.loads((root/'training_lock.json').read_text())
    assert sha256(root/'protocol.md') == lock['protocol_sha256']
    for name, digest in lock['code'].items():
        assert sha256(root/'code'/name) == digest, name
    previous = Path(lock['previous_root'])/'training_lock.json'
    assert sha256(previous) == lock['previous_lock_sha256']
    assert lock['arms'] == ['late', 'early'] and lock['seeds'] == [272001, 272003]
    assert lock['checkpoints'] == [0, 32, 128] and lock['gradient_budget'] == 128
    return lock


def placement_model(native, arm, seed):
    blocks = list(native.pairformer_stack.blocks)
    assert len(blocks) == 16
    if arm == 'early':
        continuation = FrozenPairContinuation(blocks[2:])
        net = EarlyPairRecovery(blocks[:2], seed, continuation).cuda()
    elif arm == 'late':
        net = ReferenceAnchoredPairRecovery(blocks[-2:], seed).cuda()
    else:
        raise ValueError(arm)
    assert sum(p.numel() for p in net.parameters()) == 1315332
    assert all(p.requires_grad for p in net.parameters())
    return net


class PairEntryCapture:
    """Observe one actual native block0 input; never synthesize a boundary."""
    def __init__(self, stack):
        self.stack, self.value = stack, None

    def __enter__(self):
        def observe(module, args, kwargs):
            if self.value is not None:
                raise RuntimeError('one-recycle capture was called twice')
            pair = kwargs.get('z', args[1] if len(args) > 1 else None)
            if not isinstance(pair, torch.Tensor):
                raise RuntimeError('missing native pair input')
            self.value = pair.detach().clone()
        self.handle = self.stack.blocks[0].register_forward_pre_hook(observe, with_kwargs=True)
        return self

    def __exit__(self, *exc):
        self.handle.remove()
        if exc[0] is None and self.value is None:
            raise RuntimeError('native block0 was not executed')


class PlacementBoundaries:
    def __init__(self, root, manifest_sha256):
        self.root = Path(root)
        path = self.root/'boundary_manifest.json'
        assert sha256(path) == manifest_sha256
        manifest = json.loads(path.read_text())
        self.candidates = {r['label']: r for r in manifest['candidates']}
        self.references = {r['parent']: r for r in manifest['references']}
        self.cache = {}
        assert len(self.candidates) == 912 and len(self.references) == 24

    def read(self, record):
        name = record['path']
        if name not in self.cache:
            path = self.root/name
            assert sha256(path) == record['sha256']
            self.cache[name] = torch.load(path, map_location='cpu', weights_only=True)
        return self.cache[name]

    def candidate(self, label):
        return self.read(self.candidates[label])['early'].cuda()

    def reference(self, parent, arm):
        return self.read(self.references[parent])[arm].cuda()
