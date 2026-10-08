"""Verify newly authorized evaluation HIP devices against archived zero output."""
import argparse
from pathlib import Path
import numpy as np
import torch
from run_recycle_lora import LoRARuntime
from fastglycan.models.recycle_lora import RecycleLoRA
from fastglycan.paired_teacher_protocol import write_json


def audit_device(source,output):
    rt=LoRARuntime(source,str(output/'work'))
    cp=torch.load(source/'runs/272001/checkpoints/0.pt',map_location='cpu',weights_only=False)
    bank=RecycleLoRA(rt.model.pairformer_stack,**cp['config']).cuda();bank.load_state_dict(cp['state_dict'])
    site=rt.base.sites['p3_s37'];aa=site['candidates'][0]
    with torch.no_grad():
        item,c=rt.conditioning(bank,site,aa)
        expected=np.load(source/'runs/272001/coordinates'/f'0_adapted_{item["label"]}.npz')['coordinates']
        for ni in range(2):assert np.array_equal(rt.base.decode(item,c,ni).cpu().numpy(),expected[ni])
    rt.finish();write_json(output/'device_replay.json',dict(complete=True,runtime=rt.base.runtime,noise_count=2,bitwise=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();audit_device(a.source,a.output)
