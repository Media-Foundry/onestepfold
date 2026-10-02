"""Describe already-captured H trajectories; these are not learned transitions."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.paired_teacher_protocol import sha256,write_json


def analyze_blockwise(root):
    path=root/'blockwise/report.json'
    if not path.exists():write_json(root/'blockwise_analysis.json',dict(complete=True,executed=False,reason='H gate not triggered'));return
    report=json.loads(path.read_text());assert report['complete'];lock=json.loads((root/'lock.json').read_text());store=FactorTeacherStore(Path(lock['teachers']),training_only=True);records=report['records'];wt=torch.load(records[0]['path'],map_location='cpu',weights_only=False);rows=[];manifest=[];previous_check=[]
    for item in records:
        p=Path(item['path']);assert sha256(p)==item['sha256'];manifest.append(dict(path=str(p),sha256=item['sha256'],bytes=p.stat().st_size));value=torch.load(p,map_location='cpu',weights_only=False)
        teacher=store.load(3,36,item['aa']);assert all(torch.equal(a,b) for a,b in zip(value['boundaries'][-1],teacher['conditioning'][1:]));assert len(value['boundaries'])==16 and len(value['recycle_inputs'])==4
        if item is records[0]:continue
        for cycle in range(4):
            previous=[a.double()-b.double() for a,b in zip(value['recycle_inputs'][cycle],wt['recycle_inputs'][cycle])]
            for offset in range(4):
                index=cycle*4+offset;current=[a.double()-b.double() for a,b in zip(value['boundaries'][index],wt['boundaries'][index])];fields={}
                for name,before,after in zip(['s','z'],previous,current):
                    energy=float(after.square().sum());den=max(energy,1e-30);inner=float((before*after).sum());scale=float(before.square().sum()*after.square().sum())**.5
                    fields[name]=dict(energy=energy,relative_transition_squared_error=float((after-before).square().sum())/den,cosine_previous_response=inner/max(scale,1e-30))
                fields['spatial_r32_residual']=item['response'][index]['spatial_r32_residual'];rows.append(dict(aa=item['aa'],cycle=cycle+1,block=(offset+1)*4,**fields));previous=current
        if not previous_check:
            delta=(value['boundaries'][0][1].double()-wt['boundaries'][0][1].double()).numpy();sigma=np.linalg.svd(np.moveaxis(delta,-1,0),compute_uv=False);res=float((sigma[:,32:]**2).sum()/(sigma**2).sum());saved=item['response'][0]['spatial_r32_residual'];assert abs(res-saved)<1e-10;previous_check.append(dict(aa=item['aa'],boundary=1,numpy_r32_residual=res,saved=saved))
    summary=[]
    for cycle in range(1,5):
        for block in [4,8,12,16]:
            group=[x for x in rows if x['cycle']==cycle and x['block']==block];summary.append(dict(cycle=cycle,block=block,s_energy_mean=float(np.mean([x['s']['energy'] for x in group])),z_energy_mean=float(np.mean([x['z']['energy'] for x in group])),z_step_relative_error_mean=float(np.mean([x['z']['relative_transition_squared_error'] for x in group])),z_cosine_mean=float(np.mean([x['z']['cosine_previous_response'] for x in group])),spatial_r32_residual_mean=float(np.mean([x['spatial_r32_residual'] for x in group]))))
    write_json(root/'blockwise_analysis.json',dict(complete=True,executed=True,rows=rows,summary=summary,manifest=manifest,independent_numpy_check=previous_check,final_native_replays=20,interpretation='Descriptive response evolution only; neither transition learnability nor final-map impossibility was tested.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();torch.set_num_threads(1);analyze_blockwise(a.root)
