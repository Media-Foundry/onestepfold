#!/usr/bin/env python3
"""Bounded fixed-pose sidechain fits of saved C4 predictions, with frozen inputs."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback

import numpy as np
import torch

from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.sidechain_projection_fit import fit_sidechain_projection
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.geometry_repair import preservation
from fastglycan.connection_audit import measure_connections,TOLERANCES
from fastglycan.scaling_metrics import lddt_observed
from fastglycan.paired_teacher_protocol import sha256,write_json


def prepare_sidechain_trial(root,baseline):
    assert not (root/'lock.json').exists()
    prior=json.loads((baseline/'lock.json').read_text());audit=json.loads((baseline/'audit.json').read_text())
    assert prior['reference_contract']=='calibrated_c4_ideal_reference_v1'
    assert audit['verified']==28 and audit['paired']==14 and audit['report_sha256']==sha256(baseline/'report.json')
    assert json.loads((baseline/'pipeline_exit.json').read_text())['returncode']==0
    hashes=dict(prior['hashes'])
    for p,h in hashes.items():assert sha256(Path(p))==h
    for folder in [baseline/'cases',root/'code']:
        for p in folder.rglob('*'):
            if p.is_file() and p.suffix in ['.py','.md','.json','.npz','.pt']:hashes[str(p)]=sha256(p)
    for name in ['lock.json','report.json','audit.json','pipeline_exit.json']:
        p=baseline/name;hashes[str(p)]=sha256(p)
    for name in ['anchored_geometry.py','articulated_output.py','articulated_reference.py']:
        assert {h for p,h in prior['hashes'].items() if Path(p).name==name}=={sha256(root/'code/src/fastglycan'/name)}
    write_json(root/'lock.json',dict(baseline=str(baseline),source=prior['source'],hashes=hashes,
        contract='fixed_backbone_sidechain_fit_v1',planned=16,supported=14,seeds=[12345,54321],workers=2,
        max_iter=60,max_eval=90,timeout_seconds=900,device='cpu',dtype='float64',screen=dict(
            severe_total_max=37,zero_severe_min=7,penetration_max=2.8412365888979707+1e-6)))


def run_sidechain_case(root,index):
    torch.set_num_threads(1);lock=json.loads((root/'lock.json').read_text());source=Path(lock['source'])
    coupled=lock['contract']=='fixed_backbone_sidechain_repulsion_v1'
    assert coupled or lock['contract']=='fixed_backbone_sidechain_fit_v1'
    selection=json.loads((source/'selection.json').read_text());item=selection[index//2];seed=lock['seeds'][index%2]
    folder=root/'cases'/f'{index:02d}';folder.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    row=dict(index=index,pdb_id=item['pdb_id'],group_id=item['group_id'],seed=seed,success=False,lock_sha256=sha256(root/'lock.json'))
    try:
        for p,h in lock['hashes'].items():assert sha256(Path(p))==h
        packet=source/'chemistry'/item['group_id'];chem=json.loads((packet/'report.json').read_text())
        if not chem['passed']:row.update(not_run=True,source_failure=chem['error']);return
        prior=Path(lock['baseline'])/'cases'/f'{2*index+1:02d}'
        old=json.loads((prior/'report.json').read_text());assert old['success'] and old['arm']=='ideal_ref'
        assert sha256(prior/'coordinates.npz')==old['coordinates_sha256']
        data=dict(np.load(prior/'coordinates.npz'));m=dict(np.load(packet/'mapping.npz'));assert m['mask'].all()
        names=data['atom_names'];res=data['residue_ids'];seq=item['sequence']
        assert np.array_equal(data['target'],m['coordinates']) and np.array_equal(names,m['atom_names']) and np.array_equal(res,m['residue_ids'])
        adapter=ArticulatedOutput(data['output_reference'],names,res,seq,json.loads((packet/'variants.json').read_text())).double()
        collision_args={}
        if coupled:
            native_atoms=torch.load(packet/'native.pt',weights_only=False,map_location='cpu')['atoms']
            native_top=GeometryTopology(native_atoms,m['reference'])
            collision_args=dict(collision_pairs=native_top.pairs,collision_radii=native_top.radii)
        start=time.monotonic();fit=fit_sidechain_projection(adapter,torch.tensor(data['raw']),names,max_iter=lock['max_iter'],max_eval=lock['max_eval'],**collision_args)
        row['fit_seconds']=time.monotonic()-start
        assert np.max(np.abs(fit['initial'].numpy()-data['local']))<1e-8
        arrays=dict(raw=data['raw'],initial=fit['initial'].numpy(),final=fit['coordinates'].numpy(),target=data['target'],output_reference=data['output_reference'],atom_names=names,residue_ids=res,mobile=fit['mobile'].numpy())
        assert np.array_equal(arrays['initial'][~arrays['mobile']],arrays['final'][~arrays['mobile']])
        if coupled:
            row['collision']=fit['collision'];arrays['collision_pair_mask']=fit['collision_pair_mask']
        row['fit']={k:fit[k] for k in ['initial_mse','final_mse','iterations','closure_calls','final_gradient_norm','eligible_dof','improved','eligible']}
        row['no_mobile_residues']=[int(i) for i in np.unique(res) if not arrays['mobile'][res==i].any()]
        atoms=torch.load(packet/'native.pt',weights_only=False,map_location='cpu')['atoms'];top=GeometryTopology(atoms,m['reference'])
        ca=names=='CA';bone=np.isin(names,['N','CA','C','O','OXT'])
        anchors=np.array([[np.flatnonzero((res==j)&(names==n))[0] for n in ['N','CA','C','O']] for j in range(1,len(seq)+1)])
        branch=measure_connections(data['raw'],anchors,seq)['nearest_omega_sign']
        side=np.array([[np.flatnonzero((res==j)&(names==n))[0] for n in ['CB','CA','CG1' if aa=='I' else 'OG1','CG2']] for j,aa in enumerate(seq,1) if aa in 'IT'],int).reshape(-1,4)
        def signed(x):
            a,b,c,d=side.T;return np.sum(np.cross(x[b]-x[a],x[c]-x[a])*(x[d]-x[a]),axis=1)
        sign=signed(m['reference']);row['metrics']={}
        for label in ['initial','final']:
            x=arrays[label];_,geometry=top.terms(torch.tensor(x));connections=measure_connections(x,anchors,seq,branch)
            row['metrics'][label]=dict(all_atom_lddt=lddt_observed(x,arrays['target'],res)['score'],
                ca_lddt=lddt_observed(x[ca],arrays['target'][ca],res[ca])['score'],geometry=geometry,
                checked_chirality=geometry['chirality_fraction']==1 and bool((signed(x)*sign>0).all()),
                preservation=preservation(arrays['raw'],x,np.flatnonzero(ca)),
                connection_max={k:float(np.abs(v).max()) for k,v in connections['residuals'].items()},
                connection_pass=all(np.abs(v).max()<=TOLERANCES[k]+1e-6 for k,v in connections['residuals'].items()))
        for k in ['all_atom_lddt','ca_lddt']:
            assert abs(row['metrics']['initial'][k]-old['metrics']['local'][k])<1e-12
        row['backbone_max_abs']=float(np.max(np.abs(arrays['final'][bone]-arrays['initial'][bone])))
        assert row['backbone_max_abs']==0 and row['metrics']['final']['ca_lddt']==row['metrics']['initial']['ca_lddt']
        np.savez_compressed(folder/'coordinates.npz',**arrays);torch.save(dict(values=fit['values'],masks=fit['masks']),folder/'values.pt')
        row.update(success=True,coordinates_sha256=sha256(folder/'coordinates.npz'),values_sha256=sha256(folder/'values.pt'),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception:row['error']=traceback.format_exc()
    finally:row['seconds']=time.monotonic()-started;write_json(folder/'report.json',row)
    if not row['success']:raise RuntimeError(row.get('error','failed case'))


def batch_sidechain_trial(root):
    assert not (root/'controller.json').exists();lock=json.loads((root/'lock.json').read_text())
    write_json(root/'controller.json',dict(pid=os.getpid(),planned=16,phase='running'))
    def worker(index):
        with (root/f'case_{index:02d}.log').open('x') as out:
            try:
                p=subprocess.run([sys.executable,__file__,'--root',str(root),'--mode','case','--index',str(index)],stdout=out,stderr=subprocess.STDOUT,timeout=lock['timeout_seconds'])
                return dict(index=index,returncode=p.returncode)
            except subprocess.TimeoutExpired:return dict(index=index,returncode=124)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:execution=list(pool.map(worker,range(16)))
    rows=[]
    for item in execution:
        p=root/'cases'/f'{item["index"]:02d}'/'report.json'
        rows.append(json.loads(p.read_text()) if p.exists() else dict(index=item['index'],success=False,error='missing terminal report'))
    write_json(root/'report.json',dict(complete=True,rows=rows,execution=execution,lock_sha256=sha256(root/'lock.json')))
    write_json(root/'exit.json',dict(process_failures=sum(x['returncode']!=0 for x in execution),successful=sum(x['success'] for x in rows),skipped=sum(x.get('not_run',False) for x in rows)))
    if any(x['returncode'] for x in execution):raise RuntimeError('batch case failure')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--baseline',type=Path);p.add_argument('--mode',choices=['prepare','case','batch'],required=True);p.add_argument('--index',type=int)
    a=p.parse_args()
    if a.mode=='prepare':prepare_sidechain_trial(a.root,a.baseline)
    elif a.mode=='case':run_sidechain_case(a.root,a.index)
    else:batch_sidechain_trial(a.root)
