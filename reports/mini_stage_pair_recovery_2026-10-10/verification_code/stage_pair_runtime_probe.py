"""Bounded, no-update reproduction of a slow batch on a spare device."""
import json, time
from pathlib import Path
import torch
from fastglycan.models.stage_pair_recovery import StagePairRecovery, aligned_pair_loss
from fastglycan.stage_pair_data import StagePairData
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.reference_editor_multiref import multiref_update, editor_state_digest
from run_recycle_lora import LoRARuntime

root=Path('/data/user/shuang886/Folding/stage_pair_recovery_v1_20261010/n15')
lock=json.loads((root/'training_lock.json').read_text())
rt=LoRARuntime(Path(lock['source']),str(root/'runtime_probe_work'));b=rt.base
data=PairRecoveryData(lock['build_root'],lock['cache_manifest_sha256'])
stage=StagePairData(lock['stage_root'],lock['stage_manifest_sha256'])
net=StagePairRecovery(list(rt.model.pairformer_stack.blocks[-2:]),272001).cuda().train()
cp=root/'runs/final/272001/checkpoints/4104.pt'
net.load_state_dict(torch.load(cp,map_location='cpu',weights_only=False)['state_dict'])
guard=editor_state_digest(net)
schedule=dict(updates=8208,train_site_keys=lock['train_sites'])
site,aas=multiref_update(schedule,b.sites,1420)
pi,pos=site['parent_index'],site['position_zero_based']
print('PROBE_BATCH',site['site_key'],aas,'checkpoint',str(cp),flush=True)
for aa in aas:
    label=b.label(pi,pos,aa);base=data.base(label);target=data.target(label)
    boundary,_,hint=stage.load(label,training=True)
    start=time.monotonic();print('FORWARD_BEGIN',aa,list(boundary.shape),flush=True)
    c,st=net(base,boundary,rt.prefixes[pi][0][1],pos,b.aa.index(site['original_aa']),b.aa.index(aa))
    torch.cuda.synchronize();print('FORWARD_END',aa,time.monotonic()-start,flush=True)
    loss,_=aligned_pair_loss(st,target,hint,lock['site_scale_squared'][site['site_key']],'final')
    print('BACKWARD_BEGIN',aa,float(loss.detach()),flush=True)
    (loss/2).backward();torch.cuda.synchronize()
    print('BACKWARD_END',aa,time.monotonic()-start,flush=True)
    del c,st,loss,target,base,boundary,hint
assert all(p.grad is None or torch.isfinite(p.grad).all() for p in net.parameters())
assert editor_state_digest(net)==guard
rt.finish();print('PROBE_COMPLETE',b.counts,flush=True)
