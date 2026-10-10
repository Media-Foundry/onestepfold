"""torchrun entry: narrow HIP visibility before importing torch or the runtime."""
import argparse
import os
from pathlib import Path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    assert not any(k in os.environ for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    devices = [int(x) for x in os.environ['HIP_VISIBLE_DEVICES'].split(',')]
    assert devices == list(range(6))
    rank = int(os.environ['LOCAL_RANK'])
    assert 0 <= rank < len(devices)
    os.environ['HIP_VISIBLE_DEVICES'] = str(devices[rank])
    from fastglycan.native_parallel_audit import native_parallel_audit
    from run_recycle_lora import LoRARuntime
    native_parallel_audit(args.root, LoRARuntime, devices)
