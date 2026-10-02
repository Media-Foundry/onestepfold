import argparse,hashlib
from pathlib import Path
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json


def prepare_factor_training(root):
    assert rt.load_json(root/'teacher_report.json')['complete'] and not (root/'student_lock.json').exists();t=rt.load_json(root/'teacher_lock.json')
    train=sorted([r for r in t['rows'] if r['role']=='train'],key=lambda r:hashlib.sha256(('factor-student-probe:'+r['group_id']).encode()).hexdigest())[:4]
    eval_ids=[r['index'] for r in t['rows'] if r['role']=='validation']+[r['index'] for r in train]
    assign=[[] for _ in range(8)];load=[0]*8
    for i in sorted(eval_ids,key=lambda i:len(t['rows'][i]['sequence']),reverse=True):
        w=min(range(8),key=lambda w:load[w]);assign[w].append(i);load[w]+=len(t['rows'][i]['sequence'])**2
    write_json(root/'student_lock.json',dict(schema='factor_student_pilot_v1',teacher_lock_sha256=sha256(root/'teacher_lock.json'),teacher_manifest_sha256=sha256(root/'teacher_manifest.json'),architecture=dict(single_channels=384,pair_channels=128,rank=32,width=128),initialization_seeds=[230301,230303],sampling_seed=230401,lr=3e-4,weight_decay=1e-4,updates=1024,warmup=256,loss_weights=dict(coordinate=.25,distance=.25,clash=.01,chirality=.1),evaluation_parents=eval_ids,evaluation_assignments=assign,code_hashes={str(p):sha256(p) for p in (root/'student_code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']},oracle_target_s=True,training_only_roles=['train'],deployment_accepted=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();prepare_factor_training(a.root)
