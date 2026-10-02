import json,hashlib
from pathlib import Path
base=Path('/home/husrcf/Code/onestepfold_runtime');r=base/'readout_endpoint_decode_v1_20261002';p=base/'response_readout_v1_20261002'
a=json.loads((p/'functional/closure/worker_0/p3_s37_scores.json').read_text());b=json.loads((r/'functional/endpoints/worker_0/p3_s37_scores.json').read_text());old={(x['arm'],x['aa'],x['noise']):x for x in a['outputs']};count=0
for x in b['outputs']:
 if x['arm'] not in ['exact','baseline','wt_z','oracle_r32']:continue
 assert x==old[x['arm'],x['aa'],x['noise']],(x['arm'],x['aa'],x['noise']);count+=1
oldrank={(x['arm'],x['noise'],x['reference'],x['includes_wt']):x for x in a['ranking']};rc=0
for x in b['ranking']:
 k=(x['arm'],x['noise'],x['reference'],x['includes_wt'])
 if k in oldrank:assert x==oldrank[k];rc+=1
lock=json.loads((r/'lock.json').read_text());source=Path('scripts/run_readout_endpoint_decode.py');h=hashlib.sha256(source.read_bytes()).hexdigest();assert h==lock['code_hashes']['/data/user/shuang886/Folding/readout_endpoint_decode_v1_20261002/code/scripts/run_readout_endpoint_decode.py']
assert Path('scripts/control_readout_endpoint_decode.py').read_bytes()==(r/'launch_endpoint_audit.py').read_bytes()
manifest=json.loads((r/'coordinate_manifest.json').read_text())
for x in manifest:
 f=r/Path(x['path']).relative_to('/data/user/shuang886/Folding/readout_endpoint_decode_v1_20261002');assert hashlib.sha256(f.read_bytes()).hexdigest()==x['sha256']
record=dict(complete=True,unchanged_reference_score_rows=count,unchanged_reference_rankings=rc,downloaded_coordinate_hashes=len(manifest),committed_runner_matches_executed_snapshot=True,controller_matches=True)
(r/'reference_score_audit.json').write_text(json.dumps(record,indent=2));print(record)
