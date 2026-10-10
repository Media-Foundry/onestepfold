"""Isolate native loader identity before initializing six-rank Gloo."""
import argparse
import os
from pathlib import Path


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--arm',choices=['late','early'],required=True)
    p.add_argument('--seed',type=int,choices=[272001,272003],required=True)
    p.add_argument('--mode',choices=['audit','train'],required=True);a=p.parse_args()
    assert not any(k in os.environ for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES'))
    devices=[int(v) for v in os.environ['HIP_VISIBLE_DEVICES'].split(',')];assert devices==list(range(6))
    from fastglycan.paired_distributed import configure_torchrun_worker
    launch=configure_torchrun_worker(devices)
    from fastglycan.placement_training import run_placement
    from run_recycle_lora import LoRARuntime
    run_placement(a.root,a.arm,a.seed,a.mode,LoRARuntime,launch)
