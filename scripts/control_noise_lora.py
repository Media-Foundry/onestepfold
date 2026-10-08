"""Four fresh runs; two training pairs and independent two-shard evaluation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def control_noise_lora(root):
    base = root.parent
    virtual = Path('/data/user/shuang886/Folding')/root.name
    lock = json.loads((root/'noise_lock.json').read_text())
    source = base/Path(lock['source']).name
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    for path, digest in lock['code'].items():
        assert sha(root/'code'/path) == digest, path
    assert sha(root/'protocol.md') == lock['protocol_sha256']
    assert sha(source/'lora_lock.json') == lock['source_lock_sha256']
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
        LAYERNORM_TYPE='torch', FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
        PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
        PYTHONPATH=str(virtual/'code/src')+':'+str(virtual/'code/scripts'))
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    prefix = ['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
              '-b',str(base)+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u']
    state = dict(complete=False,phase='preflight',jobs={},noise_lock_sha256=sha(root/'noise_lock.json'))
    jobs = {}
    started = time.monotonic()

    def save():
        state['seconds'] = time.monotonic()-started
        tmp = root/'controller.tmp'
        tmp.write_text(json.dumps(state,indent=2)+'\n')
        tmp.replace(root/'controller.json')

    def launch(name, command, hips):
        log = (root/(name+'.log')).open('w')
        p = subprocess.Popen(prefix+command,env=dict(env,HIP_VISIBLE_DEVICES=hips),
                             stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        jobs[name] = (p,log,time.monotonic())
        state['jobs'][name] = dict(pid=p.pid,status='running',hip=hips)
        save()

    def poll():
        for name,(p,log,begin) in jobs.items():
            if state['jobs'][name]['status'] != 'running':
                continue
            code = p.poll()
            if code is None:
                if time.monotonic()-begin > 28800:
                    raise TimeoutError(name+' exceeded8h; inspect owned worker')
                continue
            log.close()
            state['jobs'][name].update(status='complete' if code==0 else 'failed',exit_code=code)
            save()
            if code:
                raise RuntimeError(f'{name} failed: {code}')

    save()
    # Reuse ONLY the audited zero-state evaluations, not historical training.
    for arm in lock['arms']:
        ar = root/arm
        ar.mkdir(exist_ok=True)
        for name in ('lora_lock.json','audit_code','protocol.md'):
            (ar/name).symlink_to(source/name)
        for seed in lock['seeds']:
            folder = ar/'runs'/str(seed)
            (folder/'coordinates').mkdir(parents=True)
            (folder/'checkpoints').mkdir()
            original = source/'runs'/str(seed)
            assert sha(original/'checkpoints/0.pt') == lock['initial_checkpoints'][str(seed)]
            (folder/'checkpoints/0.pt').symlink_to(original/'checkpoints/0.pt')
            (folder/'evaluation_0.json').symlink_to(original/'evaluation_0.json')
            ev = json.loads((original/'evaluation_0.json').read_text())
            assert len(ev['predictions']) == 912 and ev['sha256'] == lock['initial_checkpoints'][str(seed)]
            for row in ev['predictions']:
                assert sha(original/row['path']) == row['sha256']
                (folder/row['path']).symlink_to(original/row['path'])
    for seed in lock['seeds']:
        name = f'preflight_{seed}'
        launch(name,['-m','torch.distributed.run','--standalone','--nproc_per_node=2',
            str(virtual/'code/scripts/run_noise_lora.py'),'--root',str(virtual),'--arm','dual',
            '--seed',str(seed),'--devices','0','2','--mode','preflight'],'0,2')
        while state['jobs'][name]['status'] == 'running':
            time.sleep(3)
            poll()
        assert json.loads((root/f'preflight_{seed}.json').read_text())['complete']
    # Counterbalance arm against device pair and wave. Same seed runs paired.
    queues = [[('single',272001),('dual',272003)], [('dual',272001),('single',272003)]]
    hips = [(0,2),(1,3)]
    active = [None,None]
    active_eval = None
    eval_done = set()
    scored = set()
    all_runs = [(arm,seed) for arm in lock['arms'] for seed in lock['seeds']]
    state['phase'] = 'training_and_evaluation'
    save()
    while len(scored) < 4 or any(state['jobs'][n]['status']=='running' for n in scored):
        poll()
        for pair in (0,1):
            if active[pair] and state['jobs'][active[pair]]['status']=='complete':
                active[pair] = None
            if active[pair] is None and queues[pair]:
                arm,seed = queues[pair].pop(0)
                name = f'train_{arm}_{seed}'
                launch(name,['-m','torch.distributed.run','--standalone','--nproc_per_node=2',
                    str(virtual/'code/scripts/run_noise_lora.py'),'--root',str(virtual),'--arm',arm,
                    '--seed',str(seed),'--devices',*map(str,hips[pair]),'--mode','train'],','.join(map(str,hips[pair])))
                active[pair] = name
        if active_eval is not None:
            arm,seed,step,names = active_eval
            if all(state['jobs'][n]['status']=='complete' for n in names):
                folder = root/arm/'runs'/str(seed)
                shards = [json.loads((folder/f'shard_{step}_{i}.json').read_text()) for i in (0,1)]
                cp = folder/'checkpoints'/f'{step}.pt'
                assert all(s['complete'] and s['checkpoint_sha256']==sha(cp) for s in shards)
                rows = sum([s['predictions'] for s in shards],[])
                assert len(rows)==len({r['label'] for r in rows})==912
                for row in rows:
                    assert sha(folder/row['path']) == row['sha256']
                ev = dict(step=step,predictions=rows,checkpoint=f'checkpoints/{step}.pt',sha256=sha(cp))
                (folder/f'evaluation_{step}.json').write_text(json.dumps(ev,indent=2)+'\n')
                eval_done.add((arm,seed,step))
                active_eval = None
        if active_eval is None:
            ready = [(arm,seed,step) for step in (4104,8208) for arm,seed in all_runs
                if (arm,seed,step) not in eval_done and (root/arm/'runs'/str(seed)/'checkpoints'/f'{step}.pt').exists()]
            if ready:
                arm,seed,step = ready[0]
                names = []
                for shard,hip in enumerate((4,5)):
                    name = f'eval_{arm}_{seed}_{step}_{shard}'
                    launch(name,[str(virtual/'code/scripts/evaluate_noise_lora.py'),'--root',str(virtual),
                        '--arm',arm,'--seed',str(seed),'--step',str(step),'--shard',str(shard)],str(hip))
                    names.append(name)
                active_eval = (arm,seed,step,names)
        for arm,seed in all_runs:
            name = f'score_{arm}_{seed}'
            if name not in scored and all((arm,seed,s) in eval_done for s in (4104,8208)) and (root/arm/'runs'/str(seed)/'training_complete.json').exists():
                launch(name,[str(virtual/'code/scripts/score_noise_lora.py'),'--root',str(virtual),
                             '--arm',arm,'--seed',str(seed)],'4')
                scored.add(name)
        time.sleep(3)
    state['phase'] = 'replay'
    save()
    for arm,seed in all_runs:
        name = f'replay_{arm}_{seed}'
        launch(name,[str(virtual/'code/scripts/audit_recycle_lora.py'),'--root',str(virtual/arm),
                     '--seed',str(seed),'--mode','replay'],'0')
        while state['jobs'][name]['status']=='running':
            time.sleep(3)
            poll()
    for seed in lock['seeds']:
        assert json.loads((root/f'paired_{seed}.json').read_text())['complete']
    state.update(complete=True,phase='closed',promoted=False)
    save()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    args = p.parse_args()
    try:
        control_noise_lora(args.root)
    except BaseException as error:
        (args.root/'controller_error.json').write_text(json.dumps(dict(error=repr(error)))+'\n')
        raise
