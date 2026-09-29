#!/usr/bin/env python3
"""Paired frozen joint solver from zero or saved fitted pose parameters."""
import argparse
import concurrent.futures
import hashlib
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

from fastglycan.anchored_geometry import solve
from fastglycan.anchored_tail import TailObjective
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.geometry_start import pose_variables_at_start
from fastglycan.geometry_repair import preservation
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.repair_outcomes import absolute_failures
from fastglycan.scaling_metrics import lddt_observed


def buffer_digest(module):
    result = hashlib.sha256()
    for name, value in module.named_buffers():
        value = value.detach().cpu().contiguous()
        result.update(json.dumps([name, str(value.dtype), list(value.shape)]).encode())
        result.update(value.numpy().tobytes())
    return result.hexdigest()


def prepare(root, source):
    assert not (root/'lock.json').exists()
    old = json.loads((source/'report.json').read_text())
    audit = json.loads((source/'audit.json').read_text())
    previous = json.loads((source/'execution_lock.json').read_text())
    assert old['complete'] and old['successful'] == 21 and audit['verified_fits'] == 21
    assert audit['report_sha256'] == sha256(source/'report.json')
    assert old['lock_sha256'] == sha256(source/'execution_lock.json')
    for path, value in previous['hashes'].items():
        assert sha256(Path(path)) == value
    hashes = dict(previous['hashes'])
    for path in source.rglob('*'):
        if path.is_file() and (path.name in ['selection.json','report.json','audit.json','values.pt','coordinates.npz','execution_lock.json']):
            hashes[str(path)] = sha256(path)
    for path in (root/'code').rglob('*'):
        if path.is_file() and path.suffix in ['.py','.md','.json']:
            hashes[str(path)] = sha256(path)
    for name in ['anchored_geometry.py','anchored_tail.py','articulated_output.py']:
        current = root/'code/src/fastglycan'/name
        earlier = [v for p,v in previous['hashes'].items() if Path(p).name == name]
        assert earlier == [sha256(current)]
    write_json(root/'lock.json', dict(source=str(source), hashes=hashes,
        source_selection_sha256=sha256(source/'selection.json'), planned=32, supported=28,
        seeds=[12345,54321], starts=['zero','fitted'], workers=2, timeout_seconds=900,
        device='cpu', dtype='float64', joint_iterations=180, extra_fitted_iterations=60,
        scope='paired initialization only; original raw chart and objective retained; C1/S1 development'))


def case(root, index):
    torch.set_num_threads(1)
    lock=json.loads((root/'lock.json').read_text());source=Path(lock['source'])
    selected=json.loads((source/'selection.json').read_text())
    item=selected[index//4];seed=lock['seeds'][(index//2)%2];arm=lock['starts'][index%2]
    g=item['group_id'];packet=source/'chemistry'/g
    folder=root/'cases'/f'{index:02d}';folder.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    result=dict(index=index,group_id=g,pdb_id=item['pdb_id'],seed=seed,arm=arm,success=False,
                lock_sha256=sha256(root/'lock.json'))
    try:
        for path,value in lock['hashes'].items():assert sha256(Path(path))==value
        chemistry=json.loads((packet/'report.json').read_text())
        if not chemistry['passed']:
            result.update(not_run=True,source_failure=chemistry['error']);return
        previous=source/'fits'/f'{index//4*3+1+(index//2)%2:02d}'
        fitreport=json.loads((previous/'report.json').read_text())
        assert fitreport['success'] and fitreport['arm']==f'native_{seed}'
        assert sha256(previous/'values.pt')==fitreport['values_sha256']
        assert sha256(previous/'coordinates.npz')==fitreport['coordinates_sha256']
        fitted=dict(np.load(previous/'coordinates.npz'))
        raw_array=np.load(source/'data'/g/f'native_{seed}.npy').astype(np.float64)
        assert np.array_equal(raw_array,fitted['raw'])
        mapping=dict(np.load(packet/'mapping.npz'))
        assert mapping['mask'].all()
        names,residues=mapping['atom_names'],mapping['residue_ids']
        inv=dict(np.load(source/'data'/g/'inventory.npz'))
        assert np.array_equal(names,inv['atom_name']) and np.array_equal(residues,inv['residue_id'])
        raw=torch.tensor(raw_array)
        adapter=ArticulatedOutput(mapping['reference'],names,residues,item['sequence'],
                                  json.loads((packet/'variants.json').read_text())).double()
        values=torch.load(previous/'values.pt',map_location='cpu',weights_only=True) if arm=='fitted' else None
        variables=pose_variables_at_start(adapter,raw,values)
        start=variables().detach().clone()
        expected=fitted['final'] if arm=='fitted' else fitted['initial']
        assert np.max(np.abs(start.numpy()-expected))<1e-8
        assert np.max(np.abs(variables.initial.numpy()-fitted['initial']))<1e-8
        atoms=torch.load(packet/'native.pt',map_location='cpu',weights_only=False)['atoms']
        topology=GeometryTopology(atoms,mapping['reference'])
        anchors=np.array([[int(np.flatnonzero((residues==j)&(names==name))[0]) for name in ['N','CA','C','O']]
                          for j in range(1,len(item['sequence'])+1)])
        objective=TailObjective(raw,anchors,item['sequence'],topology.pairs,topology.radii)
        result.update(chart_sha256=buffer_digest(variables),objective_sha256=buffer_digest(objective),
            raw_sha256=sha256(source/'data'/g/f'native_{seed}.npy'),
            recorded_extra_fit_seconds=fitreport['fit_seconds'] if arm=='fitted' else 0.,
            extra_fit_iterations=fitreport['iterations'] if arm=='fitted' else 0,
            extra_fit_closures=fitreport['closure_calls'] if arm=='fitted' else 0,
            start_replay_max_abs=float(np.max(np.abs(start.numpy()-expected))))
        with torch.no_grad():
            loss,terms=objective(start,variables.variables,1.)
        result['start_objective']=dict(loss=float(loss),terms={k:float(v) for k,v in terms.items()})
        initial_values=tuple(p.detach().clone() for p in variables.variables)
        write_json(folder/'progress.json',dict(stage='initialized',**result))
        def callback(state):
            write_json(folder/'progress.json',dict(stage='solving',seconds=time.monotonic()-started,**state))
        t=time.monotonic();final,history=solve(variables,objective,callback)
        result.update(solver_seconds=time.monotonic()-t,history=history)
        assert buffer_digest(variables)==result['chart_sha256']
        assert buffer_digest(objective)==result['objective_sha256']
        arrays=dict(raw=raw_array,local=variables.initial.numpy(),start=start.numpy(),final=final.numpy(),
                    target=mapping['coordinates'].astype(np.float64))
        result['metrics']={};ca=names=='CA';bone=np.isin(names,['N','CA','C','O'])
        side=np.array([[int(np.flatnonzero((residues==j)&(names==n))[0])
                       for n in ['CB','CA','CG1' if aa=='I' else 'OG1','CG2']]
                       for j,aa in enumerate(item['sequence'],1) if aa in 'IT'],dtype=int).reshape(-1,4)
        def volume(x):
            c,a,b,d=side.T;return (np.cross(x[a]-x[c],x[b]-x[c])*(x[d]-x[c])).sum(-1)
        reference_volume=volume(mapping['reference'])
        for label in ['raw','local','start','final']:
            x=arrays[label];tx=torch.tensor(x)
            _,geometry=topology.terms(tx)
            connection={k:float(v.abs().max()) for k,v in objective.residuals(tx).items()}
            connected=all(connection[k]<=tol+1e-6 for k,tol in
                dict(cn=.03,angle_c=.04,angle_n=.04,omega=.1,carbonyl=.1).items())
            chirality=geometry['chirality_fraction']==1 and bool((volume(x)*reference_volume>0).all())
            failures=absolute_failures(geometry);pres=preservation(raw_array,x,np.flatnonzero(ca))
            squared=((x-raw_array)**2).sum(-1)
            result['metrics'][label]=dict(all_atom_lddt=lddt_observed(x,arrays['target'],residues)['score'],
                ca_lddt=lddt_observed(x[ca],arrays['target'][ca],residues[ca])['score'],
                geometry=geometry,connection_max=connection,connection_pass=connected,
                all_checked_chirality_pass=chirality,absolute_failures=failures,preservation=pres,
                joint_pass=not failures and pres['accepted'] and chirality and connected,
                backbone_raw_mse=float(squared[bone].mean()),sidechain_raw_mse=float(squared[~bone].mean()))
        np.savez_compressed(folder/'coordinates.npz',**arrays,atom_names=names,residue_ids=residues)
        torch.save(dict(initial=initial_values,final=tuple(p.detach().clone() for p in variables.variables)),folder/'values.pt')
        result.update(success=True,coordinates_sha256=sha256(folder/'coordinates.npz'),
            values_sha256=sha256(folder/'values.pt'),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception:
        result['error']=traceback.format_exc()
    finally:
        result['seconds']=time.monotonic()-started;write_json(folder/'report.json',result)
    if not result['success']:raise RuntimeError(result.get('error','case failed'))


def batch(root):
    lock=json.loads((root/'lock.json').read_text());assert not (root/'controller.json').exists()
    write_json(root/'controller.json',dict(pid=os.getpid(),phase='running',planned=lock['planned']))
    def worker(i):
        with (root/f'case_{i:02d}.log').open('x') as log:
            try:
                p=subprocess.run([sys.executable,__file__,'--root',str(root),'--mode','case','--index',str(i)],
                    stdout=log,stderr=log,timeout=lock['timeout_seconds'],env=dict(os.environ,
                    OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',ROCR_VISIBLE_DEVICES=''))
                return dict(index=i,returncode=p.returncode)
            except subprocess.TimeoutExpired:return dict(index=i,returncode=124)
    with concurrent.futures.ThreadPoolExecutor(max_workers=lock['workers']) as pool:
        execution=list(pool.map(worker,range(lock['planned'])))
    rows=[]
    for i in range(lock['planned']):
        file=root/'cases'/f'{i:02d}'/'report.json'
        rows.append(json.loads(file.read_text()) if file.exists() else dict(index=i,success=False,error='missing report'))
    write_json(root/'report.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),rows=rows,
        execution=execution,successful=sum(x['success'] for x in rows),expected=lock['planned']))
    write_json(root/'exit.json',dict(process_failures=sum(x['returncode']!=0 for x in execution),
        successful=sum(x['success'] for x in rows),source_skipped=sum(x.get('not_run',False) for x in rows)))
    write_json(root/'controller.json',dict(pid=os.getpid(),phase='finished',planned=lock['planned']))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--source',type=Path)
    p.add_argument('--mode',choices=['prepare','batch','case'],required=True);p.add_argument('--index',type=int)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.root,a.source)
    elif a.mode=='batch':batch(a.root)
    else:case(a.root,a.index)
