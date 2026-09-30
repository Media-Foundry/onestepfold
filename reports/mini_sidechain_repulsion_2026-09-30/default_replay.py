import json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.sidechain_projection_fit import fit_sidechain_projection
from fastglycan.paired_teacher_protocol import sha256,write_json
root=Path('/media/PM982/onestepfold/sidechain_repulsion_v1_20260930');pure=root.parent/'sidechain_fit_v1_20260930'
torch.set_num_threads(1);report=json.loads((pure/'cases/00/report.json').read_text());lock=json.loads((pure/'lock.json').read_text());source=Path(lock['source']);selection=json.loads((source/'selection.json').read_text());item=selection[0]
p=source/'chemistry'/item['group_id'];d=dict(np.load(pure/'cases/00/coordinates.npz'))
adapter=ArticulatedOutput(d['output_reference'],d['atom_names'],d['residue_ids'],item['sequence'],json.loads((p/'variants.json').read_text())).double()
begin=time.monotonic();fit=fit_sidechain_projection(adapter,torch.tensor(d['raw']),d['atom_names'])
err=float(np.max(np.abs(fit['coordinates'].numpy()-d['final'])));assert err<1e-10
assert fit['closure_calls']==report['fit']['closure_calls'] and fit['iterations']==report['fit']['iterations']
write_json(root/'default_replay.json',dict(case=0,pure_report_sha256=sha256(pure/'cases/00/report.json'),max_abs=err,bitwise=np.array_equal(fit['coordinates'].numpy(),d['final']),closures=fit['closure_calls'],iterations=fit['iterations'],seconds=time.monotonic()-begin))
