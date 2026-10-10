"""Score one normalized-transport shard or combine the complete fixed cohort."""
import argparse
from pathlib import Path
from fastglycan.transport_normalization_results import score_transport_normalization, summarize_transport_normalization

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--shard',type=int,choices=range(6));a=p.parse_args()
    if a.shard is None:summarize_transport_normalization(a.root)
    else:score_transport_normalization(a.root,a.shard)
