"""Bounded lazy packet loading and a deterministic update schedule for scaling."""

import json
import math
import random
from functools import lru_cache

import numpy as np
import torch

from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.frame_supervision import training_sampler_seed
from fastglycan.paired_teacher_protocol import sha256
from fastglycan.teacher_pairing import feature_digest


def update_schedule(records, max_steps):
    step, epoch = 0, 0
    while step < max_steps:
        epoch += 1
        order = list(range(len(records)))
        random.Random(101 + epoch).shuffle(order)
        for i in order:
            step += 1
            if step > max_steps:
                return
            r = records[i]
            yield step, epoch, r, training_sampler_seed(r["group_id"], epoch)


def learning_rate(schedule, step, max_steps=32768):
    if schedule == "constant":
        return 1e-4
    if schedule == "lr3":
        return 3e-4
    if schedule == "cosine":
        return 1e-5 + 0.5 * (1e-4 - 1e-5) * (1 + math.cos(math.pi * (step - 1) / (max_steps - 1)))
    raise ValueError("undeclared optimizer schedule")


class PacketStore:
    def __init__(self, root, acceptance):
        self.root = root
        self.hashes = acceptance["prepared_sha256"]
        self.checked = set()
        self.load = lru_cache(maxsize=32)(self._load)

    def _load(self, group):
        folder = self.root / "examples" / group
        info_path = folder / "prepared.json"
        assert sha256(info_path) == self.hashes[group]
        info = json.loads(info_path.read_text())
        if group not in self.checked:
            for name, digest in info["files_sha256"].items():
                assert sha256(folder / name) == digest
            self.checked.add(group)
        data = torch.load(folder / "inputs.pt", map_location="cpu", weights_only=True)
        assert feature_digest(data["features"]) == info["input_provenance"]["feature_sha256"]
        with np.load(folder / "inventory.npz") as saved:
            inventory = dict(saved)
        with np.load(folder / "gt.npz") as saved:
            arrays = dict(saved)
        variant = json.loads((folder / "articulation_report.json").read_text())["variants"]
        adapter = ArticulatedOutput(
            data["features"]["ref_pos"].numpy(),
            inventory["atom_name"],
            inventory["residue_id"],
            info["selection"]["sequence"],
            variant,
        ).float()
        assert feature_digest(adapter.state_dict()) == info["adapter_sha256"]
        sup = torch.load(folder / "supervision.pt", map_location="cpu", weights_only=True)
        return data | {
            "inventory": inventory,
            "arrays": arrays,
            "adapter": adapter.cuda(),
            "supervision": sup,
            "info": info,
        }
