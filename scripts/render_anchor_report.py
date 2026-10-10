"""Render all fixed-node comparisons from completed, verified result exports."""
import argparse
from pathlib import Path
from fastglycan.anchor_reporting import render_anchor_report

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(render_anchor_report(args.root,args.output))
