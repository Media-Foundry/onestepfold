#!/usr/bin/env python3
"""Complete paired TRAIN/VALIDATION scores with an independent dense GT check."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import time
import traceback

import numpy as np
import torch
from scipy.spatial.distance import cdist
from fastglycan.diffusion_pilot_metrics import prepare_pilot_scoring, score_diffusion_pilot
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.evaluation_reuse import expected_evaluation_calls
from onestepfold.data.gt_materializer import ATOM37_INDEX


def score_diffusion_case(arguments):
    root,row=arguments;root=Path(root);torch.set_num_threads(1);begin=time.monotonic()
    result=dict(group_id=row['group_id'],role=row['role'],complete=False,records=[])
    try:
        lock=json.loads((root/'lock.json').read_text());source=Path(lock['source']);g=row['group_id']
        packet=source/'chemistry'/g;folder=root/'examples'/g
        for path in [packet/'mapping.npz',packet/'native.pt',source/'data/examples'/g/'gt.npz']:
            if str(path) in lock['input_hashes']:assert sha256(path)==lock['input_hashes'][str(path)]
        mapping=dict(np.load(packet/'mapping.npz'));native=torch.load(packet/'native.pt',map_location='cpu',weights_only=False)
        atoms=native['atoms'];names=mapping['atom_names'];ri=mapping['residue_ids']-1
        for key,array in [('atom_names',atoms.atom_name),('residue_ids',atoms.res_id),('chain_ids',atoms.chain_id)]:
            assert np.array_equal(mapping[key],array)
        original=dict(np.load(source/'data/examples'/g/'gt.npz'));ai=np.array([ATOM37_INDEX[n] for n in names])
        observed=original['atom37_mask'][ri,ai]&original['residue_mask'][ri]
        assert np.array_equal(observed,mapping['mask'])
        assert np.array_equal(original['atom37_positions'][ri[observed],ai[observed]],mapping['coordinates'][observed])
        context=prepare_pilot_scoring(mapping,atoms.bonds.as_array(),row['sequence'])
        calibration=json.loads((root/'code/docs/connection_reference_bands.json').read_text())
        report=json.loads((folder/'report.json').read_text());assert report['lock_sha256']==sha256(root/'lock.json')
        seeds=lock['train_seeds'] if row['role']=='train' else lock['validation_seeds']
        assert {(e['seed'],e['model']) for e in report['entries']}=={(s,m) for s in seeds for m in lock['models']}
        metric_error=0.;labels=mapping['residue_ids'];ca=(names=='CA')&observed
        for entry in report['entries']:
            path=folder/entry['name'];assert sha256(path)==entry['sha256']
            x=np.load(path);assert x.dtype==np.float32
            scores=score_diffusion_pilot(x,context,calibration)
            # Dense distances in bounded row blocks: no production spatial index.
            for mask,key in [(observed,'all_atom_lddt'),(ca,'ca_lddt')]:
                y=np.asarray(mapping['coordinates'][mask],dtype=float);prediction=np.asarray(x[mask],dtype=float);res=labels[mask]
                total=0.;valid_count=0
                for first in range(0,len(y),256):
                    reference=cdist(y[first:first+256],y);measured=cdist(prediction[first:first+256],prediction)
                    keep=(reference<15)&(res[first:first+256,None]!=res[None,:]);counts=keep.sum(1);valid=counts>0
                    agreement=np.zeros_like(reference)
                    for threshold in (.5,1.,2.,4.):agreement+=((np.abs(measured-reference)<threshold)&keep)/4
                    total+=float((agreement.sum(1)[valid]/counts[valid]).sum());valid_count+=int(valid.sum())
                metric_error=max(metric_error,abs(total/valid_count-scores[key]))
            result['records'].append(dict(group_id=g,pdb_id=row['pdb_id'],role=row['role'],length=len(row['sequence']),
                model=entry['model'],seed=entry['seed'],seconds=entry['seconds'],**scores))
        assert metric_error<1e-10
        result.update(complete=True,metric_max_abs=metric_error,report_sha256=sha256(folder/'report.json'))
    except Exception:result['error']=traceback.format_exc()
    result['seconds']=time.monotonic()-begin;write_json(root/'scores'/f'{row["group_id"]}.json',result)
    return result


def summarize_diffusion_evaluation(root,workers):
    begin=time.monotonic();lock=json.loads((root/'lock.json').read_text());execution=json.loads((root/'execution.json').read_text())
    assert execution['complete'] and all(w['exit_code']==0 for w in execution['workers'])
    for path,digest in lock['hashes'].items():assert sha256(Path(path))==digest
    for checkpoint in lock['checkpoints'].values():assert sha256(Path(checkpoint['path']))==checkpoint['sha256']
    totals=dict(native=0,**{arm:0 for arm in lock['checkpoints']});seen=[]
    planned=len(lock['rows']);probe_nfe=1+3*len(lock['checkpoints'])
    for i,assigned in enumerate(lock['assignments']):
        report=json.loads((root/f'worker_{i}/report.json').read_text());assert report['complete']
        assert report['lock_sha256']==sha256(root/'lock.json') and report['probe_nfe']==probe_nfe
        assert all(all(p.values()) for p in report['probe'].values())
        assert [r['group_id'] for r in report['rows']]==[r['group_id'] for r in assigned]
        for name in totals:totals[name]+=report['calls'][name]
        seen.extend(r['group_id'] for r in report['rows'])
    assert len(seen)==len(set(seen))==planned
    assert totals==expected_evaluation_calls(lock,lock['rows'])
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results=list(pool.map(score_diffusion_case,[(str(root),r) for r in lock['rows']]))
    failures=[dict(group_id=r['group_id'],role=r['role'],error=r['error']) for r in results if not r['complete']]
    records=[v for r in results if r['complete'] for v in r['records']]
    if failures:
        write_json(root/'evaluation.json',dict(complete=False,planned_proteins=planned,failures=failures,
            completed_proteins=sum(r['complete'] for r in results),records=records))
        raise RuntimeError('incomplete evaluation; failures retained, no reduced-denominator summary')
    expected_outputs=2*planned*len(lock['models']);assert len(records)==expected_outputs
    summary={};paired=[]
    for role in sorted({r['role'] for r in lock['rows']}):
        part=[r for r in records if r['role']==role];groups=sorted({r['group_id'] for r in part});n=len(groups)
        lookup={(r['group_id'],r['seed'],r['model']):r for r in part}
        seeds=lock['train_seeds'] if role=='train' else lock['validation_seeds']
        bootstrap=np.random.default_rng(lock['bootstrap']['seed']).integers(0,n,size=(10000,n))
        by_model={};arrays={}
        for model in lock['models']:
            rows=[r for r in part if r['model']==model]
            arrays[model]={metric:np.array([np.mean([lookup[g,s,model][metric] for s in seeds]) for g in groups])
                for metric in ['all_atom_lddt','ca_lddt','ca_aligned_rmsd']}
            quality={}
            for metric,a in arrays[model].items():
                quality[metric]=dict(mean=float(a.mean()),median=float(np.median(a)),p01=float(np.quantile(a,.01)),
                    p05=float(np.quantile(a,.05)),worst5_mean=float((np.sort(a)[-max(1,int(np.ceil(.05*n))):]
                        if metric=='ca_aligned_rmsd' else np.sort(a)[:max(1,int(np.ceil(.05*n)))]).mean()))
            zero=[r['geometry']['severe_pairs']==0 for r in rows];stereo=[r['geometry']['strict_checked_chirality'] for r in rows]
            by_model[model]=dict(quality_protein_means=quality,instances=len(rows),zero_severe_instances=sum(zero),
                strict_chirality_instances=sum(stereo),zero_and_strict_instances=sum(a and b for a,b in zip(zero,stereo)),
                zero_and_strict_both_noises=sum(all(lookup[g,s,model]['geometry']['severe_pairs']==0 and lookup[g,s,model]['geometry']['strict_checked_chirality'] for s in seeds) for g in groups),
                severe_pairs_total=sum(r['geometry']['severe_pairs'] for r in rows),
                ca_wrong_total=sum(r['geometry']['ca_chirality_wrong'] for r in rows),
                side_wrong_total=sum(r['geometry']['sidechain_checked_wrong'] for r in rows),
                max_penetration_max=max(r['geometry']['max_penetration'] for r in rows),
                diffusion_seconds_mean=float(np.mean([r['seconds'] for r in rows])) if all(r['seconds'] is not None for r in rows) else None)
        contrasts=[]
        for candidate,reference in lock.get('contrasts', [('native_s2','native_s1'),('gt','native_s1'),('gt_s2','native_s1'),('gt_s2','gt')]):
            difference={}
            for metric in ['all_atom_lddt','ca_lddt']:
                delta=arrays[candidate][metric]-arrays[reference][metric]
                difference[metric]=dict(mean=float(delta.mean()),median=float(np.median(delta)),
                    ci95=np.quantile(delta[bootstrap].mean(1),[.025,.975]).tolist(),p01=float(np.quantile(delta,.01)),
                    p05=float(np.quantile(delta,.05)),worst5_mean=float(np.sort(delta)[:max(1,int(np.ceil(.05*n)))].mean()),
                    below_minus_005=int((delta<-.05).sum()),positive_proteins=int((delta>0).sum()))
            worse=sum(lookup[g,s,candidate]['geometry']['severe_pairs']>0 and lookup[g,s,reference]['geometry']['severe_pairs']==0 for g in groups for s in seeds)
            lost_stereo=sum(not lookup[g,s,candidate]['geometry']['strict_checked_chirality'] and lookup[g,s,reference]['geometry']['strict_checked_chirality'] for g in groups for s in seeds)
            contrasts.append(dict(candidate=candidate,reference=reference,quality=difference,
                introduced_severe_on_zero_instances=worse,lost_strict_chirality_instances=lost_stereo))
            for g in groups:
                paired.append(dict(role=role,group_id=g,candidate=candidate,reference=reference,
                    per_noise=[dict(seed=s,delta_aa=lookup[g,s,candidate]['all_atom_lddt']-lookup[g,s,reference]['all_atom_lddt'],
                        delta_ca=lookup[g,s,candidate]['ca_lddt']-lookup[g,s,reference]['ca_lddt']) for s in seeds]))
        summary[role]=dict(proteins=n,seeds=seeds,models=by_model,contrasts=contrasts)
    write_json(root/'evaluation.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),
        outputs=expected_outputs,proteins=planned,counts=totals,probe_nfe=probe_nfe*len(lock['assignments']),metric_max_abs=max(r['metric_max_abs'] for r in results),
        summary=summary,paired=paired,records=records,seconds=time.monotonic()-begin,
        scope=lock.get('primary','terminal paired learning pilot; TRAIN and held-out VALIDATION kept separate; no deployment pass')))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--workers',type=int,default=16);a=p.parse_args()
    torch.set_num_threads(1);summarize_diffusion_evaluation(a.root,a.workers)
