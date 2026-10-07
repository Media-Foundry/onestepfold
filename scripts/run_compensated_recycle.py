"""Locked Mini WT3 correction + one native target recycle, no input preparation."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

from fastglycan.models.compensated_recycle import (
    RecycleCompensator, initialize_cached_recycle, native_recycle_step, capture_cached_prefix,
)
from fastglycan.models.prefix_recycle import capture_rng_state, restore_rng_state
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_runtime import MiniEditorRuntime
from fastglycan.reference_editor_multiref import editor_state_digest, multiref_update
from fastglycan.reference_editor_intervention import fixed_candidate_derangement
from run_reference_editor import coordinate_objective, state_hash


def read_lock(root):
    lock = json.loads((root/'compensation_lock.json').read_text())
    for p, digest in lock['code'].items():
        assert sha256(root/'audit_code'/p) == digest, p
    assert sha256(root/'protocol.md') == lock['protocol_sha256']
    for p, digest in lock['source_files'].items():
        assert sha256(Path(lock['source_root'])/p) == digest, p
    assert lock['updates'] == 8208 and lock['checkpoints'] == [0,4104,8208]
    assert lock['seeds'] == [272001,272003]
    return lock


class CompensationRuntime:
    def __init__(self, root, name, preparation=False):
        self.root = root
        self.lock = read_lock(root)
        self.base = MiniEditorRuntime(root, name)
        self.model = self.base.decoder
        # Replace ONLY this experiment's prohibition hook with a real cycle count.
        self.base.handles[0].remove()
        self.base.counts['recycle'] = 0
        self.cycle_handle = self.model.pairformer_stack.register_forward_hook(self.count_cycle)
        self.prefixes = {}
        self.inputs = {}
        self.preparation = preparation
        self.native_digest = state_hash(tuple(self.model.parameters()))
        if not preparation:
            self.preflight = json.loads((root/'compensation_preflight.json').read_text())
            assert self.preflight['complete']
            for pi, record in self.preflight['prefixes'].items():
                path = root/record['path']; assert sha256(path) == record['sha256']
                x = torch.load(path, map_location='cpu', weights_only=False)
                self.prefixes[int(pi)] = (tuple(t.cuda() for t in x['state']), x['rng'])

    def count_cycle(self, *args):
        self.base.counts['recycle'] += 1

    def candidate_input(self, item):
        label = item['label']
        if label not in self.inputs:
            record = self.preflight['inputs'][label]
            path = self.root/record['path']; assert sha256(path) == record['sha256']
            x = torch.load(path, map_location='cpu', weights_only=True)
            assert isinstance(x, torch.Tensor) and x.ndim == 2 and x.shape[-1] == 449
            self.inputs[label] = x
        return self.inputs[label].cuda()

    def conditioning(self, net, site, actual_aa, query_aa=None):
        pi, pos = site['parent_index'], site['position_zero_based']
        item = self.base.item(pi,pos,actual_aa)
        with torch.no_grad():
            init = initialize_cached_recycle(self.model,item['features'],self.candidate_input(item))
        state, rng = self.prefixes[pi]
        original = self.base.aa.index(site['original_aa'])
        corrected = state if net is None else net(state,pos,original,self.base.aa.index(query_aa or actual_aa))
        ambient = capture_rng_state()
        try:
            final = native_recycle_step(self.model,item['features'],init,corrected,rng=rng)
        finally:
            restore_rng_state(ambient)
        return item, (init.inputs, *final)

    def finish(self):
        self.base.finish_checks()
        assert state_hash(tuple(self.model.parameters())) == self.native_digest
        read_lock(self.root)


def save_tensor(root, path, data):
    path = root/path
    path.parent.mkdir(parents=True,exist_ok=True)
    torch.save(data,path)
    return dict(path=str(path.relative_to(root)),sha256=sha256(path))


def native_preflight(root):
    started=time.monotonic(); rt=CompensationRuntime(root,'prepare_work',True); b=rt.base
    report=dict(complete=False,prefixes={},inputs={},baseline={},candidate_replays=[],wt_replays=[],gradients=[])
    with torch.no_grad():
        for pi, reference in b.references.items():
            item=b.item(pi); init=initialize_cached_recycle(rt.model,item['features'],reference[0])
            prefix,rng=capture_cached_prefix(rt.model,item['features'],init)
            final=native_recycle_step(rt.model,item['features'],init,prefix,rng=rng)
            assert all(torch.equal(x,y) for x,y in zip(final,reference[1:])),(pi,'WT cached C4')
            for ni in range(2):
                assert torch.equal(b.decode(item,(init.inputs,*final),ni),item['teacher'][ni])
            rt.prefixes[pi]=(prefix,rng)
            report['prefixes'][str(pi)]=save_tensor(root,f'prefixes/{pi}.pt',dict(state=tuple(t.cpu() for t in prefix),rng=rng))
            report['wt_replays'].append(pi)
        for site in b.plan['sites']:
            pi,pos=site['parent_index'],site['position_zero_based']
            state,rng=rt.prefixes[pi];guard=state_hash(state)
            for aa in site['candidates']:
                item=b.item(pi,pos,aa);label=item['label']
                # Audit-only target final tensors are never retained as model inputs.
                archived=torch.load(b.store.path(pi,label,'conditioning.pt'),map_location='cpu',weights_only=False)
                target_input=archived['conditioning'][0].cuda()
                report['inputs'][label]=save_tensor(root,f'inputs/{label}.pt',target_input.cpu())
                init=initialize_cached_recycle(rt.model,item['features'],target_input)
                target3,target_rng=capture_cached_prefix(rt.model,item['features'],init)
                target4=native_recycle_step(rt.model,item['features'],init,target3,rng=target_rng)
                assert all(torch.equal(x.cpu(),y) for x,y in zip(target4,archived['conditioning'][1:])),(label,'cached target C4')
                for ni in range(2):
                    assert torch.equal(b.decode(item,(target_input,*target4),ni),item['teacher'][ni]),label
                del archived,target3,target4,target_rng
                warm=native_recycle_step(rt.model,item['features'],init,state,rng=rng)
                xyz=np.stack([b.decode(item,(target_input,*warm),ni).cpu().numpy() for ni in range(2)])
                path=root/'unadapted'/f'{label}.npz';path.parent.mkdir(exist_ok=True)
                np.savez_compressed(path,coordinates=xyz)
                report['baseline'][label]=dict(path=str(path.relative_to(root)),sha256=sha256(path))
                report['candidate_replays'].append(label)
                del warm,init,target_input
            assert state_hash(state)==guard
            report['seconds']=time.monotonic()-started
            write_json(root/'compensation_preflight.json',report)
            print('PREFLIGHT_SITE',site['site_key'],b.counts,flush=True)
    rt.preflight=report
    for seed in rt.lock['seeds']:
        torch.manual_seed(seed);net=RecycleCompensator().cuda()
        digest=editor_state_digest(net);site=b.sites['p3_s37'];aa=site['candidates'][0]
        with torch.no_grad():
            item,c=rt.conditioning(net,site,aa)
            expected=np.load(root/report['baseline'][item['label']]['path'])['coordinates']
            for ni in range(2): assert np.array_equal(b.decode(item,c,ni).cpu().numpy(),expected[ni])
        opt=torch.optim.AdamW(net.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8)
        audit=[]
        for step in range(2):
            opt.zero_grad();item,c=rt.conditioning(net,site,aa)
            x=b.decode(item,c,0);loss=coordinate_objective(x,item['teacher'][0],item['ca'],item['labels'])[0]
            loss.backward()
            norms={n:float(p.grad.norm()) if p.grad is not None else None for n,p in net.named_parameters()}
            assert all(v is not None and np.isfinite(v) for v in norms.values())
            for n in ['single_out.weight','pair_out.weight']+(['aa.weight','relation.1.weight'] if step else []): assert norms[n]>0,(n,norms)
            audit.append(norms);torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True);opt.step()
        with torch.no_grad():
            state=rt.prefixes[3][0];old=b.aa.index(site['original_aa'])
            assert net(state,36,old,old) is state
            _,c1=rt.conditioning(net,site,aa)
            rt.conditioning(net,site,site['candidates'][1])
            _,c2=rt.conditioning(net,site,aa)
            assert all(torch.equal(x,y) for x,y in zip(c1,c2))
        report['gradients'].append(dict(seed=seed,initial_sha256=digest,norms=audit,parameters=sum(p.numel() for p in net.parameters())))
        del net,opt,c,x,loss,c1,c2
    assert len(report['candidate_replays'])==912 and len(report['wt_replays'])==24
    rt.finish(); report.update(complete=True,seconds=time.monotonic()-started,counts=b.counts,runtime=b.runtime,
                              peak_allocated_bytes=torch.cuda.max_memory_allocated())
    write_json(root/'compensation_preflight.json',report)
    print('PREFLIGHT_COMPLETE',report['seconds'],b.counts,flush=True)


def evaluate_compensation(rt,net,opt,output,step,seed):
    net.eval();records=[];begin=time.monotonic()
    with torch.no_grad():
        for site in rt.base.plan['sites']:
            donors=fixed_candidate_derangement(site['site_key'],site['candidates'])
            for ai,aa in enumerate(site['candidates']):
                for arm,query in [('correct',aa),('wrong',site['candidates'][donors[ai]])]:
                    item,c=rt.conditioning(net,site,aa,query)
                    xyz=np.stack([rt.base.decode(item,c,ni).cpu().numpy() for ni in range(2)])
                    assert np.isfinite(xyz).all()
                    if step==0:
                        expected=np.load(rt.root/rt.preflight['baseline'][item['label']]['path'])['coordinates']
                        assert np.array_equal(xyz,expected),(item['label'],arm,'zero baseline')
                    path=output/'coordinates'/f'{step}_{arm}_{item["label"]}.npz'
                    np.savez_compressed(path,coordinates=xyz)
                    records.append(dict(path=str(path.relative_to(output)),sha256=sha256(path),label=item['label'],arm=arm))
                    del c
    cp=output/'checkpoints'/f'{step}.pt'
    torch.save(dict(state_dict=net.state_dict(),optimizer=opt.state_dict(),step=step,seed=seed,
                    config=net.config,lock_sha256=sha256(rt.root/'compensation_lock.json')),cp)
    result=dict(step=step,predictions=records,checkpoint=str(cp.relative_to(output)),sha256=sha256(cp),seconds=time.monotonic()-begin)
    write_json(output/f'evaluation_{step}.json',result)
    print('EVALUATE',seed,step,rt.base.counts,flush=True)
    return {k:v for k,v in result.items() if k!='predictions'}


def train_compensation(root,seed):
    begin=time.monotonic();rt=CompensationRuntime(root,f'work_{seed}');b=rt.base
    assert seed in rt.lock['seeds']
    output=root/'runs'/str(seed);output.mkdir(parents=True,exist_ok=False)
    (output/'coordinates').mkdir();(output/'checkpoints').mkdir()
    torch.manual_seed(seed);net=RecycleCompensator().cuda()
    initial=editor_state_digest(net)
    expected=next(r for r in rt.preflight['gradients'] if r['seed']==seed)
    assert initial==expected['initial_sha256']
    opt=torch.optim.AdamW(net.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8)
    run=dict(updates=rt.lock['updates'],train_site_keys=sorted([s['site_key'] for s in b.plan['sites'] if s['role_n15']=='train'],
                                   key=lambda k:(b.sites[k]['parent_index'],b.sites[k]['position_zero_based'])))
    assert len(run['train_site_keys'])==27
    prefix_hash={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    report=dict(complete=False,seed=seed,initial_sha256=initial,counts=b.counts,evaluations=[],runtime=b.runtime,
                parameters=sum(p.numel() for p in net.parameters()),updates=rt.lock['updates'],train_site_keys=run['train_site_keys'])
    exposure={k:{a:0 for a in b.sites[k]['candidates']} for k in run['train_site_keys']}
    report['evaluations'].append(evaluate_compensation(rt,net,opt,output,0,seed))
    write_json(output/'report.json',report)
    with (output/'history.jsonl').open('w',buffering=1) as history:
        for step in range(rt.lock['updates']):
            net.train();opt.zero_grad(set_to_none=True)
            site,choices=multiref_update(run,b.sites,step)
            components=[]
            for aa in choices:
                item,c=rt.conditioning(net,site,aa)
                x=b.decode(item,c,0)
                loss,values=coordinate_objective(x,item['teacher'][0],item['ca'],item['labels'])
                assert torch.isfinite(loss)
                (loss/2).backward();components.append(values)
                exposure[site['site_key']][aa]+=1
                del x,c,loss
            norm=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True)
            opt.step();b.counts['updates']+=1
            history.write(json.dumps(dict(step=step+1,site=site['site_key'],aa=choices,components=components,
                               gradient_norm=float(norm),clipped=bool(norm>1)),allow_nan=False)+'\n')
            if (step+1)%128==0:
                report['seconds']=time.monotonic()-begin;write_json(output/'report.json',report)
                print('TRAIN',seed,step+1,report['seconds'],flush=True)
            if step+1 in rt.lock['checkpoints']:
                report['evaluations'].append(evaluate_compensation(rt,net,opt,output,step+1,seed))
                write_json(output/f'exposure_{step+1}.json',exposure);write_json(output/'report.json',report)
    assert all(v==32 for row in exposure.values() for v in row.values())
    assert prefix_hash=={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    rt.finish()
    report.update(complete=True,seconds=time.monotonic()-begin,exposure=exposure,
                  history_sha256=sha256(output/'history.jsonl'),peak_allocated_bytes=torch.cuda.max_memory_allocated())
    write_json(output/'report.json',report)
    print('TRAIN_COMPLETE',seed,report['seconds'],b.counts,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['preflight','train'],required=True);p.add_argument('--seed',type=int)
    a=p.parse_args();t=time.monotonic()
    status=a.root/('prepare_execution.json' if a.mode=='preflight' else f'execution_{a.seed}.json')
    try:
        (native_preflight(a.root) if a.mode=='preflight' else train_compensation(a.root,a.seed))
        write_json(status,dict(complete=True,seconds=time.monotonic()-t))
    except BaseException as e:
        write_json(status,dict(complete=False,error=repr(e),seconds=time.monotonic()-t));raise
