"""Independent dense-distance and rigid-fit CPU audit of saved Chord outputs."""
import argparse
from pathlib import Path
import json
import numpy as np
import torch
from scipy.spatial.distance import cdist
from scipy.spatial.transform import Rotation
from fastglycan.paired_teacher_protocol import sha256,write_json


def audit_chord_outputs(root):
    lock=json.loads((root/'lock.json').read_text());report=json.loads((root/'report.json').read_text())
    assert report['complete'] and report['lock_sha256']==sha256(root/'lock.json')
    for p,h in {**lock['input_hashes'],**lock['code_hashes']}.items():assert sha256(Path(p))==h,p
    errors=dict(lddt=0.,rmsd=0.,max_penetration=0.,field_reconstruction=0.);backbones=0;full=0
    def dense_lddt(x,y,res):
        dx,dy=cdist(x,x),cdist(y,y);allowed=(dy<15)&(res[:,None]!=res[None,:]);counts=allowed.sum(1)
        pairscore=sum((np.abs(dx-dy)<v).astype(float) for v in [.5,1,2,4])/4
        return float(((pairscore*allowed).sum(1)[counts>0]/counts[counts>0]).mean())
    def align(x,y,support):
        x=np.asarray(x,float);y=np.asarray(y,float);a=x[support].mean(0);b=y[support].mean(0)
        rotation,_=Rotation.align_vectors(y[support]-b,x[support]-a)
        return rotation.apply(x-a)+b
    rms=lambda d:float(np.sqrt((d*d).sum(1).mean()))
    for pi,pair in enumerate(lock['pairs']):
        folder=root/'inputs'/str(pi);sm=dict(np.load(folder/'source_gt.npz'));tm=dict(np.load(folder/'target_gt.npz'))
        local=np.load(folder/'local_region.npy');ca=tm['atom_names']=='CA';source=sm['coordinates'][sm['atom_names']=='CA'];target=tm['coordinates'][ca]
        anchored=align(target,source,~local);native=torch.load(folder/'target_native.pt',map_location='cpu',weights_only=False)
        names=tm['atom_names'];ids=tm['residue_ids'];n=len(names);edges=native['atoms'].bonds.as_array()[:,:2]
        adjacency=[set() for _ in range(n)]
        for a,b in edges:adjacency[a].add(int(b));adjacency[b].add(int(a))
        allowed=np.triu(np.ones((n,n),bool),1)
        for i in range(n):
            reached={i};front={i}
            for _ in range(3):front={k for j in front for k in adjacency[j]}-reached;reached|=front
            allowed[i,list(reached)]=False
        radii=np.array([dict(C=1.7,N=1.55,O=1.52,S=1.8)[str(a)[0]] for a in names])
        lookup={(int(r),str(a)):i for i,(r,a) in enumerate(zip(ids,names))};centres=[]
        for ri,aa in enumerate(pair['target_sequence'],1):
            if aa!='G':centres.append([lookup[ri,a] for a in ['CA','N','C','CB']])
            if aa in 'IT':centres.append([lookup[ri,a] for a in ['CB','CA','CG1' if aa=='I' else 'OG1','CG2']])
        centres=np.array(centres)
        def volume(x):return np.linalg.det(np.stack([x[centres[:,k]]-x[centres[:,0]] for k in [1,2,3]],axis=-1))
        refsign=volume(tm['reference'].astype(float))
        for row in [r for r in report['records'] if r['pair_index']==pi]:
            path=root/f'worker_{pi}/noise_{row["seed"]}.npz';xs=np.load(path)
            wr=report['inference_reports'][pi];saved=next(r for r in wr['records'] if r['seed']==row['seed'])
            assert sha256(path)==saved['output_sha256']
            for name in ['naive','smooth']:
                field=xs['high_field'] if name=='naive' else xs['smooth_field']
                err=float(np.max(np.abs(xs[name+'_backbone']-(xs['source_backbone']-16*field))))
                errors['field_reconstruction']=max(errors['field_reconstruction'],err)
            for method,value in row['arms'].items():
                if method=='copy_source':x=source
                elif method.endswith('_backbone'):x=xs[method][:,1]
                else:x=xs[method][ca]
                expected=value['backbone'];p=align(x,source,~local)
                values=dict(ca_aligned_rmsd=rms(align(x,target,np.ones(len(x),bool))-target),
                    local_target_rmsd=rms(p[local]-anchored[local]),nonlocal_target_rmsd=rms(p[~local]-anchored[~local]),
                    nonlocal_motion=rms(p[~local]-source[~local]))
                errors['rmsd']=max(errors['rmsd'],*[abs(v-expected[k]) for k,v in values.items()])
                errors['lddt']=max(errors['lddt'],abs(dense_lddt(x,target,np.arange(len(x)))-expected['ca_lddt']));backbones+=1
                if value['full'] is None:continue
                x=xs[method].astype(float);mask=tm['mask'];quality=value['full'];g=quality['geometry']
                errors['lddt']=max(errors['lddt'],abs(dense_lddt(x[mask],tm['coordinates'][mask],ids[mask])-quality['all_atom_lddt']))
                distances=cdist(x,x);severe=int(((distances<1)&allowed).sum());assert severe==g['severe_pairs']
                depth=np.maximum(0,radii[:,None]+radii[None,:]-distances);maxdepth=float(depth[allowed].max())
                errors['max_penetration']=max(errors['max_penetration'],abs(maxdepth-g['max_penetration']))
                wrong=(volume(x)*refsign<=0);main=names[centres[:,0]]=='CA'
                assert int(wrong[main].sum())==g['ca_chirality_wrong'] and int(wrong[~main].sum())==g['sidechain_checked_wrong']
                full+=1
    assert backbones==72 and full==48 and max(errors.values())<1e-6,errors
    assert all(w['complete'] and w['actual_calls']==dict(denoiser=31,recycle=12) for w in report['inference_reports'])
    write_json(root/'independent_audit.json',dict(complete=True,backbone_scores=backbones,full_atom_scores=full,
        maximum_absolute_errors=errors,actual_denoiser_calls=124,actual_recycle_calls=48,
        scope='dense lDDT, separate rigid-fit implementation, bond-BFS contacts, determinant chirality, saved field arithmetic; no GPU rerun'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();audit_chord_outputs(a.root)
