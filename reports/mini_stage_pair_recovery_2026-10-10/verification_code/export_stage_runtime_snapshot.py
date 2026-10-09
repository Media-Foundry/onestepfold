"""Point-in-time operational evidence; explicitly not a final science export."""
import hashlib,json,pathlib,sys,time
r=pathlib.Path(sys.argv[1]);dest=r/'runtime_snapshot_20261010_a';dest.mkdir()
files={}
def copy(p,name):
 data=p.read_bytes();out=dest/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
 files[name]=hashlib.sha256(data).hexdigest()
for name in ['controller.json','controller_before_recovery.json','execution_recovery.json','runtime_recovery_lock.json','runtime_recovery_stop.json','runtime_retry_launch.json','runtime_retry_prefix_check.json','runtime_recovery_protocol.md']:
 copy(r/name,name)
for p in sorted(r.glob('runtime*protocol.md')):
 if p.name not in files:copy(p,p.name)
for p in sorted(r.glob('*.log')):copy(p,'logs/'+p.name)
for p in sorted((r/'verification_code').glob('*.py')):copy(p,'verification_code/'+p.name)
for p in sorted((r/'runtime_replay_v1').glob('*')):
 if p.is_file() and p.suffix in ('.json','.jsonl','.log'):copy(p,'runtime_replay_v1/'+p.name)
for name in ['report.json','history.jsonl','evaluation_0.json','summary_0.json','scores_0.json.gz']:
 p=r/'n15/runs/final/272003'/name
 if p.exists():copy(p,'failed_attempt/'+name)
copy(r/'runtime_retry_v1/python_stack.log','retry_observer_stack.log')
copy(pathlib.Path(__file__),'export_snapshot.py')
completed=[]
for cohort in ('n1','n15'):
 for arm in ('final','hint'):
  for seed in (272001,272003):
   p=r/cohort/'runs'/arm/str(seed)
   if json.loads((p/'report.json').read_text())['complete']:
    names=['report.json','score_complete.json','tensor_verification.json']
    assert all(json.loads((p/n).read_text())['complete'] for n in names)
    completed.append(dict(cohort=cohort,arm=arm,seed=seed,hashes={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in names}))
assert len(completed)==7
history=r/'runtime_retry_v1/runs/final/272003/history.jsonl'
status=dict(observed_at=time.time(),scientific_experiment_complete=False,recovery_complete=False,
            original_completed_runs=completed,retry_recorded_updates=len(history.read_text().splitlines()),
            original_source=str(r),files=files)
(dest/'manifest.json').write_text(json.dumps(status,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(snapshot=str(dest),files=len(files),retry_recorded_updates=status['retry_recorded_updates'])))
