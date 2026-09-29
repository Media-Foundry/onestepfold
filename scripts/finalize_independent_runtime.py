#!/usr/bin/env python3
"""Seal complete runtime after CPU preflight, preserving the preliminary manifest."""
import argparse,importlib,inspect,json
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256,write_json

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root
assert not (r/'controller.json').exists()
old=json.loads((r/'runtime_lock.json').read_text());assert len(old['prepared'])==32
for item in old['prepared']:
 for f,h in item['files'].items():assert sha256(Path(f))==h
for f,h in old['frozen_geometry'].items():assert sha256(Path(f))==h
required=['run_independent_geometry_validation.py','run_anchored_geometry.py','audit_anchored_geometry.py','audit_independent_geometry_validation.py','collect_independent_geometry_validation.py']
for name in required:assert (r/'code/scripts'/name).exists()
for name in ['run_independent_geometry_validation','run_anchored_geometry','fastglycan.independent_geometry_eval','tmtools','runner.batch_inference','protenix.data.esm.compute_esm']:
 importlib.import_module(name)
source={str(p):sha256(p) for p in sorted((r/'code').rglob('*.py'))}
for name in ['protenix','esm','runner','configs']:
 folder=Path(inspect.getfile(importlib.import_module(name))).parent
 source.update({str(p):sha256(p) for p in sorted(folder.rglob('*.py'))})
import tmtools
scoring_root=Path(tmtools.__file__).parent
old['scoring_dependency']=dict(name='tmtools',version='0.3.0',files={str(p):sha256(p) for p in scoring_root.rglob('*') if p.is_file() and p.suffix in ['.py','.so']},wheel_metadata_sha256=sha256(r/'wheels/provenance.json'))
# This correction is entirely before GPU outputs: initial pack omitted two old
# entry-point scripts. Preserve that manifest instead of overwriting its history.
(r/'runtime_lock.json').rename(r/'runtime_lock_preflight_v1.json')
old.update(source_hashes=source,preliminary_runtime_lock_sha256=sha256(r/'runtime_lock_preflight_v1.json'),runtime_pack_preflight='complete; original solver/audit entry points restored before GPU',finalized_before_gpu=True)
write_json(r/'runtime_lock.json',old);print('final runtime import preflight and lock passed')
