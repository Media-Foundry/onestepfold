"""Run one fixed parent shard of the candidate-first trajectory audit."""
import argparse
from pathlib import Path

from fastglycan.trajectory_audit import run_trajectory_audit
from run_recycle_lora import LoRARuntime


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--shard',type=int,choices=[0,1],required=True);a=p.parse_args()
    run_trajectory_audit(a.root,a.shard,LoRARuntime)
