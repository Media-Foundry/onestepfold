"""Runtime-only residual summaries for Stage 1A Protenix recycle analysis.

The overlay keeps only the previous Pairformer output for the current target,
computes compact residual summaries at each recycle transition, and writes one
JSONL record. It never serializes full single/pair representations.
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

    if getattr(InferenceRunner, "_onestepfold_residual_installed", False):
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

    def strip_optional_batch(single, pair):
        """Normalize Protenix hook outputs to [L,C] and [L,L,C]."""
        if single.ndim == 3 and single.shape[0] == 1:
            single = single[0]
        if pair.ndim == 4 and pair.shape[0] == 1:
            pair = pair[0]
        if single.ndim != 2:
            raise ValueError(f"unexpected single representation shape: {tuple(single.shape)}")
        if pair.ndim != 3:
            raise ValueError(f"unexpected pair representation shape: {tuple(pair.shape)}")
        return single, pair

    def residual_summary(single_delta, pair_delta, transition: str) -> dict[str, float | str]:
        single_delta, pair_delta = strip_optional_batch(
            single_delta.detach(), pair_delta.detach()
        )
        single_norm = torch.linalg.vector_norm(single_delta, dim=-1)
        pair_norm = torch.linalg.vector_norm(pair_delta, dim=-1)
        pair_energy = pair_norm.square()
        n_token = pair_norm.shape[0]
        row_energy = pair_energy.mean(dim=-1)
        diag = torch.arange(n_token, device=pair_norm.device)
        index_distance = (diag[:, None] - diag[None, :]).abs()
        total_energy = pair_energy.sum().clamp_min(1e-8)
        pooled_size = min(64, n_token)
        pooled = torch.nn.functional.adaptive_avg_pool2d(
            pair_norm[None, None], (pooled_size, pooled_size)
        )[0, 0]
        singular_values = torch.linalg.svdvals(pooled)
        singular_energy = singular_values.square()
        singular_total = singular_energy.sum().clamp_min(1e-8)
        channel_sample = pair_delta.reshape(-1, pair_delta.shape[-1])
        if channel_sample.shape[0] > 100_000:
            stride = math.ceil(channel_sample.shape[0] / 100_000)
            channel_sample = channel_sample[::stride]
        channel_sample = channel_sample - channel_sample.mean(dim=0, keepdim=True)
        channel_cov = channel_sample.transpose(0, 1) @ channel_sample
        channel_eigenvalues = torch.linalg.eigvalsh(channel_cov).clamp_min(0).flip(0)
        channel_total = channel_eigenvalues.sum().clamp_min(1e-8)

        result: dict[str, float | str] = {
            "transition": transition,
            "single_delta_abs_mean": scalar(single_delta.abs().mean()),
            "single_delta_fro_norm": scalar(torch.linalg.vector_norm(single_delta)),
            "single_delta_residue_norm_mean": scalar(single_norm.mean()),
            "single_delta_residue_norm_std": scalar(single_norm.std(unbiased=False)),
            "single_delta_residue_norm_p90": scalar(torch.quantile(single_norm, 0.90)),
            "single_delta_residue_active_fraction": scalar((single_norm > 1e-3).float().mean()),
            "pair_delta_abs_mean": scalar(pair_delta.abs().mean()),
            "pair_delta_fro_norm": scalar(torch.linalg.vector_norm(pair_delta)),
            "pair_delta_pair_norm_mean": scalar(pair_norm.mean()),
            "pair_delta_pair_norm_std": scalar(pair_norm.std(unbiased=False)),
            "pair_delta_pair_norm_p90": scalar(torch.quantile(pair_norm, 0.90)),
            "pair_delta_pair_active_fraction": scalar((pair_norm > 1e-3).float().mean()),
            "pair_delta_energy_band_1_fraction": scalar(
                pair_energy[index_distance <= 1].sum() / total_energy
            ),
            "pair_delta_energy_band_4_fraction": scalar(
                pair_energy[index_distance <= 4].sum() / total_energy
            ),
            "pair_delta_energy_band_8_fraction": scalar(
                pair_energy[index_distance <= 8].sum() / total_energy
            ),
            "pair_delta_energy_band_16_fraction": scalar(
                pair_energy[index_distance <= 16].sum() / total_energy
            ),
            "pair_delta_row_energy_p90": scalar(torch.quantile(row_energy, 0.90)),
            "pair_delta_pooled_spatial_rank1_energy": scalar(
                singular_energy[:1].sum() / singular_total
            ),
            "pair_delta_pooled_spatial_rank4_energy": scalar(
                singular_energy[:4].sum() / singular_total
            ),
            "pair_delta_pooled_spatial_rank8_energy": scalar(
                singular_energy[:8].sum() / singular_total
            ),
            "pair_delta_pooled_spatial_rank16_energy": scalar(
                singular_energy[:16].sum() / singular_total
            ),
            "pair_delta_channel_rank1_energy": scalar(
                channel_eigenvalues[:1].sum() / channel_total
            ),
            "pair_delta_channel_rank4_energy": scalar(
                channel_eigenvalues[:4].sum() / channel_total
            ),
            "pair_delta_channel_rank8_energy": scalar(
                channel_eigenvalues[:8].sum() / channel_total
            ),
            "pair_delta_channel_rank16_energy": scalar(
                channel_eigenvalues[:16].sum() / channel_total
            ),
        }
        return result

    def init_model(self) -> None:
        original_init_model(self)
        self._onestepfold_residual_cycles = []

        def pairformer_hook(_module, _inputs, output) -> None:
            try:
                single, pair = output
                cycle_index = len(self._onestepfold_residual_cycles) + 1
                current = {
                    "cycle_index": cycle_index,
                    "single_shape": list(single.shape),
                    "pair_shape": list(pair.shape),
                    **tensor_stats("single", single),
                    **tensor_stats("pair", pair),
                }
                if self._onestepfold_residual_cycles:
                    previous_entry = self._onestepfold_residual_cycles[-1]
                    previous = previous_entry.get("_tensors")
                    if previous is None:
                        raise RuntimeError("previous cycle representation is unavailable")
                    current["residual"] = residual_summary(
                        single - previous[0],
                        pair - previous[1],
                        f"c{cycle_index - 1}_to_c{cycle_index}",
                    )
                    previous_entry.pop("_tensors", None)
                    del previous
                current["_tensors"] = (single.detach().clone(), pair.detach().clone())
                self._onestepfold_residual_cycles.append(current)
            except Exception as exc:
                self._onestepfold_residual_cycles.append(
                    {
                        "cycle_index": len(self._onestepfold_residual_cycles) + 1,
                        "feature_error": f"{type(exc).__name__}: {exc}",
                    }
                )

        self.model.pairformer_stack.register_forward_hook(pairformer_hook)

    def predict(self, data):
        self._onestepfold_residual_cycles = []
        result = original_predict(self, data)
        cycles = []
        for cycle in self._onestepfold_residual_cycles:
            serializable = {key: value for key, value in cycle.items() if key != "_tensors"}
            cycles.append(serializable)
        record = {
            "sample_name": str(data.get("sample_name", "unknown")),
            "cycle_count": int(getattr(self.model, "N_cycle", -1)),
            "cycles": cycles,
        }
        output = Path(self.configs.dump_dir) / "residual_features.jsonl"
        with output.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        self._onestepfold_residual_cycles = []
        return result

    InferenceRunner.init_model = init_model
    InferenceRunner.predict = predict
    InferenceRunner._onestepfold_residual_installed = True


_install()
