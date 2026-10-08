"""Fixed-budget Mini candidate last-recycle adaptation, no external compensator."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import time

import numpy as np
import torch

from fastglycan.models.recycle_lora import RecycleLoRA
from fastglycan.models.compensated_recycle import initialize_cached_recycle, native_recycle_step
from fastglycan.models.prefix_recycle import capture_rng_state, restore_rng_state
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_multiref import editor_state_digest, multiref_update
from run_compensated_recycle import CompensationRuntime
from run_reference_editor import coordinate_objective, state_hash


def lora_lock(root):
    lock = json.loads((root/'lora_lock.json').read_text())
    for path, digest in lock['code'].items(): assert sha256(root/'audit_code'/path)==digest, path
    assert sha256(root/'protocol.md')==lock['protocol_sha256']
    for path, digest in lock['source_files'].items(): assert sha256(Path(lock['source_root'])/path)==digest,path
    assert lock['seeds']==[272001,272003] and lock['updates']==8208
    assert lock['checkpoints']==[0,4104,8208] and lock['rank']==16
    return lock


class LoRARuntime:
    def __init__(self, root, name):
        self.root = root; self.lock = lora_lock(root)
        self.native = CompensationRuntime(Path(self.lock['native_root']), str(root/name))
        self.base = self.native.base; self.model = self.native.model
        self.prefixes = self.native.prefixes; self.preflight = self.native.preflight
        self.candidate_input = self.native.candidate_input
        # Hooks exist only in candidate forward. Disable native backward replay;
        # inference already sets this to None when gradients are disabled.
        self.model.pairformer_stack.blocks_per_ckpt = None

    def conditioning(self, bank, site, aa):
        item = self.base.item(site['parent_index'],site['position_zero_based'],aa)
        with torch.no_grad():
            init = initialize_cached_recycle(self.model,item['features'],self.candidate_input(item))
        state,rng = self.prefixes[site['parent_index']]
        ambient = capture_rng_state()
        try:
            with bank.candidate(self.model.pairformer_stack) if bank is not None else nullcontext():
                final = native_recycle_step(self.model,item['features'],init,state,rng=rng)
        finally:
            restore_rng_state(ambient)
        return item,(init.inputs,*final)

    def finish(self):
        self.native.finish(); lora_lock(self.root)
        for block in self.model.pairformer_stack.blocks:
            for kind in ('pair_transition','single_transition'):
                assert not getattr(block,kind).linear_no_bias._forward_hooks


def check_lora_preflight(root):
    begin=time.monotonic();rt=LoRARuntime(root,'lora_prepare_work');b=rt.base
    result=dict(complete=False,seeds=[],zero_replays=0)
    guards={pi:state_hash(x[0]) for pi,x in rt.prefixes.items()}
    for seed in rt.lock['seeds']:
        torch.manual_seed(seed);bank=RecycleLoRA(rt.model.pairformer_stack,rt.lock['rank']).cuda()
        initial=editor_state_digest(bank)
        # All archived candidates, both noises, tested before any optimization.
        with torch.no_grad():
            for site in b.plan['sites']:
                for aa in site['candidates']:
                    item,c=rt.conditioning(bank,site,aa)
                    record=rt.preflight['baseline'][item['label']]
                    path=Path(rt.lock['native_root'])/record['path'];assert sha256(path)==record['sha256']
                    expected=np.load(path)['coordinates']
                    for ni in range(2): assert np.array_equal(b.decode(item,c,ni).cpu().numpy(),expected[ni])
                    result['zero_replays']+=1
                print('ZERO_REPLAY',seed,site['site_key'],flush=True)
        opt=torch.optim.AdamW(bank.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8)
        site=b.sites['p3_s37'];aa=site['candidates'][0];gradients=[]
        for step in range(2):
            opt.zero_grad(set_to_none=True);item,c=rt.conditioning(bank,site,aa)
            loss=coordinate_objective(b.decode(item,c,0),item['teacher'][0],item['ca'],item['labels'])[0]
            loss.backward()
            norms={n:float(p.grad.norm()) if p.grad is not None else None for n,p in bank.named_parameters()}
            assert all(v is not None and np.isfinite(v) for v in norms.values())
            assert all(v>0 for n,v in norms.items() if '.up.' in n or step==1),norms
            gradients.append(norms);torch.nn.utils.clip_grad_norm_(bank.parameters(),1.,error_if_nonfinite=True);opt.step()
        with torch.no_grad():
            item,c=rt.conditioning(None,site,aa)
            expected=np.load(Path(rt.lock['native_root'])/rt.preflight['baseline'][item['label']]['path'])['coordinates']
            for ni in range(2): assert np.array_equal(b.decode(item,c,ni).cpu().numpy(),expected[ni])
            _,a=rt.conditioning(bank,site,aa);rt.conditioning(bank,site,site['candidates'][-1]);_,again=rt.conditioning(bank,site,aa)
            assert all(torch.equal(x,y) for x,y in zip(a,again))
            # No-edit uses the original path by contract, never an adapted WT.
            for pi,(state,rng) in rt.prefixes.items():
                wt=b.item(pi);ini=initialize_cached_recycle(rt.model,wt['features'],b.references[pi][0])
                final=native_recycle_step(rt.model,wt['features'],ini,state,rng=rng)
                assert all(torch.equal(x,y) for x,y in zip(final,b.references[pi][1:]))
        result['seeds'].append(dict(seed=seed,initial_sha256=initial,gradients=gradients,
                                   parameters=sum(p.numel() for p in bank.parameters()),paths=bank.paths))
        del bank,opt,loss,c,a,again
    assert guards=={pi:state_hash(x[0]) for pi,x in rt.prefixes.items()}
    rt.finish();result.update(complete=True,seconds=time.monotonic()-begin,counts=b.counts,runtime=b.runtime,
                             discarded_dry_updates=4,peak_allocated_bytes=torch.cuda.max_memory_allocated())
    write_json(root/'lora_preflight.json',result)


def evaluate_lora(rt,bank,opt,out,step,seed):
    begin=time.monotonic();bank.eval();records=[]
    with torch.no_grad():
        for site in rt.base.plan['sites']:
            for aa in site['candidates']:
                item,c=rt.conditioning(bank,site,aa)
                xyz=np.stack([rt.base.decode(item,c,ni).cpu().numpy() for ni in range(2)])
                assert np.isfinite(xyz).all()
                if step==0:
                    record=rt.preflight['baseline'][item['label']]
                    assert np.array_equal(xyz,np.load(Path(rt.lock['native_root'])/record['path'])['coordinates'])
                path=out/'coordinates'/f'{step}_adapted_{item["label"]}.npz'
                np.savez_compressed(path,coordinates=xyz)
                records.append(dict(path=str(path.relative_to(out)),sha256=sha256(path),label=item['label'],arm='adapted'))
    cp=out/'checkpoints'/f'{step}.pt'
    torch.save(dict(state_dict=bank.state_dict(),optimizer=opt.state_dict(),step=step,seed=seed,config=bank.config,
                    lock_sha256=sha256(rt.root/'lora_lock.json')),cp)
    result=dict(step=step,predictions=records,checkpoint=str(cp.relative_to(out)),sha256=sha256(cp),seconds=time.monotonic()-begin)
    write_json(out/f'evaluation_{step}.json',result);print('EVALUATE',seed,step,rt.base.counts,flush=True)
    return {k:v for k,v in result.items() if k!='predictions'}


def train_lora(root,seed):
    begin=time.monotonic();rt=LoRARuntime(root,f'lora_work_{seed}');b=rt.base
    pre=json.loads((root/'lora_preflight.json').read_text());assert pre['complete']
    assert seed in rt.lock['seeds']
    out=root/'runs'/str(seed);out.mkdir(parents=True,exist_ok=False)
    (out/'coordinates').mkdir();(out/'checkpoints').mkdir()
    torch.manual_seed(seed);bank=RecycleLoRA(rt.model.pairformer_stack,rt.lock['rank']).cuda()
    initial=editor_state_digest(bank)
    assert initial==next(x['initial_sha256'] for x in pre['seeds'] if x['seed']==seed)
    opt=torch.optim.AdamW(bank.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8)
    run=dict(updates=8208,train_site_keys=sorted([s['site_key'] for s in b.plan['sites'] if s['role_n15']=='train'],
              key=lambda k:(b.sites[k]['parent_index'],b.sites[k]['position_zero_based'])))
    assert len(run['train_site_keys'])==27
    guards={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    report=dict(complete=False,seed=seed,initial_sha256=initial,counts=b.counts,evaluations=[],runtime=b.runtime,
                parameters=sum(p.numel() for p in bank.parameters()),updates=8208,train_site_keys=run['train_site_keys'])
    exposure={k:{aa:0 for aa in b.sites[k]['candidates']} for k in run['train_site_keys']}
    report['evaluations'].append(evaluate_lora(rt,bank,opt,out,0,seed));write_json(out/'report.json',report)
    with (out/'history.jsonl').open('w',buffering=1) as history:
        for step in range(8208):
            bank.train();opt.zero_grad(set_to_none=True);site,choices=multiref_update(run,b.sites,step);components=[]
            for aa in choices:
                item,c=rt.conditioning(bank,site,aa);x=b.decode(item,c,0)
                loss,values=coordinate_objective(x,item['teacher'][0],item['ca'],item['labels'])
                assert torch.isfinite(loss);(loss/2).backward();components.append(values)
                exposure[site['site_key']][aa]+=1;del x,c,loss
            norm=torch.nn.utils.clip_grad_norm_(bank.parameters(),1.,error_if_nonfinite=True)
            opt.step();b.counts['updates']+=1
            history.write(json.dumps(dict(step=step+1,site=site['site_key'],aa=choices,components=components,
                                         gradient_norm=float(norm),clipped=bool(norm>1)),allow_nan=False)+'\n')
            if (step+1)%128==0:
                report['seconds']=time.monotonic()-begin;write_json(out/'report.json',report)
                print('TRAIN',seed,step+1,report['seconds'],flush=True)
            if step+1 in rt.lock['checkpoints']:
                report['evaluations'].append(evaluate_lora(rt,bank,opt,out,step+1,seed))
                write_json(out/f'exposure_{step+1}.json',exposure);write_json(out/'report.json',report)
    assert all(v==32 for row in exposure.values() for v in row.values())
    assert guards=={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    rt.finish();report.update(complete=True,seconds=time.monotonic()-begin,exposure=exposure,
         history_sha256=sha256(out/'history.jsonl'),peak_allocated_bytes=torch.cuda.max_memory_allocated())
    write_json(out/'report.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['preflight','train'],required=True);p.add_argument('--seed',type=int)
    a=p.parse_args();begin=time.monotonic();status=a.root/('prepare_execution.json' if a.mode=='preflight' else f'execution_{a.seed}.json')
    try:
        check_lora_preflight(a.root) if a.mode=='preflight' else train_lora(a.root,a.seed)
        write_json(status,dict(complete=True,seconds=time.monotonic()-begin))
    except BaseException as e:
        write_json(status,dict(complete=False,error=repr(e),seconds=time.monotonic()-begin));raise
