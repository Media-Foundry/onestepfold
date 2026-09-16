"""Runtime-only timing overlay for the pinned Protenix 1.1.0 runner.

Place this file as ``sitecustomize.py`` ahead of the Protenix site directory in
``PYTHONPATH``. It wraps existing model methods and writes one timing record
per prediction without changing model outputs or checkpoint code.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def _install() -> None:
    try:
        import torch
        from runner.inference import InferenceRunner
    except Exception:
        return

    if getattr(InferenceRunner, "_onestepfold_timing_installed", False):
        return

    original_init_model = InferenceRunner.init_model
    original_predict = InferenceRunner.predict

    def synchronize() -> None:
        if torch.cuda.is_available():
            torch.cuda.synchronize()

    def init_model(self) -> None:
        original_init_model(self)
        self._onestepfold_timing = {}
        for name in ("get_pairformer_output", "sample_diffusion", "run_confidence_head"):
            original = getattr(self.model, name)

            def timed(*args, _name=name, _original=original, **kwargs):
                synchronize()
                started = time.perf_counter()
                result = _original(*args, **kwargs)
                synchronize()
                self._onestepfold_timing[_name] = time.perf_counter() - started
                return result

            setattr(self.model, name, timed)

    def predict(self, data):
        synchronize()
        started = time.perf_counter()
        result = original_predict(self, data)
        synchronize()
        total = time.perf_counter() - started
        stages = dict(getattr(self, "_onestepfold_timing", {}))
        stage_sum = sum(stages.values())
        record = {
            "sample_name": str(data.get("sample_name", "unknown")),
            "model_forward_seconds": total,
            "pairformer_seconds": stages.get("get_pairformer_output"),
            "diffusion_seconds": stages.get("sample_diffusion"),
            "confidence_seconds": stages.get("run_confidence_head"),
            "unattributed_model_seconds": max(0.0, total - stage_sum),
            "cycle_count": int(getattr(self.model, "N_cycle", -1)),
            "step_count": int(self.model.configs.sample_diffusion.get("N_step", -1)),
        }
        try:
            output = Path(self.configs.dump_dir) / "timing_components.jsonl"
            with output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        except Exception:
            # Timing must never turn a valid structure prediction into a failed run.
            pass
        return result

    InferenceRunner.init_model = init_model
    InferenceRunner.predict = predict
    InferenceRunner._onestepfold_timing_installed = True


_install()
