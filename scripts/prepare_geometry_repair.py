#!/usr/bin/env python3
"""Freeze the full existing batch and force-field/software provenance before repair."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import openmm.app as app
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.input=a.input.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
assert not (a.out/'lock.json').exists(), 'do not overwrite locked protocol'
r=json.loads((a.input/'report.json').read_text());audit=json.loads((a.input/'audit.json').read_text());assert audit['report_sha256']==sha256(a.input/'report.json')
old=json.loads((a.input/'lock.json').read_text());rows={0:r['parent']}
for c in r['candidates']:rows[c['hard']['index']]=c['hard']
cases=[]
for index,row in sorted(rows.items()):
 for seed in old['evaluation_seeds']:
  v=row['values'][str(seed)];base=a.input/f'worker{index%old["workers"]}'
  cases.append(dict(index=index,seed=seed,sequence=row['sequence'],coordinate=str(base/v['coordinate_file']),coordinate_sha256=v['coordinate_sha256'],
      topology=str(base/row['topology_file']),topology_sha256=row['topology_sha256'],raw_task=v['task'],raw_geometry=v['geometry']))
assert len(cases)==99
root=Path(__file__).resolve().parents[1]
files=[root/'docs/mini_geometry_repair_v1.md',root/'src/fastglycan/geometry_repair.py',root/'src/fastglycan/hybrid_geometry.py',root/'src/fastglycan/collision_audit.py',root/'src/fastglycan/mutation_utility.py',root/'src/fastglycan/sequence_gate_metrics.py']+list(root.glob('scripts/*geometry_repair.py'))
ffroot=Path(app.__file__).parent/'data'
xmls=list((ffroot/'amber14').glob('*.xml'))+list((ffroot/'implicit').glob('*.xml'))
lock=dict(scope='development geometry repair only',cases=cases,input=str(a.input),
 original_report_sha256=sha256(a.input/'report.json'),candidate_sha256=sha256(a.input/'candidates.json'),
 confirmation_seeds=old['confirmation_seeds'],source_hashes={str(f):sha256(f) for f in files},
 packages={p:importlib.metadata.version(p) for p in ['openmm','pdbfixer','numpy','torch']},
 forcefield_hashes={str(f):sha256(f) for f in xmls},
 protocol=dict(k_kj_mol_nm2=1000,tolerance_kj_mol_nm=10,max_iterations=2000,case_timeout_seconds=1800,workers=4,cpu_threads=2))
write_json(a.out/'lock.json',lock)
