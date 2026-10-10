"""Install a separately frozen, no-update audit using the closed Mini snapshot."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

parent=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding')
previous=parent/'stage_fullbatch_v1_20261010'
root=parent/'reference_anchor_audit_v1_20261010'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(previous/'training_lock.json')=='ed09b10002eaa7d04a4f2ea5843bf33657188a64cfd04836934aa47679993eed'
assert json.loads((previous/'verification_recovery/controller.json').read_text())['complete']
source=json.loads((previous/'training_lock.json').read_text())
root.mkdir(exist_ok=False);(root/'code').mkdir()
for name,digest in source['code'].items():
    p=previous/'code'/name;assert sha(p)==digest,name
    d=root/'code'/name;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
overlay=[]
with tarfile.open('/tmp/reference_anchor_audit_c12a2681.tar.gz') as archive:
    for m in archive:
        assert m.isfile() and '..' not in Path(m.name).parts and not Path(m.name).is_absolute()
        path=root/'code'/m.name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(archive.extractfile(m).read());overlay.append(m.name)
shutil.copy2(root/'code/docs/mini_reference_anchor_audit_v1.md',root/'protocol.md')
files=sorted(set(source['code'])|set(overlay))
cp=previous/'runs/adamw/272001/checkpoints/128.pt'
ev=json.loads((previous/'runs/adamw/272001/evaluation_128.json').read_text());assert sha(cp)==ev['sha256']
lock=dict(schema='mini_reference_anchor_audit_v1',created_unix=time.time(),source_commit='c12a2681325a697f504d3244c389f32d2aee6ed7',
    fullbatch_root='/data/user/shuang886/Folding/'+previous.name,fullbatch_lock_sha256=sha(previous/'training_lock.json'),
    seeds=[272001,272003],code={n:sha(root/'code'/n) for n in files},overlay=overlay,
    protocol_sha256=sha(root/'protocol.md'),functional_checkpoint='/data/user/shuang886/Folding/'+previous.name+'/runs/adamw/272001/checkpoints/128.pt',
    functional_checkpoint_sha256=sha(cp),parameter_updates=0,reference_recycles=24,new_target_recycles=0,new_esm_msa=False)
(root/'audit_lock.json').write_text(json.dumps(lock,indent=2,sort_keys=True)+'\n')
with (root/'controller.log').open('x') as output:
    process=subprocess.Popen(['python3','-u',str(root/'code/scripts/control_reference_anchor_audit.py'),'--root',str(root)],
        env=dict(os.environ,HIP_VISIBLE_DEVICES='4'),stdout=output,stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,start_new_session=True)
launch=dict(pid=process.pid,started_unix=time.time(),lock_sha256=sha(root/'audit_lock.json'))
(root/'launch.json').write_text(json.dumps(launch,indent=2)+'\n');print(json.dumps(launch))
