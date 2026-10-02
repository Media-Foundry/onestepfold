"""Recompute retained whole-field outputs and all checkpoint hashes."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fastglycan.deep_dense_control import GlobalDenseControl
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.paired_teacher_protocol import sha256,write_json
from run_deep_validation_v2 import gpu_guard,site_tensors,predict_site


def audit_global_dense(root):
    runtime=gpu_guard();lock=json.loads((root/'lock.json').read_text());jobs=json.loads((root/'planned_jobs.json').read_text());assert len(jobs)==6
    store=FactorTeacherStore(Path(lock['teachers']),training_only=True);d=site_tensors(store,3,36,oracle_floor=False);checks=[];manifest=[]
    for job in jobs:
        report=json.loads((root/'runs'/job['id']/'report.json').read_text());assert report['complete'] and report['s1_calls']==report['c4_calls']==0
        assert report['runtime']['hip_visible'] in list(map(str,range(6))) and report['runtime']['cuda_visible'] is None
        assert report['candidate_exposures']==8192*19 and job['train_sites']==[[3,36]]
        assert [x['step'] for x in report['history']]==[0,512,1024,2048,4096,8192]
        for row in report['history'][1:]:
            path=Path(row['checkpoint']);assert sha256(path)==row['checkpoint_sha256'];manifest.append(dict(path=str(path),sha256=row['checkpoint_sha256'],bytes=path.stat().st_size))
            if row['step'] not in [512,8192]:continue
            state=torch.load(path,map_location='cpu',weights_only=False);model=GlobalDenseControl(**job['architecture']).cuda().eval();model.load_state_dict(state['state_dict'])
            with torch.no_grad():
                pred=predict_site(model,d).double();target=d['target'].double();nmse=(pred-target).square().flatten(1).mean(1)/target.square().flatten(1).mean(1).clamp_min(1e-6);center=target-target.mean(0);pc=pred-pred.mean(0);cn=float((pc-center).square().sum()/center.square().sum())
            err=float(np.max(np.abs(nmse.cpu().numpy()-np.array(row['sites'][0]['nmse']))));assert err<1e-5 and abs(cn-row['centered_nmse'])<1e-5;checks.append(dict(job=job['id'],step=row['step'],max_nmse_error=err));del state,model,pred
    write_json(root/'checkpoint_manifest.json',manifest);write_json(root/'independent_audit.json',dict(complete=True,runtime=runtime,checkpoint_hashes=len(manifest),replays=checks,all_training_inputs_train_only=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();audit_global_dense(a.root)
