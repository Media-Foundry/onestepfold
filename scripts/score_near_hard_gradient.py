#!/usr/bin/env python3
"""Independent artifact/scalar/geometry audit without changing GPU FD verdicts."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fastglycan.hybrid_geometry import GeometryTopology,hard_accept
from fastglycan.conditioning_diagnostics import weighted_geometry_objectives
from fastglycan.near_hard_diagnostics import fd_measurement,summarize_directions
from fastglycan.paired_teacher_protocol import sha256,write_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();lock=json.load(open(root/'lock.json'));jobs=json.load(open(root/'jobs.json'))
 if len(jobs)!=8 or any(row['exit_code']!=0 for row in jobs):raise ValueError('incomplete or failed batch')
 results=[];hashes={};total_coordinates=0;max_loss_replay=0.;max_geometry_replay=0.
 for job in jobs:
  folder=root/job['label'];report=json.load(open(folder/'report.json'));assert report['complete'] and report['lock_sha256']==sha256(root/'lock.json')
  assert report['full_forward_calls']==34 and report['atom_cache_builder_checks']==68
  for filename,key in [('baseline.npz','baseline_sha256'),('gradients.pt','gradients_sha256'),('topology.pt','topology_sha256')]:
   assert sha256(folder/filename)==report[key];hashes[str((folder/filename).relative_to(root))]=report[key]
  with np.load(folder/'baseline.npz') as data:
   point=torch.tensor(data['coordinates'],dtype=torch.float64);hard=torch.tensor(data['hard_coordinates'],dtype=torch.float64);p0=torch.tensor(data['probabilities']);q0=torch.tensor(data['logits'])
  meta=torch.load(folder/'topology.pt',map_location='cpu',weights_only=False);topology=GeometryTopology(meta['atoms'],meta['reference'].numpy());ca=meta['ca_indices']
  for x,label in [(hard,'hard_geometry'),(point,'geometry')]:
   stats=topology.terms(x)[1]
   delta=max(abs(stats[k]-report[label][k]) for k in stats);max_geometry_replay=max(max_geometry_replay,delta)
   if delta>1e-4:raise ValueError('geometry mismatch '+str(folder))
  assert hard_accept(-1.,0.,report['geometry'],report['hard_geometry'])==report['geometry_gate']
  gradients=torch.load(folder/'gradients.pt',map_location='cpu',weights_only=True)
  for direction,vector in zip(report['directions'],gradients['directions']):
   assert len(direction['rows'])==len(lock['h'])
   for row,h in zip(direction['rows'],lock['h']):
    assert row['h']==h;path=folder/row['coordinate_file'];assert sha256(path)==row['coordinate_sha256'];hashes[str(path.relative_to(root))]=row['coordinate_sha256']
    with np.load(path) as d:
     xp=torch.tensor(d['coordinates_plus'],dtype=torch.float64);xm=torch.tensor(d['coordinates_minus'],dtype=torch.float64)
     pp=torch.tensor(d['probabilities_plus']);pm=torch.tensor(d['probabilities_minus'])
    assert (pp>0).all() and (pm>0).all()
    assert torch.equal(pp.argmax(-1),p0.argmax(-1)) and torch.equal(pm.argmax(-1),p0.argmax(-1))
    for sign,probability in [(1,pp),(-1,pm)]:
     if float(((q0+sign*h*vector).softmax(-1)-probability).abs().max())>3e-7:raise ValueError('probability input replay mismatch')
    dp=pp.double()-pm.double();dx=xp-xm;pnorm=float(dp.norm());xnorm=float(dx.norm())
    assert abs(pnorm-row['probability_delta_norm'])<1e-12 and abs(xnorm-row['coordinate_delta_norm'])<1e-10
    lp=weighted_geometry_objectives(xp,ca,topology);lm=weighted_geometry_objectives(xm,ca,topology)
    lp['new']+=.01*(pp.double()*(pp.double().log()-p0.double().log())).sum(-1).mean()
    lm['new']+=.01*(pm.double()*(pm.double().log()-p0.double().log())).sum(-1).mean()
    for name in ['old','new']:
     original=row['objectives'][name]['nonlinear'];analytic=float((gradients['gradients'][name].double()*vector.double()).sum())
     assert abs(analytic-original['analytic'])<1e-10
     # Check values, never substitute CPU recalculation for the recorded GPU FD.
     delta=max(abs(float(lp[name])-original['loss_plus']),abs(float(lm[name])-original['loss_minus']));max_loss_replay=max(max_loss_replay,delta)
     if delta>2e-5:raise ValueError('loss replay mismatch '+str(path))
     computed=fd_measurement(original['analytic'],original['loss_plus'],original['loss_minus'],h,probability_delta_norm=pnorm,coordinate_delta_norm=xnorm)
     assert computed==original
     direct=float((gradients['trust_gradient'].double()*vector.double()).sum()) if name=='new' else 0.
     numerator=float((gradients['coordinate_gradients'][name].double()*dx).sum())+2*h*direct
     stored=row['objectives'][name]['linearized'];assert abs(numerator-stored['numerator'])<1e-10
    total_coordinates+=2
  for name in ['old','new']:
   stats=report['gradient_stats'][name]
   for kind in ['nonlinear','linearized']:
    computed=summarize_directions([[row['objectives'][name][kind] for row in d['rows']] for d in report['directions']],finite=stats['finite'],gradient_norm=stats['norm'],repeat_max_abs=stats['repeat_max_abs'])
    assert computed==report['summary'][name][kind]
  total_coordinates+=2;hashes[str((folder/'report.json').relative_to(root))]=sha256(folder/'report.json')
  results.append(dict(name=job['label'],alpha=report['alpha'],steps=report['steps'],summary=report['summary'],geometry_gate=report['geometry_gate'],hard_geometry_gate=report['hard_geometry_gate'],
    grad_no_grad_exact=report['grad_no_grad_exact'],repeated_forward_exact=report['repeated_forward_exact'],gradient_stats=report['gradient_stats'],near_hard_ca_rmsd=report['near_hard_ca_rmsd']))
 write_json(root/'audit.json',dict(complete=True,runs=results,coordinate_records=total_coordinates,artifact_sha256=hashes,max_loss_replay_difference=max_loss_replay,max_geometry_replay_difference=max_geometry_replay,model_deployment_accepted=False))

if __name__=='__main__':main()
