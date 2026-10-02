"""Bounded readout experiment; single-site zero-shot results never gate multi-context."""
import argparse,copy,hashlib,json,os,signal,subprocess,time
from pathlib import Path


def control_response_readouts(root):
    base=root.parent;virtual=Path('/data/user/shuang886/Folding')/root.name
    def load(p):return json.loads(p.read_text())
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def save(name,value):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');tmp.replace(p)
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=f'{virtual}/code/src:{virtual}/code/scripts');env.pop('CUDA_VISIBLE_DEVICES',None);env.pop('ROCR_VISIBLE_DEVICES',None)
    def pool(tasks,label,cpu=False):
        pending=list(tasks);active={};done=[];start=time.time()
        while pending or active:
            for device in range(4):
                if pending and device not in active:
                    task=pending.pop(0);cmd=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot','-b',str(base)+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u',str(virtual/'code/scripts'/task['script']),'--root',str(virtual),*task['args']]
                    log=root/'logs'/f'{task["id"]}.log';log.parent.mkdir(exist_ok=True)
                    with log.open('w') as f:p=subprocess.Popen(cmd,env=dict(env,HIP_VISIBLE_DEVICES='' if cpu else str(device)),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
                    active[device]=(p,task,time.time())
            for device,(p,t,startjob) in list(active.items()):
                if p.poll() is None and time.time()-startjob>3600:os.killpg(p.pid,signal.SIGTERM)
                if p.poll() is not None:done.append(dict(id=t['id'],exit=p.returncode,device=None if cpu else device,seconds=time.time()-startjob));del active[device]
            save('status.json',dict(complete=False,phase=label,pending=len(pending),active=[dict(device=d,pid=p.pid,id=t['id'],seconds=time.time()-s) for d,(p,t,s) in active.items()],done=done))
            if active:time.sleep(3)
        save(label+'_execution.json',dict(complete=all(x['exit']==0 for x in done),jobs=done,seconds=time.time()-start))
        assert all(x['exit']==0 for x in done),f'{label} failed: preserve logs, no automatic retry'
    def task(job,mode='train'):return dict(id=job['id'],script='run_response_readouts.py',args=['--mode',mode,'--job',job['id']])
    def jobfile(job):assert not (root/'jobs'/f'{job["id"]}.json').exists();save(f'jobs/{job["id"]}.json',job);return job
    def report(job):return load(root/'runs'/job['id']/'report.json')
    def cp(job):
        last=report(job)['history'][-1];return dict(path=last['checkpoint'],sha256=last['sha256'],family='readout')
    start=time.time();decisions={}
    try:
        assert not (root/'lock.json').exists();teacher=base/'factor_student_pilot_v1_20261002';tl=load(teacher/'teacher_lock.json');code=root/'code'
        lock=dict(schema='response_readout_v1',teachers=str(virtual.parent/teacher.name),teacher_lock_sha256=sha(teacher/'teacher_lock.json'),teacher_manifest_sha256=sha(teacher/'teacher_manifest.json'),checkpoints=[512,1024,2048,4096,8192],seeds=[231301,231303],allowed_devices=list(range(4)),physical_pci_guard=True,cuda_selector=False,protocol_sha256=sha(code/'docs/mini_response_readout_v1.md'),code_hashes={str(virtual/'code'/p.relative_to(code)):sha(p) for p in code.rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']})
        save('lock.json',lock);jobs=[];groups={}
        for kind in ['free_hidden','pair','channel']:
            for target in ['raw','r32']:
                group=[]
                for seed in lock['seeds']:
                    j=jobfile(dict(id=f'single_{kind}_{target}_s{seed}',phase='single',architecture=kind,label=target,seed=seed,sites=[[3,36]],steps=8192,lr=.001,weight_decay=.0001));jobs.append(j);group.append(j)
                groups[kind+'_'+target]=group
        save('planned_jobs.json',dict(single=jobs,multi=[]))
        pool([dict(id='preflight',script='run_response_readouts.py',args=['--mode','preflight'])],'preflight')
        pool([task(j) for j in jobs],'single')
        decisions['single']={name:dict(raw_nmse=[report(j)['history'][-1]['raw_nmse'] for j in js],label_nmse=[report(j)['history'][-1]['label_nmse'] for j in js],fit=all(report(j)['history'][-1]['raw_nmse']<=.1 for j in js)) for name,js in groups.items()}
        eligible=[(name,js) for name,js in groups.items() if js[0]['architecture']!='free_hidden' and decisions['single'][name]['fit']]
        selected=[];multi=[]
        if eligible:
            best=min(sum(decisions['single'][name]['raw_nmse'])/2 for name,js in eligible)
            name,selected=min([(n,j) for n,j in eligible if sum(decisions['single'][n]['raw_nmse'])/2<=best+1e-6],key=lambda x:(report(x[1][0])['parameters'],x[0]));decisions['selected']=name
            diagnostic=[]
            for j in selected:diagnostic.append(jobfile(dict(id='single_unseen_'+str(j['seed']),checkpoint=cp(j)['path'],sha256=cp(j)['sha256'],sites=[[3,83]])))
            pool([task(j,'evaluate') for j in diagnostic],'single_unseen_diagnostic')
            for j in selected:multi.append(jobfile(dict(j,id='multi_'+str(j['seed']),phase='multi',sites=[[3,36],[3,83],[4,1],[5,64]])))
            save('planned_jobs.json',dict(single=jobs,multi=multi));pool([task(j) for j in multi],'multi')
            evaluation=[]
            for j in multi:
                for label,sites in [('unseen_site',[[4,24],[5,33]]),('unseen_protein',[[6,9],[6,16]])]:evaluation.append(jobfile(dict(id=label+'_'+str(j['seed']),checkpoint=cp(j)['path'],sha256=cp(j)['sha256'],sites=sites)))
            pool([task(j,'evaluate') for j in evaluation],'multi_evaluation');decisions['multi']=dict(executed=True,fresh_initializations=True,zero_shot_site_gate=False)
        else:decisions['multi']=dict(executed=False,reason='no shared readout fit both seeds on raw-response threshold')
        save('decisions.json',decisions)
        # Original whole-field fit closure always runs, regardless of new fit outcomes.
        old=base/'deep_validation_v2_global_dense_20261002';assert load(old/'execution.json')['complete'];checkpoints=[]
        for seed in lock['seeds']:
            r=load(old/'runs'/f'global_dense_lr1e-03_s{seed}'/'report.json');last=r['history'][-1];checkpoints.append(dict(path=last['checkpoint'],sha256=last['checkpoint_sha256'],family='whole_field'))
        checkpoints += [cp(j) for j in selected];rows=copy.deepcopy(tl['rows']);rows[3]['positions']=[36]
        panel=dict(tl,teachers=lock['teachers'],rows=rows,assignments=[[3],[],[],[],[],[]],score_assignments=[[dict(parent_index=3,position=36,worker=0)],[],[],[],[],[]],checkpoints=checkpoints,arms=['exact','baseline','wt_z','oracle_r32','whole_field_0','whole_field_1']+[f'shared_{i}' for i in range(len(selected))])
        save('functional/closure/lock.json',panel)
        pool([dict(id='closure_decode',script='readout_functional.py',args=['--mode','decode'])],'closure_decode')
        pool([dict(id=f'closure_score_{i}',script='readout_functional.py',args=['--mode','score','--index',str(i)]) for i in range(6)],'closure_score',cpu=True)
        pool([dict(id='closure_collect',script='readout_functional.py',args=['--mode','collect'])],'closure_collect',cpu=True)
        save('execution.json',dict(complete=True,decisions=decisions,seconds=time.time()-start));save('status.json',dict(complete=True,active=[],phase='closed'))
    except Exception as e:save('execution.json',dict(complete=False,error=repr(e),seconds=time.time()-start,decisions=decisions));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();control_response_readouts(a.root)
