#!/usr/bin/env python3
"""CPU final metric and independent NumPy pose replay for the locked solver."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.anchored_geometry import PoseVariables


def phase(x,ids):
 a,b,c,d=x[ids];axis=(c-b)/np.linalg.norm(c-b)
 u=a-b;u-=np.dot(u,axis)*axis;u/=np.linalg.norm(u)
 v=d-c;v-=np.dot(v,axis)*axis;v/=np.linalg.norm(v)
 return np.array([np.dot(u,v),np.dot(np.cross(u,v),axis)])


def cosine(a,b,c):
 u=a-b;v=c-b;return np.dot(u,v)/np.linalg.norm(u)/np.linalg.norm(v)


def replay(variables):
 pieces=[]
 for g,p in zip(variables.groups,variables.variables):
  x=g.base.numpy().copy();q=p.detach().numpy()
  for j,r in enumerate(g.rotations):
   origin=x[:,r.parent:r.parent+1];axis=x[:,r.child:r.child+1]-origin;axis/=np.linalg.norm(axis,axis=-1,keepdims=True)
   relative=x-origin;co=np.cos(q[:,6+j])[:,None,None];si=np.sin(q[:,6+j])[:,None,None]
   rotated=origin+relative*co+np.cross(axis,relative)*si+(relative*axis).sum(-1,keepdims=True)*axis*(1-co)
   x=np.where(g.moving[j].numpy()[:,None],rotated,x)
  rot=Rotation.from_rotvec(q[:,3:6]).as_matrix()
  x=(x@rot.transpose(0,2,1)+q[:,None,:3])@g.frame.numpy().transpose(0,2,1)+g.origin.numpy()
  pieces.append(x.reshape(-1,3))
 return np.concatenate(pieces)[variables.restore_order.numpy()]


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
 lock=json.loads((root/'lock.json').read_text());report=json.loads((root/'report.json').read_text());assert report['complete']
 assert sha256(root/'lock.json')==report['lock_sha256']
 for f,d in lock['source_hashes'].items():assert sha256(Path(f))==d
 for key in ['reference','variants','topology']:assert sha256(Path(lock[key]))==lock[key+'_sha256']
 ref=np.load(lock['reference']);names=ref['atom_names'];res=ref['residue_ids'];seq=lock['sequence'];reference=ref['reference']
 top=torch.load(lock['topology'],map_location='cpu',weights_only=False)['topology'];b=top.bonds.numpy();pep=top.peptide.numpy();pairs=top.pairs.numpy();radii=top.radii.numpy();ca,n,c,cb=top.centres.numpy().T
 anchors=[[int(np.flatnonzero((res==i)&(names==name))[0]) for name in ['N','CA','C','O']] for i in range(1,len(seq)+1)]
 side=[]
 for i,s in enumerate(seq,1):
  if s in 'IT':side.append([int(np.flatnonzero((res==i)&(names==name))[0]) for name in ['CB','CA','CG1' if s=='I' else 'OG1','CG2']])
 side=np.array(side);sc,s1,s2,s3=side.T
 side_ref=(np.cross(reference[s1]-reference[sc],reference[s2]-reference[sc])*(reference[s3]-reference[sc])).sum(-1)
 adapter=ArticulatedOutput(reference,names,res,seq,json.loads(Path(lock['variants']).read_text())).double()
 results=[]
 for row,item in zip(report['cases'],lock['cases']):
  if not row['success']:results.append(dict(case=row['case'],success=False,reason='solver failed; no coordinate audit'));continue
  folder=root/'cases'/f"{row['case']:02d}"
  assert sha256(Path(item['file']))==item['sha256'];assert sha256(folder/'coordinates.npz')==row['coordinates_sha256'];assert sha256(folder/'state.pt')==row['state_sha256']
  data=np.load(folder/'coordinates.npz');old=np.load(item['file']);assert np.array_equal(data['raw'],old['coordinates'].reshape(-1,3))
  for key in ['atom_names','residue_ids','chain_ids']:assert np.array_equal(data[key],ref[key])
  variables=PoseVariables(adapter,torch.tensor(data['raw']));variables.load_state_dict(torch.load(folder/'state.pt',map_location='cpu',weights_only=True))
  error=float(np.max(np.abs(replay(variables)-data['final'])));assert error<1e-6
  max_error=0.;verified_pass=None
  for name in ['raw','initial','final']:
   x=data[name];assert np.isfinite(x).all();m=row['metrics'][name]
   d=np.linalg.norm(x[b[:,0]]-x[b[:,1]],axis=-1);e=d-top.ideal.numpy();paird=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=-1)
   chi=(np.cross(x[n]-x[ca],x[c]-x[ca])*(x[cb]-x[ca])).sum(-1)
   g=dict(bond_rmse=float(np.sqrt(np.mean(e*e))),peptide_mae=float(np.mean(np.abs(e[pep]))),chirality_fraction=float(np.mean(chi*top.volumes.numpy()>0)),severe_pairs=int(np.sum(paird<1)),severe_pairs_per_atom=float(np.sum(paird<1)/len(x)),max_penetration=float(np.maximum(0,radii[pairs[:,0]]+radii[pairs[:,1]]-paird).max()))
   sidewrong=int(((np.cross(x[s1]-x[sc],x[s2]-x[sc])*(x[s3]-x[sc])).sum(-1)*side_ref<=0).sum());assert sidewrong==m['sidechain_wrong']
   for k,v in g.items():max_error=max(max_error,abs(v-m['geometry'][k]))
   residuals={k:[] for k in ['cn','angle_c','angle_n','omega','carbonyl']}
   for i,(prev,nxt) in enumerate(zip(anchors,anchors[1:])):
    pn,pa,pc,po=prev;nn,na,nc,no=nxt
    residuals['cn'].append(np.linalg.norm(x[pc]-x[nn])-(1.341 if seq[i+1]=='P' else 1.329))
    residuals['angle_c'].append(cosine(x[pa],x[pc],x[nn])+.4473);residuals['angle_n'].append(cosine(x[pc],x[nn],x[na])+.5203)
    target=1 if i+1 in row['cis_connections'] else -1
    residuals['omega'].append(np.linalg.norm(phase(x,[pa,pc,nn,na])-[target,0]))
    residuals['carbonyl'].append(np.linalg.norm(phase(x,[nn,pa,pc,po])-[-1,0]))
   for k,v in residuals.items():max_error=max(max_error,float(np.max(np.abs(np.asarray(v)-m['connection_residuals'][k]))))
   caix=np.array(anchors)[:,1];diff=x-data['raw'];cr=float(np.sqrt(np.mean(np.sum(diff[caix]**2,-1))));hr=float(np.sqrt(np.mean(np.sum(diff**2,-1))))
   max_error=max(max_error,abs(cr-m['preservation']['ca_rms']),abs(hr-m['preservation']['heavy_rms']))
   cp=all(np.max(np.abs(residuals[k]))<=tol+1e-6 for k,tol in dict(cn=.03,angle_c=.04,angle_n=.04,omega=.1,carbonyl=.1).items())
   valid=bool(g['bond_rmse']<=.25 and g['peptide_mae']<=.15 and g['chirality_fraction']==1 and sidewrong==0 and g['severe_pairs_per_atom']<=.02 and g['max_penetration']<=2 and cr<=1 and hr<=2 and cp)
   assert valid==m['joint_pass'];assert cp==m['connection_pass']
   if name=='final':verified_pass=valid
  assert max_error<1e-6
  results.append(dict(case=row['case'],success=True,numpy_pose_replay_max_abs=error,metric_max_abs=max_error,verified_joint_pass=verified_pass))
 write_json(root/'audit.json',dict(complete=True,report_sha256=sha256(root/'report.json'),source_sha256=sha256(Path(__file__)),cases=results,verified_joint_pass=sum(r.get('verified_joint_pass',False) for r in results)))
 print(json.dumps(results))
if __name__=='__main__':main()
