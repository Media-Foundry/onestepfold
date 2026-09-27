import json,hashlib,shutil
from pathlib import Path
parent=Path('/data/user/shuang886/Folding/esmc_pretrained_gt_hpc3_v1_20260927')
r=Path('/data/user/shuang886/Folding/esmc_pretrained_gt_continuation_v1_20260927')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (r/'lock.json').exists()
shutil.copytree(parent/'code_v1',r/'code_v1')
for p in (r/'incoming').glob('*.py'):shutil.copy2(p,r/'code_v1/scripts'/p.name)
for name in ['data','data_manifest.json','data_acceptance.json','runtime_contract.json','native.pt','bridge.pt']:(r/name).symlink_to(parent/name)
lock=json.loads((parent/'lock.json').read_text())
lock.update(parent_root=str(parent),parent_lock_sha256=sha(parent/'lock.json'),max_updates=16384,evaluation_steps=[4096,8192,16384],resume_sha256={},resume_predictions={},parent_score_sha256={})
for size in [2048,8192]:
 f=parent/('train_%d'%size);qa=json.loads((f/'checkpoint_audit_4096.json').read_text());assert qa['complete'] and all(x['exact'] for x in qa['predictions'])
 h=sha(f/'step_4096.pt');assert h==qa['checkpoint_sha256']
 lock['resume_sha256'][str(size)]=h
 lock['parent_score_sha256'][str(size)]=sha(parent/'scores'/('%d_4096.json'%size))
 rows=json.loads((f/'evaluation_4096.json').read_text())['predictions'];d={}
 for row in rows:d.setdefault(row['group_id'],{})[str(row['noise'])]=row['sha256']
 lock['resume_predictions'][str(size)]=d
source=json.loads((r/'code_v1/source_manifest.json').read_text())
for p in (r/'incoming').glob('*.py'):source['files']['scripts/'+p.name]=sha(r/'code_v1/scripts'/p.name)
(r/'code_v1/source_manifest.json').write_text(json.dumps(source,indent=2)+'\n')
lock['common_files']={n:sha(r/n) for n in lock['common_files']}
(r/'lock.json').write_text(json.dumps(lock,indent=2)+'\n')
print('Locked',r,sha(r/'lock.json'))
