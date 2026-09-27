"""Bounded Stage 0 confirmation runtime; no target labels enter inference."""

from __future__ import annotations

import copy
import hashlib
import inspect
import itertools
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.teacher_pairing import feature_digest

SETTINGS = {"c4_s5": (4, 5), "c4_s2": (4, 2), "c2_s2": (2, 2)}
ORDERS = list(itertools.permutations(SETTINGS))
MODEL = "protenix_mini_esm_v0.5.0"


def runner_setup(work: Path):
    work.mkdir(parents=True, exist_ok=False)
    os.chdir(work)
    os.environ["LAYERNORM_TYPE"] = "torch"
    from protenix.utils.seed import seed_everything
    from runner.batch_inference import get_default_runner

    seed_everything(101, deterministic=True)
    argv = sys.argv
    try:
        sys.argv = sys.argv[:1]
        runner = get_default_runner(
            seeds=[101],
            n_cycle=4,
            n_step=5,
            n_sample=1,
            dtype="bf16",
            model_name=MODEL,
            use_msa=False,
            use_template=False,
            trimul_kernel="torch",
            triatt_kernel="torch",
            enable_tf32=False,
        )
    finally:
        sys.argv = argv
    # Preserve sampling and MC dropout. Lock deterministic numerical kernels after
    # plain replay showed nondeterminism in the original runtime (archived check).
    assert runner.configs.mc_dropout_apply_rate == 0.4
    assert runner.configs.mc_dropout_rate == 0.4
    assert not runner.configs.deterministic
    runner.configs.deterministic = True
    return runner


def environment(runner) -> dict:
    from protenix.model import generator, protenix
    from protenix.utils import seed
    from runner import batch_inference, inference

    from configs import configs_base, configs_model_type

    modules = (
        generator,
        protenix,
        seed,
        batch_inference,
        inference,
        configs_base,
        configs_model_type,
    )
    runtime = {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "hostname": platform.node(),
        "job_id": os.environ.get("SLURM_JOB_ID"),
        "gpu": torch.cuda.get_device_name(0),
        "matmul_tf32": torch.backends.cuda.matmul.allow_tf32,
        "cudnn_tf32": torch.backends.cudnn.allow_tf32,
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "threads": torch.get_num_threads(),
    }
    runtime["nvidia_smi"] = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,uuid,driver_version,power.limit,clocks.sm,clocks.mem",
            "--format=csv,noheader",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    checkpoint = Path(runner.configs.load_checkpoint_dir) / (MODEL + ".pt")
    esm_checkpoint = Path(runner.configs.load_checkpoint_dir) / "esm2_t36_3B_UR50D.pt"
    return {
        "runtime": runtime,
        "resolved_config": runner.configs.to_dict(),
        "checkpoint_sha256": sha256(checkpoint),
        "esm_checkpoint_sha256": sha256(esm_checkpoint),
        "runtime_source_sha256": {m.__name__: sha256(Path(inspect.getfile(m))) for m in modules},
    }


def seed_prediction(seed: int):
    from protenix.utils.seed import seed_everything

    # Each target/config starts with the same seed label, independent of work order.
    # This is a new paired repeat protocol, not exact replay of old sequential RNG.
    seed_everything(seed, deterministic=True)


def set_setting(runner, setting: str):
    cycles, steps = SETTINGS[setting]
    runner.configs.model.N_cycle = cycles
    runner.model.N_cycle = cycles
    runner.configs.sample_diffusion.N_step = steps
    runner.configs.sample_diffusion.N_sample = 1


class Trace:
    """Observe executed stages without changing inputs, RNG, or solver equations."""

    def __init__(self, model):
        self.model = model
        self.originals = {}
        self.handles = []
        self.reset()

    def reset(self):
        self.record = {"trunk_calls": 0, "denoiser_calls": 0, "stages_seconds": {}}

    def __enter__(self):
        def trunk(module, args):
            self.record["trunk_calls"] += 1

        def decoder(module, args, kwargs):
            self.record["denoiser_calls"] += 1

        self.handles = [
            self.model.pairformer_stack.register_forward_pre_hook(trunk),
            self.model.diffusion_module.register_forward_pre_hook(decoder, with_kwargs=True),
        ]
        for name in ("get_pairformer_output", "sample_diffusion", "run_confidence_head"):
            original = getattr(self.model, name)
            self.originals[name] = original

            def timed(*args, _name=name, _original=original, **kwargs):
                if _name == "sample_diffusion":
                    schedule = kwargs["noise_schedule"]
                    self.record["noise_schedule"] = schedule.detach().float().cpu().tolist()
                    self.record["schedule_dtype"] = str(schedule.dtype)
                    self.record["sample_count"] = int(kwargs["N_sample"])
                    self.record["sampler_parameters"] = {
                        k: self.model.configs.sample_diffusion[k]
                        for k in ("gamma0", "gamma_min", "noise_scale_lambda", "step_scale_eta")
                    }
                if _name == "get_pairformer_output":
                    self.record["mc_dropout_applied"] = bool(kwargs.get("mc_dropout", False))
                torch.cuda.synchronize()
                start = time.perf_counter()
                result = _original(*args, **kwargs)
                torch.cuda.synchronize()
                self.record["stages_seconds"][_name] = time.perf_counter() - start
                return result

            setattr(self.model, name, timed)
        return self

    def __exit__(self, *exc):
        for name, original in self.originals.items():
            setattr(self.model, name, original)
        for handle in self.handles:
            handle.remove()


def predict(runner, data, setting: str, seed: int, trace: Trace | None):
    set_setting(runner, setting)
    seed_prediction(seed)
    prepared = copy.deepcopy(data)
    if trace:
        trace.reset()
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    prediction = runner.predict(prepared)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    coords = prediction["coordinate"].detach().float().cpu().numpy()
    if coords.shape[0] != 1 or not np.isfinite(coords).all():
        raise ValueError("Expected one finite predicted coordinate set")
    record = copy.deepcopy(trace.record) if trace else {}
    record.update(
        {
            "setting": setting,
            "seed": seed,
            "model_forward_seconds": elapsed,
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "coordinate_sha256": hashlib.sha256(coords.tobytes()).hexdigest(),
        }
    )
    if trace:
        cycles, steps = SETTINGS[setting]
        if (record["trunk_calls"], record["denoiser_calls"], record["sample_count"]) != (
            cycles,
            steps,
            1,
        ):
            raise ValueError(f"Executed configuration differs from label: {record}")
    return prediction, coords, record


def save_prediction(root, setting, seed, group, prediction, packet):
    from runner.dumper import DataDumper

    dumper = DataDumper(str(root / setting / f"seed-{seed}"))
    dumper.dump(
        dataset_name="",
        pdb_id=group,
        seed=seed,
        pred_dict=prediction,
        atom_array=packet["atoms"],
        entity_poly_type={
            k: v for k, v in packet["data"]["entity_poly_type"].items() if v != "non-polymer"
        },
    )
    cif = (
        root
        / setting
        / f"seed-{seed}"
        / group
        / f"seed_{seed}"
        / "predictions"
        / (group + "_sample_0.cif")
    )
    return {"cif": str(cif.relative_to(root)), "sha256": sha256(cif)}


def verify_packet(path: Path, expected: dict):
    if sha256(path) != expected["packet_sha256"]:
        raise ValueError("Input packet hash changed")
    packet = torch.load(path, map_location="cpu", weights_only=False)
    if feature_digest(packet["data"]["input_feature_dict"]) != expected["feature_sha256"]:
        raise ValueError("Input feature hash changed")
    return packet


def load_json(path):
    return json.loads(Path(path).read_text())


def write_progress(path, result, start):
    result["elapsed_seconds"] = time.perf_counter() - start
    write_json(path, result)
