"""Bounded detached controller; never trains after inspecting confirmation scores."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path


def control_context_replication(root):
    virtual=Path('/data/user/shuang886/Folding')/root.name;start=time.monotonic();stages=[]
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',
             PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
             PYTHONPATH=f'{virtual}/code/src:{virtual}/code/scripts')
    for key in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES'):env.pop(key,None)
    def save(name,value):
        path=root/name;tmp=path.with_suffix(path.suffix+'.part');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)
    def pool(mode,tasks,cpu=False,timeout=7200):
        pending=list(enumerate(tasks));active=[];stage=dict(mode=mode,complete=False,jobs=[]);stages.append(stage)
        (root/'logs').mkdir(exist_ok=True)
        try:
            while pending or active:
                busy={slot for p,i,slot,t in active}
                for slot in range(4):
                    if slot in busy or not pending:continue
                    index,args=pending.pop(0)
                    script='audit_context_replication.py' if mode=='audit' else 'run_context_replication.py'
                    cmd=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
                         '-b',str(root.parent)+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u',
                         str(virtual/'code/scripts'/script),'--root',str(virtual)]
                    if mode!='audit':cmd+=['--mode',mode]
                    cmd+=args
                    with (root/'logs'/f'{len(stages)}_{mode}_{index}.log').open('w') as log:
                        p=subprocess.Popen(cmd,env=dict(env,HIP_VISIBLE_DEVICES='' if cpu else str(slot)),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    active.append((p,index,slot,time.monotonic()))
                for p,index,slot,begin in list(active):
                    if time.monotonic()-begin>timeout:raise TimeoutError(f'{mode} task{index} exceeded {timeout}s')
                    if p.poll() is not None:
                        stage['jobs'].append(dict(index=index,exit=p.returncode,seconds=time.monotonic()-begin))
                        active.remove((p,index,slot,begin))
                        if p.returncode:raise RuntimeError(f'{mode} task{index} exit{p.returncode}')
                save('status.json',dict(complete=False,phase=mode,active=[dict(pid=p.pid,index=i,slot=s,seconds=time.monotonic()-t) for p,i,s,t in active],pending=len(pending),stages=stages,seconds=time.monotonic()-start))
                if active:time.sleep(5)
            stage['complete']=True
        except BaseException:
            for p,index,slot,begin in active:
                if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
            raise
    try:
        assert not (root/'lock.json').exists()
        pool('prepare',[[]],True,1800)
        pool('preflight',[['--index',str(i)] for i in range(4)],True,1800)
        pool('freeze_preflight',[[]],True,1800)
        pool('teacher',[['--index',str(i)] for i in range(4)],False,7200)
        pool('score',[['--index',str(i)] for i in range(4)],True,3600)
        pool('labels',[[]],True,1800)
        lock=json.loads((root/'lock.json').read_text());jobs=sorted(lock['jobs'],key=lambda j:-j['steps'])
        pool('train',[['--job',j['id']] for j in jobs if j['architecture']=='context'],False,7200)
        pool('train',[['--job',j['id']] for j in jobs if j['architecture']=='aa_only'],True,7200)
        pool('eval',[['--index',str(i)] for i in range(4)],False,1800)
        pool('collect',[[]],True,1800)
        pool('audit',[[]],True,3600)
        save('execution.json',dict(complete=True,stages=stages,seconds=time.monotonic()-start))
        save('status.json',dict(complete=True,phase='closed',active=[],seconds=time.monotonic()-start))
    except BaseException as error:
        save('execution.json',dict(complete=False,error=repr(error),stages=stages,seconds=time.monotonic()-start));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);control_context_replication(p.parse_args().root)
