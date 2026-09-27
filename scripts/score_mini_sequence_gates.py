#!/usr/bin/env python3
"""Collect four gates without converting failed scientific gates into success."""
import argparse,json
from pathlib import Path
import numpy as np
from fastglycan.models.soft_sequence_chart import native_sequence_features
from fastglycan.sequence_gate_metrics import atom_geometry
from fastglycan.paired_teacher_protocol import write_json,sha256

def main():
 p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result=dict(complete=True,runs=[],scope='exploratory monomer proxy; not binder-oracle acceptance')
 for folder in a.runs:
  report=json.load(open(folder/'report.json'))
  if not report['complete']:raise RuntimeError(f'incomplete {folder}')
  geometry=[]
  for path in sorted(folder.glob('*_seed*_s*.npz')):
   with np.load(path) as d:
    sequence=str(d['sequence']);features,atoms=native_sequence_features(sequence)
    assert np.array_equal(atoms.atom_name,d['atom_names']) and np.array_equal(atoms.res_id,d['residue_ids'])
    geometry.append(dict(artifact=path.name,**atom_geometry(d['coordinates'],atoms,features['ref_pos'].numpy())))
  r=report['gates']['4_hard_rebuild_replay']
  hard_replay=r['embedding_max_abs']<=1e-5 and r['feature_max_abs']<=1e-5 and r['coordinate_max_abs']<=.002
  observations=report['gates']['4_independent_noise'];index={(x['seed'],x['label'],x['steps']):x for x in observations}
  hard_improvement={f's{s}_seed{seed}':index[seed,'optimized',s]['loss']-index[seed,'initial',s]['loss'] for seed in (103,107) for s in (1,2)}
  result['runs'].append(dict(path=str(folder),report_sha256=sha256(folder/'report.json'),
      initial_sequence=report['sequence'],final_sequence=report['final_sequence'],
      gates=dict(native_replay=report['gates']['1_hard_replay']['passed'],
                 local_gradient_s1=report['gates']['2_s1_local_derivative']['passed'],
                 local_gradient_s2=report['gates']['2_s2_local_derivative']['passed'],
                 soft_optimization=report['gates']['3_optimization']['soft_loss_decreased'],
                 hard_replay=hard_replay,
                 hard_improves_both_noises_own_sampler=all(hard_improvement[f's{report["opt_s"]}_seed{seed}']<0 for seed in (103,107))),
      gradient_cosine=report['gradient_cosine'],hard_loss_deltas=hard_improvement,geometry=geometry,
      topology_changes=report['gates']['3_optimization']['topology_changes'],
      global_boundary_continuity='unverified',deployment_accepted=False))
 a.out.mkdir(exist_ok=False);write_json(a.out/'report.json',result)
 write_json(a.out/'acceptance.json',dict(artifacts_complete=True,report_sha256=sha256(a.out/'report.json'),deployment_accepted=False))
if __name__=='__main__':main()
