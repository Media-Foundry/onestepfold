"""Independent FP64 checkpoint metrics, score recomputation and input-role audit."""
import argparse,gzip,json
from pathlib import Path
import numpy as np
import torch
from scipy.stats import spearmanr
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.scaling_metrics import lddt_observed
from fastglycan.hip_device_policy import guarded_hip_runtime as gpu_guard
from run_response_readouts import readout_data,make_readout,readout_predict


def audit_response_readouts(root):
    runtime=gpu_guard();lock=json.loads((root/'lock.json').read_text());execution=json.loads((root/'execution.json').read_text());assert execution['complete'];plan=json.loads((root/'planned_jobs.json').read_text());assert len(plan['single'])==12
    store=FactorTeacherStore(Path(lock['teachers']),training_only=True);cache={};checks=[];manifest=[]
    def data(pi,pos):
        if (pi,pos) not in cache:cache[pi,pos]=readout_data(store,pi,pos)
        return cache[pi,pos]
    for job in plan['single']+plan['multi']:
        report=json.loads((root/'runs'/job['id']/'report.json').read_text());assert report['complete'] and report['s1_calls']==report['c4_calls']==0
        assert report['runtime']['cuda_visible'] is None and int(report['runtime']['hip_visible']) in range(6)
        assert all(store.rows[pi]['role']=='train' for pi,pos in job['sites'])
        assert report['candidate_exposures']==8192*19 and [x['step'] for x in report['history']]==[0,512,1024,2048,4096,8192]
        ds=[data(*x) for x in job['sites']]
        for row in report['history'][1:]:
            path=Path(row['checkpoint']);assert sha256(path)==row['sha256'];manifest.append(dict(path=str(path),sha256=row['sha256'],bytes=path.stat().st_size))
            if row['step'] not in [512,8192]:continue
            state=torch.load(path,map_location='cpu',weights_only=False);net=make_readout(job,ds).eval();net.load_state_dict(state['state_dict']);error=0.
            with torch.no_grad():
                for d,old in zip(ds,row['sites']):
                    p=readout_predict(net,d).double()
                    for name,t in [('raw',d['target']),('label',d['target'] if job['label']=='raw' else d['r32'])]:
                        t=t.double();v=(p-t).square().flatten(1).mean(1)/t.square().flatten(1).mean(1).clamp_min(1e-6);error=max(error,float(np.max(np.abs(v.cpu().numpy()-np.array(old[name]['nmse'])))));pc=p-p.mean(0);tc=t-t.mean(0);assert abs(float((pc-tc).square().sum()/tc.square().sum())-old[name]['centered_nmse'])<1e-5
            assert error<1e-5;checks.append(dict(job=job['id'],step=row['step'],max_nmse_error=error));del net,state,p
    # Separate NumPy implementation for one complete candidate's128channel R32 target.
    d=data(3,36);x=d['target'][0].double().cpu().numpy();u,s,v=np.linalg.svd(np.moveaxis(x,-1,0),full_matrices=False);y=np.moveaxis((u[:,:,:32]*s[:,None,:32])@v[:,:32],0,-1).astype('float32');err=float(np.max(np.abs(y-d['r32'][0].cpu().numpy())));assert err<1e-5
    # Validate phase decision from raw error, never label-only error or unseen-site outcome.
    valid={}
    for j in plan['single']:
        r=json.loads((root/'runs'/j['id']/'report.json').read_text());valid.setdefault(j['architecture']+'_'+j['label'],[]).append(r['history'][-1]['raw_nmse'])
    for key,values in valid.items():assert execution['decisions']['single'][key]['fit']==all(v<=.1 for v in values)
    if plan['multi']:
        assert len(plan['multi'])==2
        for j in plan['multi']:assert j['sites']==[[3,36],[3,83],[4,1],[5,64]]
    panel=root/'functional/closure';lk=json.loads((panel/'lock.json').read_text());coordinates=[];ranking_checks=lddt_checks=0
    with gzip.open(panel/'report.json.gz','rt') as f:functional=json.load(f)
    assert functional['complete'] and functional['oracle_target_s']
    for site in functional['sites']:
        wt=lk['aa'].index(lk['rows'][3]['sequence'][36]);tasks={}
        for arm in lk['arms']:
            for seed in lk['seeds']:tasks[arm,seed]=np.array([next(x['task'] for x in site['outputs'] if x['arm']==arm and x['noise']==seed and x['aa']==aa) for aa in lk['aa']])
        for r in site['ranking']:
            ids=np.arange(20) if r['includes_wt'] else np.delete(np.arange(20),wt);a=tasks[r['arm'],r['noise']][ids];b=tasks[r['reference'],r['noise']][ids]
            assert abs(float(spearmanr(a,b).statistic)-r['spearman'])<1e-12;assert abs(float(b[np.argsort(a,kind='stable')[0]]-b.min())-r['top1_regret'])<1e-12;ranking_checks+=1
        for ai,aa in enumerate(lk['aa']):
            label='p3_wt' if ai==wt else f'p3_s37_{aa}';path=panel/'worker_0'/f'{label}_coordinates.npz';coordinates.append(dict(path=str(path),sha256=sha256(path)))
            if ai!=next(x for x in range(20) if x!=wt):continue
            co=np.load(path)['coordinates'];inv=dict(np.load(panel/'worker_0'/f'{label}_inventory.npz'))
            for ki,arm in enumerate(lk['arms']):
                for ni,noise in enumerate(lk['seeds']):
                    measured=lddt_observed(co[ki,ni],co[0,ni],inv['residue_ids'])['score'];saved=next(x['fidelity']['all_atom_lddt'] for x in site['outputs'] if x['aa']==aa and x['arm']==arm and x['noise']==noise);assert abs(measured-saved)<1e-12;lddt_checks+=1
    write_json(root/'checkpoint_manifest.json',manifest);write_json(root/'coordinate_manifest.json',coordinates)
    write_json(root/'independent_audit.json',dict(complete=True,runtime=runtime,checkpoint_hashes=len(manifest),checkpoint_replays=checks,training_roles='train only',numpy_oracle_max_abs=err,ranking_checks=ranking_checks,lddt_checks=lddt_checks,coordinates=len(coordinates),multicontext_selection_recomputed=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();audit_response_readouts(a.root)
