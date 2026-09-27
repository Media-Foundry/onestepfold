from pathlib import Path
import json,hashlib,shutil
r=Path('/data/user/shuang886/Folding/c4_s1_attribution_v1_20260927');c=r/'code_precision_v2';shutil.copytree(r/'code_precision_v1',c)
for name in ('run_c4_s1_precision.py','score_c4_s1_attribution.py'):shutil.copy2(r/name,c/'scripts'/name)
(r/'precision_source_manifest_v2.json').write_text(json.dumps(dict(files={str(p.relative_to(c)):hashlib.sha256(p.read_bytes()).hexdigest() for p in c.rglob('*.py')}),indent=2))
l=json.loads((r/'precision_lock.json').read_text());l['audit_fix']='Allow enabled CUDA autocast with targetfloat32; require actual module inputs/outputsfloat32 and recordtargetdtype. v1 assertion was too strict; no successful v1 precision result.';(r/'precision_lock_v2.json').write_text(json.dumps(l,indent=2))
s=(r/'precision.sh').read_text().replace('code_precision_v1','code_precision_v2').replace('"$SLURM_ARRAY_TASK_ID"','"${SLURM_ARRAY_TASK_ID:-0}" ${PREFLIGHT_FLAG:-}');(r/'precision_v2.sh').write_text(s)
s=(r/'score.sh').read_text().replace('code_precision_v1','code_precision_v2');(r/'score_v2.sh').write_text(s)
