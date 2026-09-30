#!/usr/bin/env python3
"""Matched ESMC/ESM2 interface check: retained folding weights and fixed C4/S1."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import traceback

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_folding_esmc_comparison(root):
    assert not (root/'lock.json').exists()
    base=root.parent;fit=base/'folding_esmc_bridge_v1_20260930';train=base/'folding_scale_training_v1_20260930'
    old=base/'folding_coordinate_evaluation_v1_20260930'
    assert sha256(fit/'lock.json')=='cec494be3aa3f76760cebb78c0264ab12174bef961ec65a41708be56e4481035'
    f=json.loads((fit/'report.json').read_text());assert f['complete'] and f['train_proteins']==423 and f['validation_feature_reads']==0
    assert sha256(fit/'bridge.pt')==f['bridge_sha256']=='bf06a64050ffc74e4d0aeb68025c42493e7fcfa8a2e6bdae39d3ad282fbf949e'
    assert sha256(old/'lock.json')=='65a1849e3fe9baab572d685a0cb782d7956e6c8d659d92619175ce3bc7f6255b'
    prior=json.loads((old/'lock.json').read_text());t=json.loads((train/'lock.json').read_text());allrows={r['group_id']:r for r in t['rows']}
    assert sha256(train/'lock.json')=='1ec3f1c13fec5ea12981f9efef37957fec264c1bc0e659c9fc4a98519384c357'
    groups=sorted(t['probe_groups']);dev=sorted(g for g,r in allrows.items() if r['role']=='validation')
    assert len(groups)==len(dev)==32 and not set(groups)&set(dev)
    assert all(allrows[g]['role']=='train' for g in groups)
    rows=[allrows[g] for g in groups+dev]
    engineering=[min((r for r in t['rows'] if r['role']=='train'),key=lambda r:(len(r['sequence']),r['group_id'])),
                 max((r for r in t['rows'] if r['role']=='train'),key=lambda r:(len(r['sequence']),r['group_id']))]
    audit=base/'folding_esm_pair_audit_v1_20260930/report.json'
    assert sha256(audit)=='47e08e63e6689a61e49eb80294092c4d77226e65005dc50b0b0cc8c2512ef092'
    pairs={p['group_id']:p for p in json.loads(audit.read_text())['pairs']};cache=Path(t['cache'])
    checkpoint=Path(t['initial_checkpoint']);assert sha256(checkpoint)==t['initial_checkpoint_sha256']
    trusted={};execution=json.loads((old/'execution.json').read_text());assert execution['complete']
    for w in execution['workers']:
        p=old/f'worker_{w["index"]}/report.json';assert sha256(p)==w['report_sha256']
        trusted.update({r['group_id']:r for r in json.loads(p.read_text())['rows']})
    inputs={str(p):sha256(p) for p in [fit/'lock.json',fit/'report.json',fit/'bridge.pt',train/'lock.json',old/'lock.json',old/'execution.json',audit,checkpoint]}
    references={};needed={r['group_id']:r for r in rows+engineering}
    for g,row in needed.items():
        path=cache/'examples'/g/'conditioning.pt';assert sha256(path)==t['cache_files'][str(path)];inputs[str(path)]=t['cache_files'][str(path)]
        packet=Path(t['source'])/'chemistry'/g
        for p in [packet/'native.pt',packet/'mapping.npz',Path(t['source'])/'data/examples'/g/'gt.npz']:
            assert sha256(p)==prior['input_hashes'][str(p)];inputs[str(p)]=prior['input_hashes'][str(p)]
        p=old/'examples'/g/'report.json';r=json.loads(p.read_text());assert r==trusted[g];inputs[str(p)]=sha256(p)
        references[g]={}
        for e in r['entries']:
            if e['model']=='retained':
                file=p.parent/e['name'];assert sha256(file)==e['sha256'];inputs[str(file)]=e['sha256'];references[g][str(e['seed'])]=str(file)
        assert len(references[g])==2 and pairs[g]['role']==row['role']
    for p,h in json.loads(audit.read_text())['shard_hashes'].items():assert sha256(Path(p))==h;inputs[p]=h
    assignments=[[] for _ in range(4)];loads=[0]*4
    for r in sorted(rows,key=lambda r:(-len(r['sequence']),r['group_id'])):
        i=min(range(4),key=lambda j:(loads[j],j));assignments[i].append(r);loads[i]+=len(r['sequence'])**2
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']}
    for relative in ['src/fastglycan/models/differentiable_mini.py','scripts/score_diffusion_learning.py','src/fastglycan/diffusion_pilot_metrics.py']:
        assert sha256(root/'code'/relative)==sha256(old/'code'/relative)
    write_json(root/'lock.json',dict(schema='folding_esmc_c4_comparison_v1',source=t['source'],cache=t['cache'],rows=rows,engineering=engineering,
        models=['retained','esmc'],contrasts=[['esmc','retained']],cohorts={'train_probe32':groups,'observed_dev32':dev},cohort_order=['observed_dev32','train_probe32'],
        assignments=assignments,bridge=str(fit/'bridge.pt'),checkpoint=str(checkpoint),selected_names=t['selected_names'],
        reference_coordinates=references,pairs={g:pairs[g] for g in needed},feature_root=str(base/'folding_esmc_features_v1_20260930/features'),
        hashes=hashes,input_hashes=inputs,weight_stats=t['weight_stats'],train_seeds=t['training_seeds'],validation_seeds=t['validation_seeds'],
        bootstrap=dict(seed=20260930,replicates=10000),planned_outputs=256,new_predictions=128,engineering_predictions=8,
        planned_pairformer_calls=544,steps=1,cycles=4,dtype='fp32',checkpoint_selection='fixed retained512, independent of global-distance candidate',
        scope='TRAIN32 and observed DEV32; one fixed affine ESMC bridge, not new independent confirmation or encoder-only superiority'))


def run_folding_esmc_comparison(root,index=None):
    from safetensors import safe_open
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import full_recycle_pairformer, diffusion_from_conditioning
    from fastglycan.models.diffusion_scope import load_dense_diffusion_checkpoint
    from fastglycan.folding_esmc_projection import temporary_folding_esmc_projection
    from fastglycan.hybrid_proposals import identity_noise
    lock=json.loads((root/'lock.json').read_text());preflight=index is None
    folder=root/('preflight' if preflight else f'worker_{index}');folder.mkdir(exist_ok=False)
    report=dict(complete=False,rows=[],lock_sha256=sha256(root/'lock.json'));start=time.monotonic()
    try:
        for p,h in lock['hashes'].items():assert sha256(Path(p))==h,p
        for p,s in lock['weight_stats'].items():assert [Path(p).stat().st_size,Path(p).stat().st_mtime_ns]==s
        for p in [lock['bridge'],lock['checkpoint']]:assert sha256(Path(p))==lock['input_hashes'][p]
        if not preflight:
            release=json.loads((root/'preflight/report.json').read_text());assert release['complete'] and release['lock_sha256']==sha256(root/'lock.json')
            report['preflight_sha256']=sha256(root/'preflight/report.json')
        torch.set_num_threads(1);runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32'
        model=runner.model.eval().requires_grad_(False);state=torch.load(lock['checkpoint'],map_location='cpu',weights_only=False)
        load_dense_diffusion_checkpoint(model,state,arm='diffusion_dense',expected_names=lock['selected_names']);del state
        before={n:v.detach().cpu().clone() for n,v in model.state_dict().items()}
        bridge=torch.load(lock['bridge'],map_location='cpu',weights_only=True)
        counts=dict(pairformer=0,diffusion=0)
        ph=model.pairformer_stack.register_forward_hook(lambda *a:counts.__setitem__('pairformer',counts['pairformer']+1))
        dh=model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('diffusion',counts['diffusion']+1))
        rows=lock['engineering'] if preflight else lock['assignments'][index]
        with torch.no_grad():
            for row in rows:
                g=row['group_id'];pair=lock['pairs'][g];path=Path(lock['cache'])/'examples'/g/'conditioning.pt'
                assert sha256(path)==lock['input_hashes'][str(path)]
                saved=torch.load(path,map_location='cpu',weights_only=False);assert saved['group_id']==g and saved['role']==row['role']
                e=saved['features']['esm_token_embedding'];assert hashlib.sha256(e.contiguous().numpy().tobytes()).hexdigest()==pair['esm2_feature_sha256']
                ent=pair['esmc_entry'];shard=Path(lock['feature_root'])/ent['shard'];assert sha256(shard)==lock['input_hashes'][str(shard)]
                with safe_open(str(shard),framework='pt',device='cpu') as f:x=f.get_slice('final')[ent['offset_start']:ent['offset_end']]
                assert x.shape==(len(row['sequence']),1152) and x.dtype==torch.bfloat16 and torch.isfinite(x).all()
                assert hashlib.sha256(x.contiguous().view(torch.uint16).numpy().tobytes()).hexdigest()==pair['esmc_feature_sha256']
                features=device_tree(saved['features'],'cuda');esmc_features=dict(features);esmc_features['esm_token_embedding']=x.cuda().float()
                assert all(esmc_features[k] is v for k,v in features.items() if k!='esm_token_embedding')
                packet=Path(lock['source'])/'chemistry'/g/'native.pt';assert sha256(packet)==lock['input_hashes'][str(packet)]
                atoms=torch.load(packet,map_location='cpu',weights_only=False)['atoms']
                seeds=lock['train_seeds'] if row['role']=='train' else lock['validation_seeds']
                target=folder/g if preflight else root/'examples'/g;target.mkdir(parents=True,exist_ok=False)
                entries=[];max_native=0.;first_esmc=None;timings=[]
                # Preflight repeats each route after projection restoration; workers use one pair.
                for repeat in range(2 if preflight else 1):
                    point=full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False)
                    flat=torch.cat([v.flatten() for v in point]);assert torch.equal(flat.cpu(),saved['conditioning_flat'])
                    # The archived diffusion reference consumes packed contiguous views.
                    point=tuple(v.reshape(s) for v,s in zip(flat.split(saved['sizes']),saved['shapes']))
                    if preflight:
                        native=diffusion_from_conditioning(model,features,identity_noise(atoms,seeds[0],device='cuda'),point,steps=1).reshape(-1,3)
                        ref=Path(lock['reference_coordinates'][g][str(seeds[0])]);assert sha256(ref)==lock['input_hashes'][str(ref)]
                        assert np.array_equal(native.cpu().numpy(),np.load(ref));del native
                    del point,flat
                    with temporary_folding_esmc_projection(model,bridge):
                        torch.cuda.synchronize();begin=time.monotonic()
                        point=full_recycle_pairformer(model,esmc_features,N_cycle=4,inplace_safe=False,mc_dropout=False)
                        flat=torch.cat([v.flatten() for v in point]);shapes=[v.shape for v in point];sizes=[v.numel() for v in point]
                        point=tuple(v.reshape(s) for v,s in zip(flat.split(sizes),shapes))
                        torch.cuda.synchronize();conditioning_seconds=time.monotonic()-begin
                        for seed in (seeds[:1] if preflight else seeds):
                            noise=identity_noise(atoms,seed,device='cuda');cpu_rng=torch.get_rng_state().clone();gpu_rng=torch.cuda.get_rng_state().clone()
                            torch.cuda.synchronize();begin=time.monotonic()
                            coordinates=diffusion_from_conditioning(model,esmc_features,noise,point,steps=1).reshape(-1,3)
                            torch.cuda.synchronize();seconds=time.monotonic()-begin
                            assert torch.isfinite(coordinates).all() and coordinates.dtype==torch.float32
                            assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(gpu_rng,torch.cuda.get_rng_state())
                            value=coordinates.cpu().numpy()
                            if preflight:
                                if repeat==0:first_esmc=value.copy()
                                else:assert np.array_equal(first_esmc,value)
                            else:
                                file=target/f'esmc_seed{seed}.npy';np.save(file,value)
                                entries.append(dict(model='esmc',seed=seed,name=file.name,sha256=sha256(file),seconds=seconds,nfe=1))
                            del coordinates,noise
                        timings.append(conditioning_seconds);del point,flat
                if not preflight:
                    for seed in seeds:
                        ref=Path(lock['reference_coordinates'][g][str(seed)]);assert sha256(ref)==lock['input_hashes'][str(ref)]
                        file=target/f'retained_seed{seed}.npy';shutil.copyfile(ref,file)
                        entries.append(dict(model='retained',seed=seed,name=file.name,sha256=sha256(file),seconds=None,nfe=0))
                result=dict(group_id=g,role=row['role'],entries=entries,lock_sha256=sha256(root/'lock.json'),native_conditioning_exact=True,
                    native_coordinate_replay=preflight,esmc_repeat_exact=preflight,esmc_conditioning_seconds=timings)
                write_json(target/'report.json',result);report['rows'].append(result);write_json(folder/'report.json',report)
                del saved,features,esmc_features,atoms,x,e;torch.cuda.empty_cache()
        expected=dict(pairformer=(16 if preflight else 8)*len(rows),diffusion=(4 if preflight else 2)*len(rows))
        assert counts==expected
        assert set(before)==set(model.state_dict()) and all(torch.equal(v.cpu(),before[n]) for n,v in model.state_dict().items())
        ph.remove();dh.remove()
        report.update(complete=True,counts=counts,model_restored_exact=True,peak_gpu_bytes=torch.cuda.max_memory_allocated(),
            device=torch.cuda.get_device_name(0),timing_scope='cached sequence features; C4 recomputed, ESM encoder time excluded')
    except Exception:report['error']=traceback.format_exc()
    finally:report['seconds']=time.monotonic()-start;write_json(folder/'report.json',report)
    if not report['complete']:raise RuntimeError(report.get('error','incomplete'))


def score_folding_esmc_comparison(root):
    from score_diffusion_learning import score_diffusion_case
    from fastglycan.folding_evaluation import summarize_folding_cohorts
    from fastglycan.folding_global_metrics import summarize_global_structure
    lock=json.loads((root/'lock.json').read_text());submission=json.loads((root/'submission.json').read_text())
    jobs=[submission['preflight_job']]+submission['worker_jobs'];scheduler=subprocess.check_output(['sacct','-j',','.join(jobs),'-n','-X','-P','--format=JobIDRaw,State,ExitCode'],text=True)
    assert all(f'{j}|COMPLETED|0:0' in scheduler for j in jobs)
    hashes={};seen=[];counts=dict(pairformer=0,diffusion=0)
    for folder in ['preflight']+[f'worker_{i}' for i in range(4)]:
        p=root/folder/'report.json';r=json.loads(p.read_text());assert r['complete'] and r['lock_sha256']==sha256(root/'lock.json') and r['model_restored_exact']
        hashes[str(p)]=sha256(p)
        for k in counts:counts[k]+=r['counts'][k]
        if folder!='preflight':
            i=int(folder.split('_')[1]);assert [x['group_id'] for x in r['rows']]==[x['group_id'] for x in lock['assignments'][i]]
            for row in r['rows']:
                g=row['group_id'];assert json.loads((root/'examples'/g/'report.json').read_text())==row;seen.append(g)
    assert set(seen)=={r['group_id'] for r in lock['rows']} and len(seen)==64
    assert counts==dict(pairformer=544,diffusion=136)
    for p,h in lock['hashes'].items():assert sha256(Path(p))==h
    with ProcessPoolExecutor(max_workers=8) as pool:results=list(pool.map(score_diffusion_case,[(str(root),r) for r in lock['rows']]))
    failures=[r for r in results if not r['complete']]
    if failures:
        write_json(root/'evaluation.json',dict(complete=False,planned_proteins=64,failures=failures));raise RuntimeError('Failed scores retain denominator')
    records=[v for r in results for v in r['records']];assert len(records)==256
    cohorts=summarize_folding_cohorts(records,lock);global_report=summarize_global_structure(records,lock)
    lines=['# Matched ESMC/ESM2 C4/S1 interface comparison','',
        'Same retained512 diffusion checkpoint and chemistry. One TRAIN423-fitted affine bridge; frozen folding core. '
        'TRAIN32 and observed DEV32 remain separate, two fixed K1 noises averaged per protein. Not new independent confirmation.','']
    for name,c in cohorts['summary'].items():
        lines += [f'## {name}','', '|Model|AA-lDDT|CA-lDDT|Zero severe + strict /64|Both noises /32|Severe pairs|','|---|---:|---:|---:|---:|---:|']
        for m,v in c['models'].items():lines.append(f"|{m}|{v['mean_aa']:.6f}|{v['mean_ca']:.6f}|{v['zero_and_strict_instances']}|{v['zero_and_strict_both_noises']}|{v['severe_pairs']}|")
        p=c['contrasts'][0];lines+=['','|Metric esmc-retained|Mean|95% CI|P01|P05|Worst5%|Below -0.05|','|---|---:|---|---:|---:|---:|---:|']
        for m,q in p['quality'].items():lines.append(f"|{m}|{q['mean']:+.6f}|{q['ci95']}|{q['p01']:+.6f}|{q['p05']:+.6f}|{q['worst5_mean']:+.6f}|{q['below_minus_005']}|")
        lines += ['',f"New severe collision instances: {p['introduced_severe_on_zero_instances']}; lost strict stereo: {p['lost_strict_chirality_instances']}.",'']
    lines += [global_report.pop('markdown'),'','Geometry checks are operational, not comprehensive chemistry certification. Timing excludes sequence encoders. No automatic model promotion.']
    (root/'report.md').write_text('\n'.join(lines)+'\n')
    write_json(root/'evaluation.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),records=records,cohorts=cohorts,global_structure=global_report,
        proteins=64,outputs=256,counts=counts,metric_max_abs=max(r['metric_max_abs'] for r in results),scheduler=scheduler,
        worker_hashes=hashes,report_sha256=sha256(root/'report.md')))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','preflight','worker','score'],required=True);p.add_argument('--index',type=int);a=p.parse_args();root=a.root.resolve()
    if a.mode=='prepare':prepare_folding_esmc_comparison(root)
    elif a.mode=='score':score_folding_esmc_comparison(root)
    else:run_folding_esmc_comparison(root,None if a.mode=='preflight' else a.index)
