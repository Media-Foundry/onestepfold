"""Runtime-only instrumentation of teacher trunk and diffusion RNG boundaries."""

from __future__ import annotations

import hashlib

import torch


def tensor_digest(tensor: torch.Tensor) -> str:
    value = tensor.detach().contiguous().reshape(-1).view(torch.uint8).cpu().numpy()
    digest = hashlib.sha256(str((tensor.dtype, tuple(tensor.shape))).encode())
    digest.update(value.tobytes())
    return digest.hexdigest()


def feature_digest(value) -> str:
    digest = hashlib.sha256()

    def visit(item):
        if isinstance(item, torch.Tensor):
            digest.update(tensor_digest(item).encode())
        elif isinstance(item, dict):
            for key in sorted(item):
                digest.update(str(key).encode())
                visit(item[key])
        elif isinstance(item, (list, tuple)):
            digest.update(str(type(item)).encode())
            for child in item:
                visit(child)
        else:
            digest.update(repr(item).encode())

    visit(value)
    return digest.hexdigest()


class TeacherRNGTrace:
    """Temporarily wrap a teacher instance; never modify installed source files."""

    def __init__(self, model, device: torch.device):
        self.model = model
        self.device = device
        self.diffusion_seed = None
        self.events = []

    def rng_digest(self):
        state = (
            torch.cuda.get_rng_state(self.device)
            if self.device.type == "cuda"
            else torch.get_rng_state()
        )
        return tensor_digest(state)

    def __enter__(self):
        self.original_trunk = self.model.get_pairformer_output
        self.original_diffusion = self.model.sample_diffusion

        def trunk(**kwargs):
            event = {
                "kind": "trunk",
                "cycles": kwargs["N_cycle"],
                "mc_dropout": kwargs["mc_dropout"],
                "input_feature_sha256": feature_digest(kwargs["input_feature_dict"]),
                "rng_before": self.rng_digest(),
            }
            result = self.original_trunk(**kwargs)
            event.update(
                rng_after=self.rng_digest(),
                single_sha256=tensor_digest(result[1]),
                pair_sha256=tensor_digest(result[2]),
            )
            self.events.append(event)
            return result

        def diffusion(**kwargs):
            event = {
                "kind": "diffusion",
                "rng_before_reset": self.rng_digest(),
                "explicit_seed": self.diffusion_seed,
            }
            if self.diffusion_seed is not None:
                torch.manual_seed(self.diffusion_seed)
            event["rng_at_sampler_entry"] = self.rng_digest()
            result = self.original_diffusion(**kwargs)
            event["rng_after"] = self.rng_digest()
            self.events.append(event)
            return result

        self.model.get_pairformer_output = trunk
        self.model.sample_diffusion = diffusion
        return self

    def __exit__(self, *exc):
        self.model.get_pairformer_output = self.original_trunk
        self.model.sample_diffusion = self.original_diffusion
