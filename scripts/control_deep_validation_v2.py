"""Persistent bounded controller; only physical HIP devices0--5, no CUDA selector."""
import argparse,copy,hashlib,json,os,signal,subprocess,time
from pathlib import Path


def control_deep_validation(root):
    root=Path(root);base=root.parent;virtual=Path('/data/user/shuang886/Folding')/root.name
    python='/home/pc/anaconda3/envs/fold/bin/python';proot='/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot'
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=f'{virtual}/code/src:{virtual}/code/scripts')
    env.pop('CUDA_VISIBLE_DEVICES',None);env.pop('ROCR_VISIBLE_DEVICES',None)
    def load(p):return json.loads(p.read_text())
    def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def save(name,value):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temp.replace(p)
    def command(script,args):return [proot,'-b',str(base)+':/data/user/shuang886/Folding',python,'-u',str(virtual/'code/scripts'/script),'--root',str(virtual),*args]
    def jobfile(job):
        p=root/'jobs'/f'{job["id"]}.json';assert not p.exists();save(str(p.relative_to(root)),job);return job
    def run_pool(tasks,label,gpu=True):
        pending=list(tasks);active={};finished=[];start=time.time()
        while pending or active:
            for device in range(6):
                if pending and device not in active:
                    task=pending.pop(0);log=root/'logs'/f'{task["label"]}.log';log.parent.mkdir(exist_ok=True)
                    handle=log.open('w');process=subprocess.Popen(command(task['script'],task['args']),env=dict(env,HIP_VISIBLE_DEVICES=str(device) if gpu else ''),stdout=handle,stderr=subprocess.STDOUT,start_new_session=True);handle.close();active[device]=(process,task,time.time())
            for device,(process,task,began) in list(active.items()):
                if process.poll() is None and time.time()-began>7200:os.killpg(process.pid,signal.SIGTERM)
                if process.poll() is not None:
                    finished.append(dict(label=task['label'],gpu=device if gpu else None,pid=process.pid,exit=process.returncode,seconds=time.time()-began));del active[device]
            save('status.json',dict(complete=False,phase=label,pending=len(pending),active=[dict(device=d,pid=p.pid,label=t['label'],elapsed=time.time()-b) for d,(p,t,b) in active.items()],finished=finished,seconds=time.time()-start))
            if active:time.sleep(3)
        result=dict(complete=all(x['exit']==0 for x in finished),jobs=finished,seconds=time.time()-start);save(f'{label}_execution.json',result)
        if not result['complete']:raise RuntimeError(f'{label}: execution failed; see retained job logs, no automatic retry')
    def task(job,mode='train'):return dict(label=job['id'],script='run_deep_validation_v2.py',args=['--mode',mode,'--job',job['id']])
    def train_result(job):return load(root/'runs'/job['id']/'report.json')
    def checkpoint(job):
        r=train_result(job);assert r['complete'];last=r['history'][-1];return dict(path=last['checkpoint'],sha256=last['checkpoint_sha256'],job_id=job['id'])
    def base_job(name,arch,seed,lr,sites,phase='A',kind='network'):
        return dict(id=f'{phase}_{name}_lr{lr:.0e}_s{seed}',phase=phase,architecture=arch,seed=seed,lr=lr,weight_decay=0. if kind=='free' else 1e-4,train_sites=sites,steps=8192,kind=kind)
    def evaluate(jobs,sites,label,step=None):
        tasks=[];evaluation=[]
        for j in jobs:
            cp=checkpoint(j)
            if step is not None:
                saved=next(x for x in train_result(j)['history'] if x['step']==step);cp=dict(path=saved['checkpoint'],sha256=saved['checkpoint_sha256'])
            job=jobfile(dict(id=f'{label}_{j["seed"]}',checkpoint=cp['path'],checkpoint_sha256=cp['sha256'],sites=sites,phase=label));tasks.append(task(job,'evaluate'));evaluation.append(job)
        run_pool(tasks,label)
        result=[load(root/'evaluations'/j['id']/'report.json') for j in evaluation]
        return result
    def transfer_pass(results):return len(results)==2 and all(r['mean_nmse']<.8 and r['centered_nmse']<.8 for r in results)
    def fit_pass(jobs,threshold=.1):return len(jobs)==2 and all(train_result(j)['history'][-1]['mean_nmse']<=threshold for j in jobs)
    def prepare_panel(panel,rows,gt,seeds,assignments,checkpoints,teacher_lock):
        directory=root/'functional'/panel;directory.mkdir(parents=True,exist_ok=False);scores=[[] for _ in range(6)]
        for wi,parents in enumerate(assignments):
            for pi in parents:
                for pos in rows[pi]['positions']:scores[min(range(6),key=lambda i:len(scores[i]))].append(dict(parent_index=pi,position=pos,worker=wi))
        arms=['exact','baseline','wt_z','oracle_r32']+[f'student_{i}' for i in range(len(checkpoints))]
        save(f'functional/{panel}/lock.json',dict(teacher_lock,rows=rows,gt=gt,seeds=seeds,assignments=assignments,score_assignments=scores,checkpoints=checkpoints,arms=arms,teachers=str(virtual.parent/'factor_student_pilot_v1_20261002')))
        run_pool([dict(label=f'G_{panel}_{i}',script='deep_validation_outputs.py',args=['--mode','decode','--panel',panel,'--index',str(i)]) for i in range(6)],f'G_{panel}')
        run_pool([dict(label=f'G_score_{panel}_{i}',script='deep_validation_outputs.py',args=['--mode','score','--panel',panel,'--index',str(i)]) for i in range(6)],f'G_score_{panel}',gpu=False)
        run_pool([dict(label=f'G_collect_{panel}',script='deep_validation_outputs.py',args=['--mode','collect','--panel',panel])],f'G_collect_{panel}',gpu=False)
    start=time.time();decisions={};save('controller_identity.json',dict(pid=os.getpid(),physical_root=str(root),allowed_hip_devices=list(range(6)),cuda_visible_devices_set=False,started=start))
    try:
        assert not (root/'lock.json').exists(),'use a new root rather than overwriting a run'
        teacher_root=base/'factor_student_pilot_v1_20261002';teacher=load(teacher_root/'teacher_lock.json');train=[r for r in teacher['rows'] if r['role']=='train'];val=[r for r in teacher['rows'] if r['role']=='validation'];seeds=[231301,231303]
        code={str(virtual/'code'/p.relative_to(root/'code')):digest(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ('.py','.md','.json')}
        lock=dict(schema='deep_validation_v2',teachers=str(virtual.parent/teacher_root.name),teacher_lock_sha256=digest(teacher_root/'teacher_lock.json'),teacher_manifest_sha256=digest(teacher_root/'teacher_manifest.json'),aa=teacher['aa'],checkpoints=[512,1024,2048,4096,8192],code_hashes=code,seeds=seeds,allowed_devices=list(range(6)),cuda_selector=False,protocol_sha256=digest(root/'code/docs/mini_deep_validation_v2.md'))
        save('lock.json',lock);single=[[3,36]];variants=[('small_bias',dict(size='small',content=False)),('large_bias',dict(size='large',content=False)),('small_content',dict(size='small',content=True)),('large_content',dict(size='large',content=True)),('dense',dict(size='small',output='dense',length=84))]
        free=[jobfile(base_job('free',{},s,.01,single,kind='free')) for s in seeds];arms={};a_jobs=list(free)
        for lr in [3e-4,1e-4,1e-3]:
            for name,arch in variants:
                jobs=[jobfile(base_job(name,arch,s,lr,single)) for s in seeds];arms[f'{name}_{lr}']=jobs;a_jobs+=jobs
        b_jobs=[];b_arms={}
        for mode in ['wt','site','full']:
            jobs=[jobfile(base_job('input_'+mode,dict(size='large',content=True,input_mode=mode),s,3e-4,single,phase='B')) for s in seeds];b_arms[mode]=jobs;b_jobs+=jobs
        run_pool([dict(label='preflight',script='run_deep_validation_v2.py',args=['--mode','preflight'])],'preflight')
        save('planned_jobs.json',dict(A=a_jobs,B=b_jobs,total_continuous_runs=len(a_jobs)+len(b_jobs)))
        run_pool([task(j) for j in a_jobs],'A');run_pool([task(j) for j in b_jobs],'B')
        decisions['free_gate']=fit_pass(free,.075);decisions['single_site']={name:dict(primary=fit_pass(jobs),secondary=fit_pass(jobs,.12),means=[train_result(j)['history'][-1]['mean_nmse'] for j in jobs]) for name,jobs in arms.items()};decisions['oracle_input']={name:dict(primary=fit_pass(jobs),means=[train_result(j)['history'][-1]['mean_nmse'] for j in jobs]) for name,jobs in b_arms.items()};save('decisions.json',decisions)
        eligible=[(name,jobs) for name,jobs in arms.items() if not name.startswith('dense') and fit_pass(jobs)]
        if not decisions['free_gate']:decisions['stop']='free_factor_optimization_ceiling_not_passed'
        elif not eligible:
            if not any(fit_pass(j) for j in [*arms.values(),*b_arms.values()]):
                run_pool([dict(label='H_blockwise',script='deep_validation_outputs.py',args=['--mode','blockwise'])],'H');decisions['stop']='all_single_site_neural_arms_failed_blockwise_diagnostic_complete'
            else:decisions['stop']='only_dense_or_oracle_input_fit_no_WT_factor_promotion'
        else:
            means={name:sum(train_result(j)['history'][-1]['mean_nmse'] for j in jobs)/2 for name,jobs in eligible};best=min(means.values());candidates=[x for x in eligible if means[x[0]]<=best+1e-6];name,jobs=min(candidates,key=lambda x:(train_result(x[1][0])['parameters'],abs(x[1][0]['lr']-3e-4),x[0]));arch=jobs[0]['architecture'];lr=jobs[0]['lr'];decisions['selected_A']=name;selected=jobs;panel_parents=[3]
            c=evaluate(jobs,[[3,83]],'C');decisions['C']=dict(passed=transfer_pass(c),results=c)
            if transfer_pass(c):
                sites=[[r['index'],r['positions'][0]] for r in train[:3]];d_jobs=[jobfile(base_job(name,arch,s,lr,sites,phase='D')) for s in seeds];run_pool([task(j) for j in d_jobs],'D');selected=d_jobs;panel_parents=[r['index'] for r in train[:4]]
                seen=evaluate(d_jobs,[[r['index'],r['positions'][1]] for r in train[:3]],'D_newsite');unseen=evaluate(d_jobs,[[train[3]['index'],p] for p in train[3]['positions']],'D_newprotein');d_pass=fit_pass(d_jobs) and transfer_pass(seen) and transfer_pass(unseen);decisions['D']=dict(passed=d_pass,train_fit=fit_pass(d_jobs),seen=seen,unseen=unseen)
                if d_pass:
                    e_jobs=[jobfile(base_job(name,arch,s,lr,[[r['index'],p] for r in train for p in r['positions']],phase='E')) for s in seeds];run_pool([task(j) for j in e_jobs],'E');selected=e_jobs;panel_parents=[r['index'] for r in val]
                    validation=evaluate(e_jobs,[[r['index'],p] for r in val for p in r['positions']],'E_validation');e_pass=fit_pass(e_jobs) and transfer_pass(validation);decisions['E']=dict(passed=e_pass,train_fit=fit_pass(e_jobs),validation=validation)
                    previous=evaluate(e_jobs,[[r['index'],p] for r in val for p in r['positions']],'E_validation4096',step=4096)
                    plateau=all(abs(a['mean_nmse']-b['mean_nmse'])/max(a['mean_nmse'],.01)<=.05 for a,b in zip(previous,validation));decisions['E'].update(validation4096=previous,plateau_5percent=plateau)
                    if e_pass and plateau and all(r['mean_nmse']<=.15 for r in validation):
                        f_jobs=[]
                        for j in e_jobs:
                            for functional in [False,True]:
                                f_jobs.append(jobfile(dict(id=f'F_{functional}_{j["seed"]}',phase='F',checkpoint=checkpoint(j),architecture=arch,train_sites=j['train_sites'],seed=j['seed'],lr=lr,functional=functional)))
                        run_pool([dict(label=j['id'],script='deep_validation_outputs.py',args=['--mode','refine','--job',j['id']]) for j in f_jobs],'F');decisions['F']=dict(executed=True,jobs=f_jobs)
                    else:decisions['F']=dict(executed=False,reason='E fit/transfer, <=0.15 validation and plateau conditions not all satisfied')
                else:decisions['stop']='D_cross_site_or_protein_gate_failed'
            else:decisions['stop']='C_same_protein_new_site_gate_failed'
            cps=[checkpoint(j) for j in selected]
            if decisions.get('F',{}).get('executed'):cps += [checkpoint(j) for j in decisions['F']['jobs']]
            save('selected.json',dict(checkpoints=cps,architecture=arch,lr=lr,source_A=name));save('decisions.json',decisions)
            assignments=[[] for _ in range(6)]
            for i,pi in enumerate(panel_parents):assignments[i%6].append(pi)
            prepare_panel('main',teacher['rows'],teacher['gt'],teacher['seeds'],assignments,cps,teacher)
            old=load(base/'spatial_response_rank_v1_20261002/lock.json');rows=copy.deepcopy(old['rows']);rows[0]['positions']=[91];prepare_panel('stress',rows,old['gt'],old['seeds'],[[0],[],[],[],[],[]],cps,old)
            run_pool([dict(label='G_timing',script='deep_validation_outputs.py',args=['--mode','timing'])],'G_timing')
        for phase in ['C','D','E','F','G','H']:
            decisions.setdefault(phase,dict(executed=any(root.glob(f'{phase}*_execution.json')),reason='see prerequisite gates and execution records'))
        save('decisions.json',decisions);save('execution.json',dict(complete=True,seconds=time.time()-start,decisions=decisions));save('status.json',dict(complete=True,active=[],phase='closed'))
    except Exception as error:
        save('execution.json',dict(complete=False,error=repr(error),seconds=time.time()-start,decisions=decisions));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();control_deep_validation(a.root)
