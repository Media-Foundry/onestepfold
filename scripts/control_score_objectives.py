"""Bounded A/B/C controller; no retries, extensions or outcome-dependent branches."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path


def control_score_objectives(root):
    virtual=Path('/data/user/shuang886/Folding')/root.name;start=time.monotonic();stages=[]
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',
             PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=f'{virtual}/code/src:{virtual}/code/scripts')
    for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES'):env.pop(k,None)
    def save(name,data):
        p=root/name;t=p.with_suffix(p.suffix+'.part');t.write_text(json.dumps(data,indent=2)+'\n');t.replace(p)
    def pool(mode,tasks,cpu=False,timeout=7200):
        pending=list(enumerate(tasks));active=[];stage=dict(mode=mode,complete=False,jobs=[]);stages.append(stage);(root/'logs').mkdir(exist_ok=True)
        try:
            while pending or active:
                busy={s for p,i,s,t in active}
                for slot in range(4):
                    if slot in busy or not pending:continue
                    index,args=pending.pop(0)
                    script={'audit':'audit_score_objectives.py','summarize':'summarize_score_objectives.py'}.get(mode,'run_score_objectives.py')
                    cmd=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot','-b',str(root.parent)+':/data/user/shuang886/Folding',
                         '/home/pc/anaconda3/envs/fold/bin/python','-u',str(virtual/'code/scripts'/script),'--root',str(virtual)]
                    if mode not in ('audit','summarize'):cmd+=['--mode',mode]
                    cmd+=args
                    with (root/'logs'/f'{len(stages)}_{mode}_{index}.log').open('w') as log:
                        p=subprocess.Popen(cmd,env=dict(env,HIP_VISIBLE_DEVICES='' if cpu else str(slot)),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    active.append((p,index,slot,time.monotonic()))
                for p,index,slot,t in list(active):
                    if time.monotonic()-t>timeout:raise TimeoutError(f'{mode} task{index} >{timeout}s')
                    if p.poll() is not None:
                        stage['jobs'].append(dict(index=index,exit=p.returncode,seconds=time.monotonic()-t));active.remove((p,index,slot,t))
                        if p.returncode:raise RuntimeError(f'{mode} task{index} exit{p.returncode}')
                save('status.json',dict(complete=False,phase=mode,active=[dict(pid=p.pid,index=i,slot=s,seconds=time.monotonic()-t) for p,i,s,t in active],pending=len(pending),stages=stages,seconds=time.monotonic()-start))
                if active:time.sleep(5)
            stage['complete']=True
        except BaseException:
            for p,i,s,t in active:
                if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
            raise
    try:
        assert not (root/'lock.json').exists()
        pool('prepare',[[]],True,1800)
        jobs=json.loads((root/'lock.json').read_text())['jobs']
        pool('train',[['--job',j['id']] for j in jobs if j['architecture']=='context'])
        pool('train',[['--job',j['id']] for j in jobs if j['architecture']=='aa_only'],True)
        pool('eval',[['--index',str(i)] for i in range(4)],False,1800)
        pool('collect',[[]],True,1800)
        pool('audit',[[]],True,1800)
        pool('summarize',[[]],True,1800)
        save('execution.json',dict(complete=True,stages=stages,seconds=time.monotonic()-start))
        save('status.json',dict(complete=True,phase='closed',active=[],seconds=time.monotonic()-start))
    except BaseException as e:
        save('execution.json',dict(complete=False,error=repr(e),stages=stages,seconds=time.monotonic()-start));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);control_score_objectives(p.parse_args().root)
