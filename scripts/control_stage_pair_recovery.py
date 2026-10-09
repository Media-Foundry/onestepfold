"""Bounded preparation and two predeclared four-worker training cohorts."""
import argparse,hashlib,json,os,signal,subprocess,time
from pathlib import Path


def control_stage_recovery(root):
    begin=time.monotonic();virtual=Path('/data/user/shuang886/Folding')/root.name
    lock=json.loads((root/'build_lock.json').read_text());digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name,value in lock['code'].items():assert digest(root/'code'/name)==value,name
    assert digest(root/'protocol.md')==lock['protocol_sha256']
    prefix=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
            '-b',str(root.parent)+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u']
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             LAYERNORM_TYPE='torch',FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
             PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
             PYTHONPATH=str(virtual/'code/src')+':'+str(virtual/'code/scripts'))
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    jobs={};state=dict(complete=False,phase='preflight',jobs={})
    def save():
        state['seconds']=time.monotonic()-begin
        tmp=root/'controller.tmp';tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(root/'controller.json')
    def launch(key,script,args,hip):
        log=(root/f'{key}.log').open('x')
        p=subprocess.Popen(prefix+[str(virtual/'code/scripts'/script),*args],
            env=dict(env,HIP_VISIBLE_DEVICES=str(hip)),stdin=subprocess.DEVNULL,
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        jobs[key]=(p,log);state['jobs'][key]=dict(pid=p.pid,hip=hip,status='running');save()
    def poll():
        for key,(p,_) in list(jobs.items()):
            code=p.poll()
            if code is not None:
                state['jobs'][key].update(status='complete' if code==0 else 'failed',exit_code=code)
                if code:raise RuntimeError(f'{key} exited {code}')
        save()
    try:
        with (root/'preflight_tests.log').open('x') as out:
            subprocess.run(prefix+['-m','pytest','-q',str(virtual/'code/tests/test_stage_pair_recovery.py'),
                                  str(virtual/'code/tests/test_pair_recovery.py'),str(virtual/'code/tests/test_response_moments.py')],
                           env=dict(env,HIP_VISIBLE_DEVICES='4'),stdout=out,stderr=subprocess.STDOUT,check=True)
        state['phase']='native_cache'
        for shard in range(4):launch(f'cache_{shard}','build_stage_pair_cache.py',['--root',str(virtual),'--shard',str(shard)],shard)
        cache_start=time.monotonic()
        while not all(p.poll()==0 for p,_ in jobs.values()):
            poll()
            if time.monotonic()-cache_start>6*3600:raise TimeoutError('cache six-hour cap')
            time.sleep(5)
        poll();parts=[json.loads((root/f'cache_{i}.json').read_text()) for i in range(4)]
        assert all(x['complete'] for x in parts)
        rows=[r for x in parts for r in x['records']]
        assert len(rows)==len({r['label'] for r in rows})==912
        assert sum(x['teacher_candidates'] for x in parts)==513
        assert sum(x['counts']['recycle'] for x in parts)==2964 and sum(x['counts']['s1'] for x in parts)==1824
        assert all(x['initial_hashes']==parts[0]['initial_hashes'] for x in parts)
        manifest=dict(records=rows,initial_hashes=parts[0]['initial_hashes'],parameters=parts[0]['parameters'],
                      shard_hashes={str(i):digest(root/f'cache_{i}.json') for i in range(4)})
        (root/'stage_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
        # Both memberships/budgets were fixed before cache extraction; no quality gate.
        all_sites=sorted({r['site'] for r in rows},key=lambda k:(int(k.split('_')[0][1:]),int(k.split('_')[1][1:])))
        configs=[(arm,seed) for seed in lock['seeds'] for arm in lock['arms']]
        for cohort in lock['cohorts']:
            path=root/cohort;path.mkdir();(path/'code').symlink_to('../code');(path/'protocol.md').symlink_to('../protocol.md')
            train=['p3_s37'] if cohort=='n1' else lock['train_sites']
            cfg=dict(lock,cohort=cohort,train_sites=train,eval_sites=['p3_s37'] if cohort=='n1' else all_sites,
                     checkpoints=[0,304,1216,4104,8208] if cohort=='n1' else [0,4104,8208],
                     exposures=864 if cohort=='n1' else 32,stage_root=str(virtual),
                     stage_manifest_sha256=digest(root/'stage_manifest.json'),initial_hashes=parts[0]['initial_hashes'])
            (path/'training_lock.json').write_text(json.dumps(cfg,indent=2,sort_keys=True)+'\n')
            state['phase']=cohort;phase_start=time.monotonic()
            for hip,(arm,seed) in enumerate(configs):
                launch(f'{cohort}_train_{arm}_{seed}','run_stage_pair_recovery.py',
                       ['--root',str(virtual/cohort),'--arm',arm,'--seed',str(seed)],hip)
            while True:
                poll()
                for arm,seed in configs:
                    key=f'{cohort}_score_{arm}_{seed}'
                    if key in jobs or state['jobs'][f'{cohort}_train_{arm}_{seed}']['status']!='complete':continue
                    launch(key,'score_stage_pair_recovery.py',['--root',str(virtual/cohort),'--arm',arm,'--seed',str(seed)],4)
                needed=[f'{cohort}_{kind}_{arm}_{seed}' for arm,seed in configs for kind in ('train','score')]
                if all(k in jobs and jobs[k][0].poll()==0 for k in needed):break
                if time.monotonic()-phase_start>6*3600:raise TimeoutError(f'{cohort} fixed six-hour cap')
                time.sleep(5)
            poll()
        state.update(complete=True,phase='closed')
    except BaseException as error:
        state.update(phase='failed',error=repr(error))
        for p,_ in jobs.values():
            if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
        raise
    finally:
        for _,out in jobs.values():out.close()
        save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    control_stage_recovery(p.parse_args().root)
