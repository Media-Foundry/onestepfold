"""Export closed stage-aligned trials, without bulk conditioning or coordinates."""
import argparse,hashlib,json,shutil
from pathlib import Path


def export_stage_recovery(root):
    controller=json.loads((root/'controller.json').read_text())
    recovery=None
    if not controller['complete']:
        recovery=json.loads((root/'execution_recovery.json').read_text())
        assert controller['phase']=='failed' and recovery['complete'] and recovery['phase']=='closed'
        assert recovery['one_retry_only'] and recovery['source_provider']==str(root/'runtime_retry_v1')
        assert all(v['status']=='complete' and v['exit_code']==0 for v in recovery['jobs'].values())
    build=json.loads((root/'build_lock.json').read_text())
    for name,digest in build['code'].items():
        assert hashlib.sha256((root/'code'/name).read_bytes()).hexdigest()==digest,name
    dest=root/'export';dest.mkdir(exist_ok=False);files={}
    def copy(path,name):
        target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        digest=hashlib.sha256(path.read_bytes()).hexdigest();assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
        files[name]=digest
    for name in ('build_lock.json','protocol.md','controller.json','controller.log','preflight_tests.log','stage_manifest.json'):
        copy(root/name,name)
    for shard in range(4):copy(root/f'cache_{shard}.json',f'cache_{shard}.json')
    for path in sorted(root.glob('*.log')):
        if path.name not in files:copy(path,path.name)
    for path in sorted((root/'verification_code').glob('*.py')):
        copy(path,'verification_code/'+path.name)
    providers={}
    for cohort in ('n1','n15'):
        lock=json.loads((root/cohort/'training_lock.json').read_text())
        copy(root/cohort/'training_lock.json',f'{cohort}/training_lock.json')
        for arm in lock['arms']:
            for seed in lock['seeds']:
                relative=Path(cohort)/'runs'/arm/str(seed);folder=root/relative
                if recovery and (cohort,arm,seed)==('n15','final',272003):
                    folder=root/'runtime_retry_v1/runs/final/272003'
                    assert (root/cohort/'training_lock.json').read_bytes()==(root/'runtime_retry_v1/training_lock.json').read_bytes()
                providers[str(relative)]=str(folder)
                assert json.loads((folder/'report.json').read_text())['complete']
                assert json.loads((folder/'tensor_verification.json').read_text())['complete']
                for name in ('report.json','history.jsonl','score_complete.json','tensor_verification.json'):
                    copy(folder/name,str(relative/name))
                for step in lock['checkpoints']:
                    for name in (f'evaluation_{step}.json',f'summary_{step}.json',f'scores_{step}.json.gz'):
                        copy(folder/name,str(relative/name))
    accounting=None
    if recovery:
        for name in ('runtime_recovery_lock.json','runtime_recovery_protocol.md','runtime_recovery_stop.json',
                     'controller_before_recovery.json','execution_recovery.json','runtime_retry_launch.json'):
            copy(root/name,name)
        for path in sorted(root.glob('runtime*protocol.md')):
            if path.name not in files:copy(path,path.name)
        for path in sorted(root.glob('runtime*.json')):
            if path.name not in files:copy(path,path.name)
        for path in sorted((root/'runtime_replay_v1').rglob('*')):
            if path.is_file() and path.suffix in ('.json','.jsonl','.log'):
                copy(path,str(path.relative_to(root)))
        for name in ('training_lock.json','python_stack.log'):
            copy(root/'runtime_retry_v1'/name,'runtime_retry_v1/'+name)
        failed=root/'n15/runs/final/272003'
        for path in sorted(failed.iterdir()):
            if path.is_file() and (path.suffix in ('.json','.jsonl','.log','.gz')):
                copy(path,'failed_attempt/n15_final_272003/'+path.name)
        rows=(failed/'history.jsonl').read_text().splitlines()
        replay=json.loads((root/'runtime_replay_v1/result.json').read_text())
        initial=json.loads((failed/'evaluation_0.json').read_text())
        assert len(rows)==1420 and replay['counts']['updates']==1421
        assert replay['complete'] and replay['exact_updates']==1420 and replay['next_update_completed']
        accounting=dict(recorded_discarded_updates=len(rows),diagnostic_updates=1421,
                        unobserved_partial_next_update=True,unobserved_additional_update_upper_bound=1,
                        failed_attempt_s1=2*len(initial['predictions']),diagnostic_training_forwards=2842,
                        no_update_probe_forwards=2,no_update_probe_backwards=2)
        assert accounting['failed_attempt_s1']==1824
    (dest/'manifest.json').write_text(json.dumps(dict(source=str(root),files=files,
        source_provider_map=providers,operational_recovery=recovery is not None,
        operational_extra_accounting=accounting,source_snapshot_verified=len(build['code']),
        scientific_experiment_complete=True),indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(files=len(files),bytes=sum((dest/n).stat().st_size for n in files))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    export_stage_recovery(p.parse_args().root)
