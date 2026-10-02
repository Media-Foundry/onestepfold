"""Six bounded fresh whole-field controls, after the original GPU audit closes."""
import argparse,hashlib,json,os,signal,subprocess,time
from pathlib import Path


def control_global_dense(root):
    base=root.parent;old=base/'deep_validation_v2_20261002';virtual=Path('/data/user/shuang886/Folding')/root.name
    def load(p):return json.loads(p.read_text())
    def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def save(name,value):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');tmp.replace(p)
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=f'{virtual}/code/src:{virtual}/code/scripts');env.pop('CUDA_VISIBLE_DEVICES',None);env.pop('ROCR_VISIBLE_DEVICES',None)
    def launch(mode,device,job=None):
        script='audit_global_dense_control.py' if mode=='audit' else 'run_global_dense_control.py'
        cmd=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot','-b',str(base)+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u',str(virtual/'code/scripts'/script),'--root',str(virtual)]
        if mode!='audit':cmd+=['--mode',mode]
        if job:cmd+=['--job',job]
        with (root/'logs'/f'{job or mode}.log').open('w') as f:return subprocess.Popen(cmd,env=dict(env,HIP_VISIBLE_DEVICES=str(device)),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    start=time.time();active={}
    try:
        assert not (root/'lock.json').exists(),'immutable run root'
        assert all(load(old/n)['complete'] for n in ['execution.json','audit_execution.json'])
        teacher=base/'factor_student_pilot_v1_20261002';code=root/'code';(root/'logs').mkdir(exist_ok=True)
        lock=dict(schema='deep_v2_whole_field_dense_correction',teachers=str(virtual.parent/teacher.name),teacher_lock_sha256=digest(teacher/'teacher_lock.json'),teacher_manifest_sha256=digest(teacher/'teacher_manifest.json'),checkpoints=[512,1024,2048,4096,8192],allowed_devices=list(range(6)),cuda_selector=False,code_hashes={str(virtual/'code'/p.relative_to(code)):digest(p) for p in code.rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']},original_execution_sha256=digest(old/'execution.json'),original_audit_sha256=digest(old/'independent_audit.json'),amendment_sha256=digest(code/'docs/mini_deep_validation_v2_dense_amendment.md'))
        save('lock.json',lock);jobs=[]
        for lr in [1e-4,3e-4,1e-3]:
            for seed in [231301,231303]:
                job=dict(id=f'global_dense_lr{lr:.0e}_s{seed}',phase='dense_correction',architecture=dict(size='small',content=False,output='global_dense',length=84),seed=seed,lr=lr,weight_decay=1e-4,train_sites=[[3,36]],steps=8192,kind='network');jobs.append(job);save(f'jobs/{job["id"]}.json',job)
        save('planned_jobs.json',jobs);p=launch('preflight',0);assert p.wait(timeout=600)==0,'preflight failed; no jobs launched'
        for device,j in enumerate(jobs):active[device]=(launch('train',device,j['id']),j,time.time())
        finished=[]
        while active:
            for device,(p,j,began) in list(active.items()):
                if p.poll() is None and time.time()-began>7200:os.killpg(p.pid,signal.SIGTERM)
                if p.poll() is not None:
                    finished.append(dict(job=j['id'],device=device,exit=p.returncode,seconds=time.time()-began));del active[device]
            save('status.json',dict(complete=False,active=[dict(device=d,pid=p.pid,job=j['id'],seconds=time.time()-b) for d,(p,j,b) in active.items()],finished=finished))
            if active:time.sleep(3)
        assert all(x['exit']==0 for x in finished),'failed run retained, no retry'
        results=[]
        for lr in [1e-4,3e-4,1e-3]:
            selected=[j for j in jobs if j['lr']==lr];reports=[load(root/'runs'/j['id']/'report.json') for j in selected];assert all(r['complete'] for r in reports)
            values=[r['history'][-1]['mean_nmse'] for r in reports];results.append(dict(lr=lr,nmse=values,centered_nmse=[r['history'][-1]['centered_nmse'] for r in reports],primary=all(v<=.1 for v in values),secondary=all(v<=.12 for v in values)))
        save('training_execution.json',dict(complete=True,jobs=finished,results=results,seconds=time.time()-start))
        p=launch('audit',0);assert p.wait(timeout=1800)==0,'independent audit failed'
        save('execution.json',dict(complete=True,results=results,audited=True,seconds=time.time()-start,transfer_phases_executed=False));save('status.json',dict(complete=True,active=[]))
    except Exception as e:
        for p,j,b in active.values():
            if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
        save('execution.json',dict(complete=False,error=repr(e),seconds=time.time()-start));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();control_global_dense(a.root)
