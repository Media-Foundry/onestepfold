#!/usr/bin/env python3
"""Read-only final artifact-chain verification; no predictions or minimization."""
import argparse,json
from pathlib import Path
import numpy as np
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root.resolve()
lock=json.loads((r/'lock.json').read_text());report=json.loads((r/'report.json').read_text());outcome=json.loads((r/'outcome_analysis.json').read_text());controller=json.loads((r/'controller.json').read_text());analysis=json.loads((r/'analysis_controller.json').read_text());exit_record=json.loads((r/'exit.json').read_text())
assert controller['phase']==analysis['phase']=='finished' and controller['returncode']==analysis['returncode']==0
assert exit_record['complete'] and exit_record['cases']==99 and exit_record['failed']==0
assert report['complete'] and report['audit']['coordinate_recomputations']==99 and report['audit']['max_scalar_error']==0
assert report['lock_sha256']==outcome['lock_sha256']==sha256(r/'lock.json')
assert outcome['final_report_sha256']==sha256(r/'report.json') and analysis['analysis_sha256']==sha256(r/'outcome_analysis.json')
assert len(report['cases'])==len(outcome['cases'])==len(lock['cases'])==99
checked={}
def check(path,digest):
 path=Path(path)
 if str(path) not in checked:checked[str(path)]=sha256(path)
 assert checked[str(path)]==digest,str(path)
for f,d in (lock['source_hashes']|lock['forcefield_hashes']).items():check(f,d)
check(Path(lock['input'])/'report.json',lock['original_report_sha256']);check(Path(lock['input'])/'candidates.json',lock['candidate_sha256'])
for i,item in enumerate(lock['cases']):
 folder=r/'cases'/f'{i:03d}';f=folder/'report.json';v=json.loads(f.read_text())
 assert v['success'] and v['lock_sha256']==sha256(r/'lock.json')
 assert (v['index'],v['seed'])==(item['index'],item['seed'])
 assert report['cases'][i]['report_sha256']==outcome['cases'][i]['report_sha256']==sha256(f)
 for name in ['coordinate','topology']:check(item[name],item[name+'_sha256'])
 check(folder/'coordinates.npz',v['coordinate_sha256']);check(folder/'full.pdb',v['pdb_sha256'])
 x=np.load(folder/'coordinates.npz');original=np.load(item['coordinate'])
 assert np.array_equal(x['raw'],original['coordinates'].reshape(-1,3))
 for key in ['atom_names','residue_ids','chain_ids']:assert np.array_equal(x[key],original[key])
 assert np.array_equal(x['repaired'],x['full'][v['audit']['original_indices']])
 assert np.isfinite(x['full']).all() and v['audit']['original_graph_exact']
write_json(r/'collection_verification.json',dict(complete=True,verified_cases=99,checked_files=len(checked),
 raw_inputs_exact=True,original_atom_projection_exact=True,all_full_coordinates_finite=True,
 controller_exit_zero=True,analysis_exit_zero=True,coordinate_recomputations=99,
 coordinate_recomputation_max_error=report['audit']['max_scalar_error'],
 lock_sha256=sha256(r/'lock.json'),report_sha256=sha256(r/'report.json'),
 outcome_sha256=sha256(r/'outcome_analysis.json'),script_sha256=sha256(Path(__file__))))
