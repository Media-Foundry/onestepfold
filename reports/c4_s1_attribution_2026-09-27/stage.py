from pathlib import Path
import json,hashlib,shutil
r=Path('/data/user/shuang886/Folding/c4_s1_attribution_v1_20260927');old=Path('/data/user/shuang886/Folding/stage0_confirmation_v1_20260919')
assert not (r/'code_v1').exists();shutil.copytree(old/'code_v2',r/'code_v1')
shutil.copy2(r/'run_c4_s1_attribution.py',r/'code_v1/scripts/run_c4_s1_attribution.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
l=json.loads((r/'lock.json').read_text());files=['repeat/preparation.json','repeat/runtime_lock.json','repeat/execution_qa.json','control/repeat_manifest.jsonl.gz']
for i in range(16):files += [f'repeat/worker_{i}/{n}' for n in ('progress.json','scores.json')]
l['bound_old_files']={f:sha(old/f) for f in files};(r/'lock.json').write_text(json.dumps(l,indent=2)+'\n')
src=r/'code_v1';(r/'source_manifest.json').write_text(json.dumps(dict(files={str(p.relative_to(src)):sha(p) for p in src.rglob('*.py')}),indent=2)+'\n')
(r/'logs').mkdir()
