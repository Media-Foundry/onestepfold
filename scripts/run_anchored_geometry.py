#!/usr/bin/env python3
"""Locked six-case joint-pose feasibility; independent workers, no model training."""
import argparse,concurrent.futures,inspect,json,os,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.anchored_geometry import PoseVariables,JointObjective,solve
from fastglycan.geometry_repair import preservation
from fastglycan.repair_outcomes import absolute_failures
from fastglycan.collision_audit import collision_records


def arguments():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--source',type=Path);p.add_argument('--topology',type=Path);p.add_argument('--mode',choices=['prepare','batch','case','collect'],required=True);p.add_argument('--case',type=int);return p.parse_args()


def prepare(a):
 root=a.root;assert not (root/'lock.json').exists();old=json.loads((a.source/'lock.json').read_text())
 previous=json.loads((a.source/'report.json').read_text());audit=json.loads((a.source/'audit.json').read_text())
 assert previous['complete'] and audit['complete'] and audit['report_sha256']==sha256(a.source/'report.json')
 assert sha256(a.source/'chemical_reference.npz')==old['reference_sha256']
 assert sha256(a.source/'variants.json')==old['variants_sha256']
 assert sha256(a.topology)==old['topology_sha256']
 for case in old['cases']:assert sha256(Path(case['file']))==case['sha256']
 modules=['anchored_geometry','articulated_output','articulated_reference','hybrid_geometry','geometry_repair','repair_outcomes','collision_audit']
 files=[Path(inspect.getfile(__import__('fastglycan.'+m,fromlist=['x']))) for m in modules]+[Path(__file__),root/'code/docs/mini_anchored_geometry_v1.md']
 write_json(root/'lock.json',dict(sequence=old['sequence'],cases=old['cases'],reference=str(a.source/'chemical_reference.npz'),reference_sha256=old['reference_sha256'],variants=str(a.source/'variants.json'),variants_sha256=old['variants_sha256'],topology=str(a.topology),topology_sha256=old['topology_sha256'],source_hashes={str(f):sha256(f) for f in files},prior_lock_sha256=sha256(a.source/'lock.json'),timeout_seconds=900,devices=list(range(6)),scope='six same-parent regression inputs; iterative feasibility only'))


def case(a):
 root=a.root;folder=root/'cases'/f'{a.case:02d}';folder.mkdir(parents=True,exist_ok=False)
 lock=json.loads((root/'lock.json').read_text());item=lock['cases'][a.case];start=time.monotonic()
 result=dict(case=a.case,arm=item['arm'],seed=item['seed'],success=False,lock_sha256=sha256(root/'lock.json'))
 try:
  torch.set_num_threads(1)
  for f,d in lock['source_hashes'].items():assert sha256(Path(f))==d
  for key in ['reference','variants','topology']:assert sha256(Path(lock[key]))==lock[key+'_sha256']
  assert sha256(Path(item['file']))==item['sha256']
  ref=np.load(lock['reference']);names=ref['atom_names'];res=ref['residue_ids'];chains=ref['chain_ids'];sequence=lock['sequence']
  data=np.load(item['file'])
  for key in ['atom_names','residue_ids','chain_ids']:assert np.array_equal(data[key],ref[key])
  assert len(set(chains))==1
  topology=torch.load(lock['topology'],map_location='cpu',weights_only=False)['topology']
  for i,j in topology.bonds.tolist():
   if res[i]!=res[j]:assert abs(int(res[i])-int(res[j]))==1 and {names[i],names[j]}=={'C','N'}
  anchors=[[int(np.flatnonzero((res==i)&(names==n))[0]) for n in ['N','CA','C','O']] for i in range(1,len(sequence)+1)]
  raw=torch.tensor(data['coordinates'].reshape(-1,3),dtype=torch.float64,device='cuda')
  adapter=ArticulatedOutput(ref['reference'],names,res,sequence,json.loads(Path(lock['variants']).read_text())).double().cuda()
  variables=PoseVariables(adapter,raw);objective=JointObjective(raw,anchors,sequence,topology.pairs,topology.radii).cuda()
  result.update(torch_version=torch.__version__,device=torch.cuda.get_device_name(0),visible_device=os.environ.get('ROCR_VISIBLE_DEVICES'),cis_connections=(torch.nonzero(objective.omega_target[:,0]>0).flatten()+1).tolist(),initial_max_abs_vs_local=float((variables()-variables.initial).abs().max()))
  assert result['initial_max_abs_vs_local']<1e-8
  initial=variables().detach().cpu();write_json(folder/'progress.json',dict(stage='initialized',**result))
  def callback(row):write_json(folder/'progress.json',dict(stage='solving',seconds=time.monotonic()-start,**row))
  output,history=solve(variables,objective,callback);torch.cuda.synchronize()
  result['history']=history;result['solver_seconds']=time.monotonic()-start
  ca=np.array(anchors)[:,1];side=[]
  for i,aa in enumerate(sequence,1):
   if aa in 'IT':side.append([int(np.flatnonzero((res==i)&(names==n))[0]) for n in ['CB','CA','CG1' if aa=='I' else 'OG1','CG2']])
  side=np.array(side,dtype=int).reshape(-1,4)
  def signed(x,centres):
   c,a,b,d=centres.T;return (np.cross(x[a]-x[c],x[b]-x[c])*(x[d]-x[c])).sum(-1)
  refside=signed(ref['reference'],side)
  assert np.all(np.abs(refside)>1e-4)
  coordinates=dict(raw=raw.cpu(),initial=initial,final=output.cpu());result['metrics']={}
  for name,x in coordinates.items():
   _,geometry=topology.terms(x)
   with torch.no_grad():residuals=objective.residuals(x.cuda())
   residuals={k:v.cpu().numpy() for k,v in residuals.items()}
   maximum={k:float(np.abs(v).max()) for k,v in residuals.items()}
   tolerances=dict(cn=.03,angle_c=.04,angle_n=.04,omega=.1,carbonyl=.1)
   connection_pass=all(maximum[k]<=v+1e-6 for k,v in tolerances.items())
   geometry_failures=absolute_failures(geometry);pres=preservation(raw.cpu().numpy(),x.numpy(),ca)
   sidewrong=int((signed(x.numpy(),side)*refside<=0).sum());allca=geometry['chirality_fraction']==1.
   result['metrics'][name]=dict(geometry=geometry,absolute_failures=geometry_failures,preservation=pres,
    connection_max=maximum,connection_residuals={k:v.tolist() for k,v in residuals.items()},connection_pass=connection_pass,
    sidechain_wrong=sidewrong,sidechain_centres=len(side),all_checked_chirality_pass=allca and sidewrong==0,
    joint_pass=not geometry_failures and pres['accepted'] and connection_pass and allca and sidewrong==0,
    pairs=collision_records(x.numpy(),topology,names,res,chains,sequence))
  q=torch.cat([p[:,:6].detach() for p in variables.variables]);torsions=torch.cat([p[:,6:].detach().flatten() for p in variables.variables])
  result['parameter_changes']=dict(max_translation=float(q[:,:3].norm(dim=-1).max()),max_rotation_vector_radians=float(q[:,3:6].norm(dim=-1).max()),max_torsion_radians=float(torsions.abs().max()))
  torch.save({k:v.detach().cpu() for k,v in variables.state_dict().items()},folder/'state.pt')
  np.savez_compressed(folder/'coordinates.npz',**{k:v.numpy() for k,v in coordinates.items()},atom_names=names,residue_ids=res,chain_ids=chains)
  result.update(success=True,coordinates_sha256=sha256(folder/'coordinates.npz'),state_sha256=sha256(folder/'state.pt'))
 except Exception:result['error']=traceback.format_exc()
 result['seconds']=time.monotonic()-start;write_json(folder/'report.json',result)
 if not result['success']:raise RuntimeError(result['error'])


def collect(root):
 lock=json.loads((root/'lock.json').read_text());rows=[]
 for i in range(len(lock['cases'])):
  f=root/'cases'/f'{i:02d}'/'report.json'
  rows.append(json.loads(f.read_text()) if f.exists() else dict(case=i,success=False,error='missing case report'))
 write_json(root/'report.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),cases=rows,successful=sum(x['success'] for x in rows),joint_pass=sum(x['success'] and x['metrics']['final']['joint_pass'] for x in rows),scope=lock['scope']))


def batch(a):
 root=a.root;lock=json.loads((root/'lock.json').read_text());assert not (root/'controller.json').exists()
 write_json(root/'controller.json',dict(pid=os.getpid(),phase='running',cases=6))
 def worker(i):
  env=dict(os.environ,ROCR_VISIBLE_DEVICES=str(lock['devices'][i]),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
  with (root/f'case{i}.log').open('x') as log:
   try:r=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--root',str(root),'--mode','case','--case',str(i)],env=env,stdout=log,stderr=log,timeout=lock['timeout_seconds']);return dict(case=i,returncode=r.returncode)
   except subprocess.TimeoutExpired:return dict(case=i,returncode=124,reason='900s external timeout')
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:exits=list(pool.map(worker,range(6)))
 write_json(root/'exit.json',exits);collect(root);write_json(root/'controller.json',dict(pid=os.getpid(),phase='finished',exits=exits))

if __name__=='__main__':
 a=arguments();a.root=a.root.resolve();a.root.mkdir(parents=True,exist_ok=True)
 if a.source:a.source=a.source.resolve()
 if a.topology:a.topology=a.topology.resolve()
 if a.mode=='prepare':prepare(a)
 elif a.mode=='case':case(a)
 elif a.mode=='batch':batch(a)
 else:collect(a.root)
