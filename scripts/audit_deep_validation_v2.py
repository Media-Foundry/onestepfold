"""Independent terminal/checkpoint/selection and saved functional-score audit."""
import argparse,gzip,json
from pathlib import Path
import numpy as np
import torch
from scipy.stats import spearmanr
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.deep_response_student import DeepResponseStudent
from fastglycan.scaling_metrics import lddt_observed
from run_deep_validation_v2 import gpu_guard,site_tensors,predict_site


def audit_deep_validation(root):
    runtime=gpu_guard();lock=json.loads((root/'lock.json').read_text());execution=json.loads((root/'execution.json').read_text());assert execution['complete'];plan=json.loads((root/'planned_jobs.json').read_text());assert len(plan['A'])==32 and len(plan['B'])==6
    store=FactorTeacherStore(Path(lock['teachers']),training_only=True);d=site_tensors(store,3,36,oracle_floor=False);checks=[];manifest=[];paired512=[]
    for job in plan['A']+plan['B']:
        out=root/'runs'/job['id'];report=json.loads((out/'report.json').read_text());assert report['complete'] and report['s1_calls']==report['c4_calls']==0
        assert report['runtime']['hip_visible'] in list(map(str,range(6))) and report['runtime']['cuda_visible'] is None
        assert job['train_sites']==[[3,36]] and report['candidate_exposures']==8192*19
        assert [x['step'] for x in report['history']]==[0,512,1024,2048,4096,8192]
        for item in report['history'][1:]:
            path=Path(item['checkpoint']);assert sha256(path)==item['checkpoint_sha256'];manifest.append(dict(path=str(path),sha256=item['checkpoint_sha256'],bytes=path.stat().st_size))
            if item['step'] not in [512,8192]:continue
            saved=torch.load(path,map_location='cpu',weights_only=False)
            with torch.no_grad():
                if job['kind']=='free':
                    u,v=[saved['state_dict'][str(i)].cuda() for i in range(2)];pred=(u.permute(0,2,1,3)@v.permute(0,2,3,1)).permute(0,2,3,1)/np.sqrt(32)
                else:
                    net=DeepResponseStudent(**job['architecture']).cuda().eval();net.load_state_dict(saved['state_dict']);pred=predict_site(net,d)
                target=d['target'].double();pred=pred.double();nmse=(pred-target).square().flatten(1).mean(1)/target.square().flatten(1).mean(1).clamp_min(1e-6)
                centered=target-target.mean(0);pc=pred-pred.mean(0);centered_error=float((pc-centered).square().sum()/centered.square().sum())
            err=float(np.max(np.abs(nmse.cpu().numpy()-np.array(item['sites'][0]['nmse']))));assert err<1e-5 and abs(centered_error-item['sites'][0]['centered_nmse'])<1e-5
            checks.append(dict(job=job['id'],step=item['step'],max_nmse_error=err))
            if item['step']==512 and job['phase']=='A' and job['lr']==3e-4 and job['architecture']==dict(size='small',content=False):
                old=root.parent/f'factor_learnability_v1_20261002/stage_0_{0 if job["seed"]==231301 else 1}/final.pt';prior=torch.load(old,map_location='cpu',weights_only=False)['state_dict'];diff=max(float((saved['state_dict'][k].cpu()-v).abs().max()) for k,v in prior.items());paired512.append(dict(seed=job['seed'],max_parameter_difference=diff,bitwise=all(torch.equal(saved['state_dict'][k].cpu(),v) for k,v in prior.items())))
            del saved,pred
            if job['kind']!='free':del net
    decisions=json.loads((root/'decisions.json').read_text());free=[json.loads((root/'runs'/j['id']/'report.json').read_text())['history'][-1]['mean_nmse'] for j in plan['A'] if j['kind']=='free'];assert decisions['free_gate']==all(x<=.075 for x in free)
    for folder in ['runs','evaluations']:
        for p in (root/folder).glob('*/report.json'):
            r=json.loads(p.read_text());assert r['complete'];job=r['job']
            if folder=='runs':assert all(store.rows[pi]['role']=='train' for pi,pos in job['train_sites'])
            if job['id'].startswith('C_'):assert job['sites']==[[3,83]]
    ranks=lddt=0;coord=[]
    for path in (root/'functional').glob('*/report.json.gz'):
        with gzip.open(path,'rt') as f:r=json.load(f)
        lk=json.loads((path.parent/'lock.json').read_text());assert r['complete'];seen=set()
        for site in r['sites']:
            pi,pos=site['parent_index'],site['position'];wtid=lk['aa'].index(lk['rows'][pi]['sequence'][pos]);tasks={}
            for arm in lk['arms']:
                for seed in lk['seeds']:tasks[arm,seed]=np.array([next(x['task'] for x in site['outputs'] if x['arm']==arm and x['noise']==seed and x['aa']==aa) for aa in lk['aa']])
            for rank in site['ranking']:
                ids=np.arange(20) if rank['includes_wt'] else np.delete(np.arange(20),wtid);a=tasks[rank['arm'],rank['noise']][ids];b=tasks[rank['reference'],rank['noise']][ids]
                assert abs(float(spearmanr(a,b).statistic)-rank['spearman'])<1e-12
                assert abs(float(b[np.argsort(a,kind='stable')[0]]-b.min())-rank['top1_regret'])<1e-12;ranks+=1
            wi=next(i for i,ps in enumerate(lk['assignments']) if pi in ps);work=path.parent/f'worker_{wi}'
            for ai,aa in enumerate(lk['aa']):
                label=f'p{pi}_wt' if ai==wtid else f'p{pi}_s{pos+1}_{aa}';p=work/f'{label}_coordinates.npz'
                if p not in seen:coord.append(dict(path=str(p),sha256=sha256(p)));seen.add(p)
                if ai!=next(x for x in range(20) if x!=wtid):continue
                co=np.load(p)['coordinates'];inv=dict(np.load(work/f'{label}_inventory.npz'))
                for k,arm in enumerate(lk['arms']):
                    measured=lddt_observed(co[k,0],co[0,0],inv['residue_ids'])['score'];saved=next(x['fidelity']['all_atom_lddt'] for x in site['outputs'] if x['aa']==aa and x['arm']==arm and x['noise']==lk['seeds'][0]);assert abs(measured-saved)<1e-12;lddt+=1
    write_json(root/'checkpoint_manifest.json',manifest);write_json(root/'coordinate_manifest.json',coord)
    write_json(root/'independent_audit.json',dict(complete=True,runtime=runtime,continuous_runs=38,checkpoint_hashes=len(manifest),recomputed_checkpoints=checks,paired_previous512=paired512,all_training_inputs_train_only=True,free_gate_recomputed=True,ranking_checks=ranks,independent_lddt_checks=lddt,coordinate_packets=len(coord)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();audit_deep_validation(a.root)
