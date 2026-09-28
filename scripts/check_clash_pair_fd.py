#!/usr/bin/env python3
"""Separate denoiser directional response from downstream loss curvature and precision."""
import argparse,json
from pathlib import Path
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_esm import AMINO_ACIDS,sequence_probabilities
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features
from fastglycan.models.differentiable_mini import full_recycle_pairformer,diffusion_from_conditioning
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.sequence_gate_metrics import contact_objective
from fastglycan.paired_teacher_protocol import write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--case',required=True);a=p.parse_args();root=a.root.resolve();lock=rt.load_json(root/'lock.json');seq=lock['cases'][a.case]['sequence'];out=root/f'clash_pair_fd_{a.case}';out.mkdir(exist_ok=False)
runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False);torch.serialization.add_safe_globals([argparse.Namespace])
from protenix.data.esm.compute_esm import load_esm_model
esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates);topology=GeometryTopology(chart.atoms,chart.native['ref_pos'].cpu().numpy());initial=identity_noise(chart.atoms,211,device='cuda')
with torch.no_grad():
 features=chart.features((sequence_probabilities(seq,device='cuda')*4).softmax(-1))
 point=full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False)
shapes=[v.shape for v in point];sizes=[v.numel() for v in point];scales=[max(float(v.square().mean().sqrt()),1e-3) for v in point];flat=torch.cat([v.flatten() for v in point])
def unpack(v):return tuple(t.reshape(shape) for t,shape in zip(v.split(sizes),shapes))



from fastglycan.paired_teacher_protocol import sha256
with torch.no_grad():x0=diffusion_from_conditioning(model,features,initial,unpack(flat),steps=1)
generator=torch.Generator(device='cuda').manual_seed(731)
for index in range(2):
 v=torch.cat([(torch.randn(shape,device='cuda',generator=generator)*scale).flatten() for shape,scale in zip(shapes,scales)])
pairs=topology.pairs.to('cuda');i,j=pairs.T;radii=topology.radii.to('cuda').double();radius=radii[i]+radii[j];n=topology.n
base=x0[0].double();r0=base[i]-base[j];distance=r0.norm(dim=-1);excess=torch.relu(radius-distance-1.5)
records=[];saved={'x0':x0.cpu()}
for h in [.003,.001]:
 with torch.no_grad():
  xp=diffusion_from_conditioning(model,features,initial,unpack(flat+h*v),steps=1)[0].double()
  xm=diffusion_from_conditioning(model,features,initial,unpack(flat-h*v),steps=1)[0].double()
 response=(xp-xm)/(2*h);dr=response[i]-response[j]
 linear=-2*excess*(r0*dr).sum(-1)/distance.clamp_min(1e-30)/n
 dp=(xp[i]-xp[j]).norm(dim=-1);dm=(xm[i]-xm[j]).norm(dim=-1)
 ep=torch.relu(radius-dp-1.5);em=torch.relu(radius-dm-1.5)
 finite=(ep.square()-em.square())/(2*h)/n;remainder=finite-linear
 top=torch.argsort(remainder.abs(),descending=True)[:20];rows=[]
 for k in top.tolist():
  ii,jj=pairs[k].tolist()
  def atom_label(t):return dict(index=t,residue=int(chart.atoms.res_id[t]),resname=str(chart.atoms.res_name[t]),atom=str(chart.atoms.atom_name[t]))
  rows.append(dict(first=atom_label(ii),second=atom_label(jj),base_distance=float(distance[k]),plus_distance=float(dp[k]),minus_distance=float(dm[k]),
    active_zero=bool(excess[k]>0),active_plus=bool(ep[k]>0),active_minus=bool(em[k]>0),linear=float(linear[k]),finite_difference=float(finite[k]),remainder=float(remainder[k])))
 records.append(dict(h=h,total_linear=float(linear.sum()),total_finite_difference=float(finite.sum()),total_remainder=float(remainder.sum()),top_pairs=rows,
   minimum_pair_distance=float(distance.min()),hinge_switch_pairs=int((((excess>0)!=(ep>0)).logical_or((excess>0)!=(em>0))).sum())))
 saved['plus_'+str(h)]=xp.cpu();saved['minus_'+str(h)]=xm.cpu()
path=out/'coordinates.pt';torch.save(saved,path)
write_json(out/'report.json',dict(complete=True,case=a.case,direction_index=1,scope='same fixed soft chart, not native hard coordinates; clash pair attribution only',rows=records,
 source_sha256=sha256(Path(__file__)),coordinate_sha256=sha256(path),lock_sha256=sha256(root/'lock.json')))
