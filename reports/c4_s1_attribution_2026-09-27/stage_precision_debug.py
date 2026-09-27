from pathlib import Path
import shutil,json,hashlib
r=Path('/data/user/shuang886/Folding/c4_s1_attribution_v1_20260927');c=r/'code_precision_debug';shutil.copytree(r/'code_precision_v1',c)
p=c/'scripts/run_c4_s1_precision.py';s=p.read_text().replace("root/'precision_source_manifest.json'","root/'precision_debug_source_manifest.json'").replace("f'precision_{a.worker}'","f'precision_debug_{a.worker}'")
s=s.replace("assert all(not x['autocast_enabled'] for v in dtypes.values() for x in v)","write_json(folder/'dtype_debug.json',dict(config_dtype=runner.configs.dtype,trace=dtypes)); raise RuntimeError('intentional stop after dtype capture')")
p.write_text(s)
(r/'precision_debug_source_manifest.json').write_text(json.dumps(dict(files={str(p.relative_to(c)):hashlib.sha256(p.read_bytes()).hexdigest() for p in c.rglob('*.py')})))
p=r/'precision_debug.sh';p.write_text((r/'precision.sh').read_text().replace('code_precision_v1','code_precision_debug'))
