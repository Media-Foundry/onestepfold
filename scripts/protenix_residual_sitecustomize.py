"""Runtime-only residual summaries for Stage 1A Protenix recycle analysis.

The overlay keeps only the previous Pairformer output for the current target,
computes compact residual summaries at each recycle transition, and writes one
JSONL record. It never serializes full single/pair representations.
"""

from __future__ import annotations

import json
import math
import os
import re
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

    def direction_cosine(left, right) -> float:
        left = left.detach().float().cpu().reshape(-1)
        right = right.detach().float().cpu().reshape(-1)
        denominator = torch.linalg.vector_norm(left) * torch.linalg.vector_norm(right)
        if scalar(denominator) <= 1e-12:
            return float("nan")
        return scalar(torch.dot(left, right) / denominator)

    sketch_enabled = os.environ.get("ONESTEPFOLD_SIGNED_SKETCH", "0") == "1"
    sketch_size = int(os.environ.get("ONESTEPFOLD_SKETCH_SIZE", "64"))
    sketch_channels = int(os.environ.get("ONESTEPFOLD_SKETCH_CHANNELS", "16"))
    sketch_projection_cache: dict[int, object] = {}

    def signed_pair_sketch(pair, path: Path) -> None:
        """Persist a deterministic signed, spatially pooled pair sketch."""
        import numpy as np

        pair = pair.detach()
        if pair.ndim == 4 and pair.shape[0] == 1:
            pair = pair[0]
        pair = pair.float().cpu()
        channels = int(pair.shape[-1])
        projection = sketch_projection_cache.get(channels)
        if projection is None:
            generator = torch.Generator(device="cpu").manual_seed(1729 + channels)
            projection = torch.randn(
                channels, sketch_channels, generator=generator, dtype=torch.float32
            ) / math.sqrt(sketch_channels)
            sketch_projection_cache[channels] = projection
        projected = pair.reshape(-1, channels) @ projection
        projected = projected.reshape(pair.shape[0], pair.shape[1], sketch_channels)
        pooled = torch.nn.functional.adaptive_avg_pool2d(
            projected.permute(2, 0, 1)[None], (sketch_size, sketch_size)
        )[0]
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            sketch=pooled.numpy().astype(np.float16),
            original_shape=np.asarray(pair.shape, dtype=np.int64),
            projection_seed=np.asarray([1729 + channels], dtype=np.int64),
        )

    def residual_summary(
        single_delta,
        pair_delta,
        transition: str,
        previous_single_delta=None,
        previous_pair_delta=None,
    ) -> dict[str, float | str]:
        single_delta, pair_delta = strip_optional_batch(
            single_delta.detach(), pair_delta.detach()
        )
        # Keep diagnostic linear algebra backend-independent. Protenix runs in
        # BF16 on CUDA, while SVD/eigh support differs across GPU generations.
        single_delta = single_delta.float().cpu()
        pair_delta = pair_delta.float().cpu()
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
            pair_norm.float()[None, None], (pooled_size, pooled_size)
        )[0, 0]
        singular_values = torch.linalg.svdvals(pooled)
        singular_energy = singular_values.square()
        singular_total = singular_energy.sum().clamp_min(1e-8)
        # CUDA eigvalsh has no BF16 implementation on some supported GPUs.
        channel_sample = pair_delta.float().reshape(-1, pair_delta.shape[-1])
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
        if previous_single_delta is not None and previous_pair_delta is not None:
            result["single_delta_direction_cosine"] = direction_cosine(
                single_delta, previous_single_delta
            )
            result["pair_delta_direction_cosine"] = direction_cosine(
                pair_delta, previous_pair_delta
            )
        return result

    def init_model(self) -> None:
        original_init_model(self)
        self._onestepfold_residual_cycles = []
        self._onestepfold_previous_delta = None

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
                sketch_root = Path(self.configs.dump_dir) / "signed_sketches"
                if sketch_enabled and cycle_index in (2, 4):
                    sample_name = re.sub(
                        r"[^A-Za-z0-9_.-]+",
                        "_",
                        getattr(self, "_onestepfold_sample_name", "unknown"),
                    )
                    state_path = sketch_root / f"{sample_name}_c{cycle_index}_pair_state.npz"
                    signed_pair_sketch(pair, state_path)
                    current["signed_pair_state_sketch_path"] = str(state_path)
                if self._onestepfold_residual_cycles:
                    previous_entry = self._onestepfold_residual_cycles[-1]
                    previous = previous_entry.get("_tensors")
                    if previous is None:
                        raise RuntimeError("previous cycle representation is unavailable")
                    previous_delta = self._onestepfold_previous_delta
                    single_delta = single - previous[0]
                    pair_delta = pair - previous[1]
                    current["residual"] = residual_summary(
                        single_delta,
                        pair_delta,
                        f"c{cycle_index - 1}_to_c{cycle_index}",
                        None if previous_delta is None else previous_delta[0],
                        None if previous_delta is None else previous_delta[1],
                    )
                    if sketch_enabled:
                        sample_name = re.sub(
                            r"[^A-Za-z0-9_.-]+",
                            "_",
                            getattr(self, "_onestepfold_sample_name", "unknown"),
                        )
                        transition = current["residual"]["transition"]
                        delta_path = sketch_root / f"{sample_name}_{transition}_pair_delta.npz"
                        signed_pair_sketch(pair_delta, delta_path)
                        current["residual"]["signed_pair_delta_sketch_path"] = str(delta_path)
                    previous_entry.pop("_tensors", None)
                    del previous
                    self._onestepfold_previous_delta = (
                        single_delta.detach(),
                        pair_delta.detach(),
                    )
                current["_tensors"] = (single.detach().clone(), pair.detach().clone())
                self._onestepfold_residual_cycles.append(current)
            except Exception as exc:
                self._onestepfold_residual_cycles.append(
                    {
                        "cycle_index": len(self._onestepfold_residual_cycles) + 1,
                        "feature_error": f"{type(exc).__name__}: {exc}",
                        "single_shape": list(single.shape),
                        "pair_shape": list(pair.shape),
                        "_tensors": (single.detach().clone(), pair.detach().clone()),
                    }
                )

        self.model.pairformer_stack.register_forward_hook(pairformer_hook)

    def predict(self, data):
        self._onestepfold_residual_cycles = []
        self._onestepfold_previous_delta = None
        self._onestepfold_sample_name = str(data.get("sample_name", "unknown"))
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
        self._onestepfold_previous_delta = None
        return result

    InferenceRunner.init_model = init_model
    InferenceRunner.predict = predict
    InferenceRunner._onestepfold_residual_installed = True


_install()
