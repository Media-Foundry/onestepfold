"""Runtime-only cycle representation feature overlay for Protenix 1.1.0.

Install as ``sitecustomize.py`` ahead of the pinned Protenix package. The
overlay aggregates single/pair tensors emitted by each Pairformer invocation
and never stores full representations.
"""

from __future__ import annotations

import json
import math
from pathlib import Path


def _install() -> None:
    try:
        import torch
        from runner.inference import InferenceRunner
    except Exception:
        return

    if getattr(InferenceRunner, "_onestepfold_router_installed", False):
        return

    original_init_model = InferenceRunner.init_model
    original_predict = InferenceRunner.predict

    def scalar(value) -> float:
        return float(value.detach().to(dtype=torch.float32).cpu())

    def tensor_stats(prefix: str, tensor) -> dict[str, float]:
        value = tensor.detach()
        variance, mean = torch.var_mean(value, correction=0)
        normalized_norm = torch.linalg.vector_norm(value, dim=-1) / math.sqrt(value.shape[-1])
        norm_variance, norm_mean = torch.var_mean(normalized_norm, correction=0)
        return {
            f"{prefix}_mean": scalar(mean),
            f"{prefix}_std": math.sqrt(max(0.0, scalar(variance))),
            f"{prefix}_abs_mean": scalar(value.abs().mean()),
            f"{prefix}_normalized_norm_mean": scalar(norm_mean),
            f"{prefix}_normalized_norm_std": math.sqrt(max(0.0, scalar(norm_variance))),
        }

    def init_model(self) -> None:
        original_init_model(self)
        self._onestepfold_router_cycles = []

        def pairformer_hook(_module, _inputs, output) -> None:
            try:
                single, pair = output
                features = {
                    "cycle_index": len(self._onestepfold_router_cycles) + 1,
                    "single_shape": list(single.shape),
                    "pair_shape": list(pair.shape),
                    **tensor_stats("single", single),
                    **tensor_stats("pair", pair),
                }
                pair_transpose = pair.transpose(-3, -2)
                features["pair_symmetry_abs_mean"] = scalar((pair - pair_transpose).abs().mean())
                diagonal = pair.diagonal(dim1=-3, dim2=-2).movedim(-1, -2)
                features.update(tensor_stats("pair_diagonal", diagonal))
                self._onestepfold_router_cycles.append(features)
            except Exception as exc:
                self._onestepfold_router_cycles.append(
                    {
                        "cycle_index": len(self._onestepfold_router_cycles) + 1,
                        "feature_error": f"{type(exc).__name__}: {exc}",
                    }
                )

        self.model.pairformer_stack.register_forward_hook(pairformer_hook)

    def predict(self, data):
        self._onestepfold_router_cycles = []
        result = original_predict(self, data)
        record = {
            "sample_name": str(data.get("sample_name", "unknown")),
            "cycle_count": int(getattr(self.model, "N_cycle", -1)),
            "cycles": self._onestepfold_router_cycles,
        }
        output = Path(self.configs.dump_dir) / "router_features.jsonl"
        with output.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return result

    InferenceRunner.init_model = init_model
    InferenceRunner.predict = predict
    InferenceRunner._onestepfold_router_installed = True


_install()
