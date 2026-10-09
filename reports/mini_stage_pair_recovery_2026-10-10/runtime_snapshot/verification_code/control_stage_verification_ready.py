"""Verify completed runs without blocking ready work behind an unfinished run."""
import json, os, pathlib, subprocess, time

root=pathlib.Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/stage_pair_recovery_v1_20261010')
virtual=pathlib.Path('/data/user/shuang886/Folding')/root.name
prefix=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
        '-b',str(root.parent)+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u']
env=dict(os.environ,HIP_VISIBLE_DEVICES='4',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
         LAYERNORM_TYPE='torch',FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
         PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
         PYTHONPATH=str(virtual/'code/src')+':'+str(virtual/'code/scripts'))
assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
start=time.monotonic()
while True:
    pending=[];ready=[]
    for cohort in ('n1','n15'):
        for arm in ('final','hint'):
            for seed in (272001,272003):
                folder=root/cohort/'runs'/arm/str(seed)
                verified=folder/'tensor_verification.json'
                if verified.exists() and json.loads(verified.read_text())['complete']:continue
                pending.append((cohort,arm,seed))
                report=folder/'report.json'
                if report.exists() and json.loads(report.read_text())['complete']:ready.append((cohort,arm,seed))
    if not pending:break
    if not ready:
        state=json.loads((root/'controller.json').read_text())
        assert state['phase']!='failed',state
        assert time.monotonic()-start<6*3600,'read-only audit wait cap'
        time.sleep(5);continue
    cohort,arm,seed=ready[0];key=f'verify_{cohort}_{arm}_{seed}'
    print('VERIFY_START',key,flush=True)
    with (root/f'{key}.log').open('x') as out:
        subprocess.run(prefix+[str(virtual/'verification_code/verify_stage_pair_recovery.py'),
            '--root',str(virtual/cohort),'--arm',arm,'--seed',str(seed)],
            env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=3600)
    print('VERIFY_COMPLETE',key,flush=True)
print('ALL_VERIFIED',time.monotonic()-start,flush=True)
