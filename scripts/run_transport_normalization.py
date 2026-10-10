"""Run a fixed no-training transport-coordinate diagnostic shard."""
import argparse
from pathlib import Path
from fastglycan.transport_normalization_audit import run_transport_normalization_audit
from run_recycle_lora import LoRARuntime

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--shard',type=int,choices=range(6),required=True)
    args=parser.parse_args()
    run_transport_normalization_audit(args.root,args.shard,LoRARuntime)
