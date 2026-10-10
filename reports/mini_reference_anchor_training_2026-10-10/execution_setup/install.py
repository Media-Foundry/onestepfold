"""Freeze a new paired training trial; never modify the completed controls."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

parent=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding')
virtual=Path('/data/user/shuang886/Folding')
audit=parent/'reference_anchor_audit_v1_20261010'
previous=parent/'stage_fullbatch_v1_20261010'
root=parent/'reference_anchor_training_v1_20261010'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(audit/'audit_lock.json')=='4ce5a10e7c1d2f3fc62a5fc1e6eec56277cf6291a41765d80fcb5958698d6171'
assert sha(audit/'report.json')=='a7b11019df25e2a0362996f954bff0b7420b54235ccd86a10965cb669c07ac48'
assert json.loads((audit/'controller.json').read_text())['complete']
assert sha(previous/'training_lock.json')=='ed09b10002eaa7d04a4f2ea5843bf33657188a64cfd04836934aa47679993eed'
assert json.loads((previous/'verification_recovery/controller.json').read_text())['complete']
old=json.loads((previous/'training_lock.json').read_text())
audited=json.loads((audit/'audit_lock.json').read_text())
report=json.loads((audit/'report.json').read_text())
assert report['complete'] and report['parameter_updates']==0
root.mkdir(exist_ok=False);(root/'code').mkdir()
for name,digest in audited['code'].items():
    p=audit/'code'/name;assert sha(p)==digest,name
    q=root/'code'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
overlay=[]
with tarfile.open('/tmp/reference_anchor_training_c12a2681.tar.gz') as archive:
    for member in archive:
        assert member.isfile() and '..' not in Path(member.name).parts and not Path(member.name).is_absolute()
        q=root/'code'/member.name;q.parent.mkdir(parents=True,exist_ok=True)
        q.write_bytes(archive.extractfile(member).read());overlay.append(member.name)
shutil.copy2(root/'code/docs/mini_reference_anchor_training_v1.md',root/'protocol.md')
fields=['source','build_root','cache_manifest_sha256','stage_root','stage_manifest_sha256',
        'oracle_root','oracle_lock_sha256','site_scale_squared','train_sites','eval_sites','initial_hashes',
        'resident_tensor_byte_cap','torch_version','initial_objective']
lock={key:old[key] for key in fields}
refs={};controls={}
for seed in report['seeds']:
    p=audit/seed['vector_path'];assert sha(p)==seed['vector_sha256']
    key=str(seed['seed']);refs[key]=dict(path=str(virtual/audit.name/p.name),sha256=sha(p))
    assert seed['initial_sha256']==old['initial_hashes'][key]
    folder=previous/'runs/adamw'/key
    assert json.loads((folder/'report.json').read_text())['complete']
    assert json.loads((folder/'tensor_verification.json').read_text())['complete']
    controls[key]={}
    for name in ['report.json','tensor_verification.json','history.jsonl']+[
            n for step in (0,32,128) for n in (f'evaluation_{step}.json',f'summary_{step}.json',f'scores_{step}.json.gz')]:
        controls[key][name]=sha(folder/name)
    for step in (0,32,128):
        ev=json.loads((folder/f'evaluation_{step}.json').read_text())
        assert sha(folder/ev['checkpoint'])==ev['sha256']
        controls[key][ev['checkpoint']]=ev['sha256']
for rec in report['reference_records']:assert sha(audit/rec['path'])==rec['sha256']
files=sorted(set(audited['code'])|set(overlay))
lock.update(schema='mini_reference_anchor_training_v1',cohort='n15',arms=['anchor'],seeds=[272001,272003],
    gradient_budget=128,checkpoints=[0,32,128],objective='final',
    budget_unit='complete513-candidate gradient plus27-reference pullbacks',
    gradient_references=refs,reference_cache_root=str(virtual/audit.name),reference_records=report['reference_records'],
    audit_lock_sha256=sha(audit/'audit_lock.json'),audit_report_sha256=sha(audit/'report.json'),
    controls_root=str(virtual/previous.name),controls_lock_sha256=sha(previous/'training_lock.json'),matched_controls=controls,
    code={n:sha(root/'code'/n) for n in files},overlay=overlay,protocol_sha256=sha(root/'protocol.md'),
    created_unix=time.time(),source_commit='c12a2681325a697f504d3244c389f32d2aee6ed7',
    per_run_training_forwards=65664,per_run_training_backwards=65664,
    per_run_training_reference_forwards=3456,per_run_training_reference_backwards=3456,
    per_run_fixed_prediction_forwards=2736,per_run_evaluation_reference_forwards=144,
    per_run_isolation_forwards=6,per_run_isolation_reference_forwards=2,per_run_s1=7296,
    per_run_verification_forwards=2736,per_run_verification_reference_forwards=144,
    native_recycle_calls=0,new_esm_msa_preparation=False,promoted=False,independent_confirmation=False)
(root/'training_lock.json').write_text(json.dumps(lock,indent=2,sort_keys=True)+'\n')
with (root/'controller.log').open('x') as out:
    proc=subprocess.Popen(['python3','-u',str(root/'code/scripts/control_anchor_training.py'),'--root',str(root)],
        env=dict(os.environ,HIP_VISIBLE_DEVICES=''),stdout=out,stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,start_new_session=True)
launch=dict(pid=proc.pid,started_unix=time.time(),lock_sha256=sha(root/'training_lock.json'))
(root/'launch.json').write_text(json.dumps(launch,indent=2)+'\n');print(json.dumps(launch))
