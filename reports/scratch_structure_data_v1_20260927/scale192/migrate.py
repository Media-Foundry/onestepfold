import os,signal,time,json,shutil,hashlib
from pathlib import Path
r=Path('/media/PM982/onestepfold/scratch_structure_data_v1_20260927')
assert not (r/'scale192').exists()
s=r/'scale192';s.mkdir()
launch=json.loads((r/'launch.json').read_text());controller=launch['controller_pid']
# Only terminate this pipeline's controller and its known preparation workers;
# leave the independent rsync child running.
def stop(pid,needle):
 p=Path(f'/proc/{pid}/cmdline')
 if p.exists():
  command=p.read_bytes().replace(b'\0',b' ').decode()
  assert str(r) in command and needle in command,(pid,command)
  os.kill(pid,signal.SIGTERM)
stop(controller,'run.py')
workers=[x['pid'] for x in launch['workers'] if x['kind']=='new']
for pid in workers:stop(pid,'prepare_scratch_structure_data.py')
for _ in range(50):
 live=[pid for pid in workers if Path(f'/proc/{pid}/cmdline').exists() and Path(f'/proc/{pid}/cmdline').read_bytes()]
 if not live:break
 time.sleep(.2)
assert not live,live
(s/'generation16').mkdir();(s/'incomplete').mkdir()
for pattern in ['worker_*.log','worker_*.json','progress_worker_*.json','exit.json']:
 for p in (r/'new').glob(pattern):p.rename(s/'generation16'/p.name)
complete=0;partial=[]
for p in (r/'new/examples').iterdir():
 if (p/'prepared.json').exists():complete+=1
 else:
  assert not p.is_symlink();partial.append(p.name);p.rename(s/'incomplete'/p.name)
shutil.copytree(r/'code_v1',r/'code_v2',ignore=shutil.ignore_patterns('__pycache__'))
p=r/'code_v2/scripts/prepare_scratch_structure_data.py'
code=p.read_text().replace('    torch.set_num_threads(1)','    torch.set_num_threads(1)\n    torch.set_num_interop_threads(1)')
p.write_text(code)
# Verifier keeps original data/label policy but checks 192-way ownership and v2 source.
p=r/'code_v2/scripts/accept_scratch_structure_data.py'
code=p.read_text().replace("range(16)","range(192)").replace("rows[i::16]","rows[i::192]").replace("code_v1","code_v2")
p.write_text(code)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source={'files':{str(p.relative_to(r/'code_v2')):sha(p) for p in (r/'code_v2').rglob('*.py')}}
(r/'code_v2/source_manifest.json').write_text(json.dumps(source,indent=2)+'\n')
record={'complete':True,'retained_completed':complete,'quarantined_partial':partial,'stopped_controller':controller,'stopped_workers':workers,'preserved_rsync_pid':launch['reuse_transfer_pid'],'source_manifest_sha256':sha(r/'code_v2/source_manifest.json')}
(s/'migration.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
