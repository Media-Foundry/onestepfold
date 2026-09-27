from pathlib import Path
import json,shutil,hashlib
r=Path('/data/user/shuang886/Folding/c4_s1_attribution_v1_20260927');out=r/'diamondhill_bundle';out.mkdir();(out/'packets').mkdir()
l=json.loads((r/'lock.json').read_text());old=Path(l['old_root']);prep=json.loads((old/'repeat/preparation.json').read_text());new=json.loads((r/'prepare_b/preparation.json').read_text())
for name in ('lock.json','manifest.json','precision_lock.json'):shutil.copy2(r/name,out/name)
shutil.copytree(r/'code_precision_v1',out/'code_v1')
infos={}
for g in l['panel_b']:
 source=old/'repeat/packets'/f'{g}.pt' if g in prep['packets'] else r/'prepare_b/packets'/f'{g}.pt'
 (out/'packets'/f'{g}.pt').symlink_to(source);infos[g]=(prep if g in prep['packets'] else new)['packets'][g]
(out/'packets.json').write_text(json.dumps(infos,indent=2))
for i in range(8):
 f=out/f'b_{i}';f.mkdir()
 for p in (r/f'b_{i}').iterdir():
  if p.suffix in ('.npz','.json'):(f/p.name).symlink_to(p)
(out/'environment_hpc3.json').write_text((r/'preflight/environment.json').read_text())
manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
(out/'bundle_manifest.json').write_text(json.dumps(dict(files=manifest),indent=2));print(len(manifest),'files')
