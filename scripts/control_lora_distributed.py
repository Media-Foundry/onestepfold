"""Fixed4104 handoff: two DDP pairs, two evaluation GPUs, original terminal audit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def distributed_controller(root):
    base=root.parent;source=base/'recycle_lora_v1d_20261008'
    virtual=Path('/data/user/shuang886/Folding');vr=virtual/root.name;vs=virtual/source.name
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=json.loads((root/'code_manifest.json').read_text())
    for path,digest in manifest.items():assert sha(root/'code'/path)==digest
    bench=json.loads((root/'benchmark'/'benchmark.json').read_text());assert bench['complete']
    for hip in (4,5):
        assert json.loads((root/f'device_{hip}'/'device_replay.json').read_text())['bitwise']
    parallel=sum(r['seconds'] for r in bench['timing'] if r['mode']=='parallel')
    serial=sum(r['seconds'] for r in bench['timing'] if r['mode']=='serial')
    assert serial/parallel>1.1,'no worthwhile measured paired throughput gain'
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',
             FASTGLYCAN_AUTHORIZED_HIP_0_5='1',PROTENIX_ROOT_DIR=str(virtual/'protenix_stage0_pkg/v1_1/runtime'),
             PYTHONPATH=str(vr/'code/src')+':'+str(vr/'code/scripts'))
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    prefix=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot','-b',str(base)+':'+str(virtual),
            '/home/pc/anaconda3/envs/fold/bin/python','-u']
    state=dict(complete=False,phase='waiting_fixed4104',benchmark_speedup=serial/parallel,jobs={},handoffs={})
    started=time.monotonic();jobs={}
    def save():
        state['seconds']=time.monotonic()-started
        p=root/'controller.tmp';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'controller.json')
    def launch(name,cmd,hips):
        log=(root/(name+'.log')).open('w')
        p=subprocess.Popen(prefix+cmd,env=dict(env,HIP_VISIBLE_DEVICES=hips),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        jobs[name]=(p,log,time.monotonic());state['jobs'][name]=dict(pid=p.pid,status='running',hip=hips);save()
    def wait_jobs(names,limit):
        while any(state['jobs'][n]['status']=='running' for n in names):
            for n in names:
                if state['jobs'][n]['status']!='running':continue
                p,log,t=jobs[n];code=p.poll()
                if code is None and time.monotonic()-t>limit:
                    os.killpg(p.pid,signal.SIGTERM);code=p.wait(timeout=30)
                if code is not None:
                    log.close();state['jobs'][n].update(status='complete' if code==0 else 'failed',exit_code=code);save()
                    if code:raise RuntimeError(f'{n} failed: {code}')
            time.sleep(5)
    save()
    # Handoff each seed immediately after its fixed checkpoint; do not idle the
    # faster seed while waiting for the slower one. Stop original controller once.
    old=json.loads((source/'controller.json').read_text())
    pending={272001,272003}
    old_controller_stopped=False
    while pending:
        for seed in list(pending):
            folder=source/'runs'/str(seed);cp=folder/'checkpoints/4104.pt';ev=folder/'evaluation_4104.json'
            if not(cp.exists() and ev.exists() and (folder/'exposure_4104.json').exists()):continue
            e=json.loads(ev.read_text());assert e['sha256']==sha(cp)
            for row in e['predictions']:assert sha(folder/row['path'])==row['sha256']
            pid=old['jobs'][f'train_{seed}']['pid'];os.killpg(pid,signal.SIGSTOP)
            rows=[json.loads(s) for s in (folder/'history.jsonl').read_text().splitlines() if s.strip()]
            state['handoffs'][str(seed)]=dict(source_checkpoint_sha256=sha(cp),resume_step=4104,
                 observed_old_last_step=rows[-1]['step'],discarded_post_checkpoint_updates=max(0,rows[-1]['step']-4104),old_pgid=pid)
            if not old_controller_stopped:
                lines=subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines()
                matches=[int(line.strip().split(None,1)[0]) for line in lines if 'control_recycle_lora.py --root '+str(source) in line and 'python' in line]
                assert len(matches)==1,matches
                os.kill(matches[0],signal.SIGTERM);old_controller_stopped=True
            os.killpg(pid,signal.SIGTERM);os.killpg(pid,signal.SIGCONT)
            (source/'distributed_handoff.json').write_text(json.dumps(state['handoffs'],indent=2)+'\n')
            hips=[0,2] if seed==272001 else [1,3]
            launch(f'train_{seed}',['-m','torch.distributed.run','--standalone','--nproc_per_node=2',str(vr/'code/scripts/run_lora_distributed.py'),
                 '--source',str(vs),'--output',str(vr/'runs'/str(seed)),'--checkpoint',str(vs/'runs'/str(seed)/'checkpoints/4104.pt'),
                 '--seed',str(seed),'--devices',*map(str,hips),'--mode','train'],','.join(map(str,hips)))
            pending.remove(seed);save()
        if time.monotonic()-started>10800:raise TimeoutError('checkpoint wait exceeded3h')
        if pending:time.sleep(3)
    state['phase']='paired_training';save()
    # Training/evaluation overlap: each completed seed goes to both spare GPUs.
    audit=root/'audit';audit.mkdir(exist_ok=False)
    (audit/'lora_lock.json').symlink_to(source/'lora_lock.json')
    (audit/'audit_code').symlink_to(source/'audit_code')
    (audit/'protocol.md').symlink_to(source/'protocol.md')
    pending_evaluation={272001,272003}
    for _ in range(2):
        while True:
            ready=[s for s in sorted(pending_evaluation) if jobs[f'train_{s}'][0].poll() is not None]
            if ready:
                seed=ready[0];pending_evaluation.remove(seed);break
            expired=[f'train_{s}' for s in pending_evaluation if time.monotonic()-jobs[f'train_{s}'][2]>21600]
            if expired:wait_jobs(expired,21600)
            time.sleep(5)
        wait_jobs([f'train_{seed}'],21600)
        folder=audit/'runs'/str(seed);folder.mkdir(parents=True);(folder/'coordinates').mkdir();(folder/'checkpoints').mkdir()
        oldfolder=source/'runs'/str(seed)
        for step in (0,4104):
            for name in (f'evaluation_{step}.json',): (folder/name).symlink_to(oldfolder/name)
            (folder/'checkpoints'/f'{step}.pt').symlink_to(oldfolder/'checkpoints'/f'{step}.pt')
            for row in json.loads((oldfolder/f'evaluation_{step}.json').read_text())['predictions']:
                (folder/row['path']).symlink_to(oldfolder/row['path'])
        cp=root/'runs'/str(seed)/'checkpoints/8208.pt';(folder/'checkpoints/8208.pt').symlink_to(cp)
        (folder/'history.jsonl').symlink_to(root/'runs'/str(seed)/'history.jsonl')
        state['phase']='training_and_evaluation';save()
        names=[]
        for shard,hip in enumerate((4,5)):
            name=f'eval_{seed}_{shard}';names.append(name)
            launch(name,[str(vr/'code/scripts/evaluate_lora_shard.py'),'--source',str(vs),'--output',str(vr/'audit'),
                         '--checkpoint',str(vr/'runs'/str(seed)/'checkpoints/8208.pt'),'--seed',str(seed),'--shard',str(shard)],str(hip))
        wait_jobs(names,3600)
        shards=[json.loads((folder/f'shard_{i}.json').read_text()) for i in (0,1)]
        rows=sum([r['predictions'] for r in shards],[]);assert len(rows)==len({r['label'] for r in rows})==912
        evaluation=dict(step=8208,predictions=rows,checkpoint='checkpoints/8208.pt',sha256=sha(cp),seconds=max(r['seconds'] for r in shards))
        (folder/'evaluation_8208.json').write_text(json.dumps(evaluation,indent=2)+'\n')
        history=[json.loads(s) for s in (folder/'history.jsonl').read_text().splitlines()]
        assert [r['step'] for r in history]==list(range(1,8209))
        exposures={}
        for r in history:
            for aa in r['aa']:exposures[(r['site'],aa)]=exposures.get((r['site'],aa),0)+1
        assert len(exposures)==513 and all(n==32 for n in exposures.values())
        report=dict(complete=True,seed=seed,counts=dict(updates=8208,input_embedder=0,c4=0),
              evaluations=[{k:v for k,v in json.loads((folder/f'evaluation_{step}.json').read_text()).items() if k!='predictions'} for step in (0,4104,8208)],
              history_sha256=sha(folder/'history.jsonl'),execution='serial4104_then_pairedDDP4104',handoff=state['handoffs'][str(seed)])
        (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        launch(f'score_{seed}',[str(vr/'code/scripts/audit_recycle_lora.py'),'--root',str(vr/'audit'),'--seed',str(seed),'--mode','score'],'4')
    wait_jobs([f'score_{s}' for s in (272001,272003)],7200)
    state['phase']='serial_replay_timing';save()
    for seed in (272001,272003):
        name=f'replay_{seed}'
        launch(name,[str(vr/'code/scripts/audit_recycle_lora.py'),'--root',str(vr/'audit'),'--seed',str(seed),'--mode','replay'],'0')
        wait_jobs([name],1800)
    state.update(complete=True,phase='closed');save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    try:distributed_controller(a.root)
    except BaseException as e:
        (a.root/'controller_error.json').write_text(json.dumps(dict(error=repr(e)))+'\n')
        # If handoff failed before termination, do not leave an old worker stopped.
        state=json.loads((a.root/'controller.json').read_text()) if (a.root/'controller.json').exists() else {}
        for h in state.get('handoffs',{}).values():
            try:os.killpg(h['old_pgid'],signal.SIGCONT)
            except ProcessLookupError:pass
        raise
