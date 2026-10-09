"""Observe native block boundaries without changing their tensors or RNG."""
import json
from pathlib import Path
import torch
from fastglycan.paired_teacher_protocol import sha256


class PairStageCapture:
    def __init__(self, stack, indices=(13,14)):
        self.stack, self.indices = stack, tuple(indices)
        self.values, self.handles = {}, []

    def __enter__(self):
        for index in self.indices:
            def observe(module, args, output, index=index):
                if index in self.values:
                    raise RuntimeError('capture is for one recycle only')
                self.values[index] = output[1].detach().clone()
            self.handles.append(self.stack.blocks[index].register_forward_hook(observe))
        return self

    def __exit__(self, *exc):
        for handle in self.handles:
            handle.remove()
        if exc[0] is None and set(self.values) != set(self.indices):
            raise RuntimeError('missing native stage')


class StagePairData:
    def __init__(self, root, expected_manifest):
        self.root = Path(root)
        path = self.root/'stage_manifest.json'
        assert sha256(path) == expected_manifest
        self.records = {r['label']:r for r in json.loads(path.read_text())['records']}
        self.cache = {}

    def load(self, label, *, training=False):
        record = self.records[label]
        if training and record['role'] != 'train':
            raise ValueError('held label access in training')
        if label not in self.cache:
            path = self.root/record['path']; assert sha256(path) == record['sha256']
            self.cache[label] = torch.load(path,map_location='cpu',weights_only=False)
        x = self.cache[label]
        # Teacher hint only leaves this loader when TRAIN loss explicitly asks.
        return x['boundary'].cuda(), x['warm_hint'].cuda(), x['target_hint'].cuda() if training else None
