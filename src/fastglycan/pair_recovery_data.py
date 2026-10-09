"""Separate cached predictor inputs from supervised target pair labels."""
from pathlib import Path
import json
import torch
from fastglycan.paired_teacher_protocol import sha256


class PairRecoveryData:
    def __init__(self, root, expected_manifest):
        self.root=Path(root)
        assert sha256(self.root/'cache_manifest.json')==expected_manifest
        self.records={r['label']:r for r in json.loads((self.root/'cache_manifest.json').read_text())['rows']}
        self.inputs={};self.labels={}

    def base(self, label):
        if label not in self.inputs:
            r=self.records[label];p=self.root/r['path'];assert sha256(p)==r['sha256']
            self.inputs[label]=torch.load(p,map_location='cpu',weights_only=False)['base']
        return tuple(t.cuda() for t in self.inputs[label])

    def target(self, label):
        if label not in self.labels:
            r=self.records[label];p=Path(r['target_path']);assert sha256(p)==r['target_sha256']
            self.labels[label]=torch.load(p,map_location='cpu',weights_only=False)['conditioning'][2]
        return self.labels[label].cuda()
