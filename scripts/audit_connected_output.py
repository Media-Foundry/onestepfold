#!/usr/bin/env python3
"""Read-only NumPy audit of the six archived connected outputs."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json


def angle(a,b,c):
    x=a-b;y=c-b
    return np.dot(x,y)/np.linalg.norm(x)/np.linalg.norm(y)


def dihedral(a,b,c,d):
    axis=(c-b)/np.linalg.norm(c-b)
    u=a-b;u-=np.dot(u,axis)*axis;u/=np.linalg.norm(u)
    v=d-c;v-=np.dot(v,axis)*axis;v/=np.linalg.norm(v)
    return np.array([np.dot(u,v),np.dot(np.cross(u,v),axis)])


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--source',type=Path,required=True);a=p.parse_args();root=a.root;source=a.source
    lock=json.loads((root/'lock.json').read_text());report=json.loads((root/'report.json').read_text());assert report['complete']
    assert sha256(root/'lock.json')==report['lock_sha256']
    for f,digest in lock['source_hashes'].items():assert sha256(Path(f))==digest
    assert sha256(root/'chemical_reference.npz')==lock['reference_sha256']
    assert sha256(root/'variants.json')==lock['variants_sha256']
    assert sha256(source/'topology.pt')==lock['topology_sha256']
    top=torch.load(source/'topology.pt',map_location='cpu',weights_only=False)['topology']
    ref=np.load(root/'chemical_reference.npz');names=ref['atom_names'];res=ref['residue_ids']
    anchors=[[int(np.flatnonzero((res==i)&(names==n))[0]) for n in ['N','CA','C','O']] for i in range(1,len(lock['sequence'])+1)]
    b=top.bonds.numpy();pairs=top.pairs.numpy();radii=top.radii.numpy();peptide=top.peptide.numpy();ca,n,c,cb=top.centres.numpy().T
    rows=[]
    for source_case,row in zip(lock['cases'],report['cases']):
        assert row['success'];assert sha256(Path(source_case['file']))==source_case['sha256']
        file=root/row['output_file'];assert sha256(file)==row['output_sha256'];z=np.load(file)
        old=np.load(source_case['file']);assert np.array_equal(z['raw'],old['coordinates'].reshape(-1,3))
        for key in ['atom_names','residue_ids','chain_ids']:assert np.array_equal(z[key],ref[key])
        err=0.
        for name in ['raw','local','connected']:
            x=z[name];assert np.isfinite(x).all()
            distances=np.linalg.norm(x[b[:,0]]-x[b[:,1]],axis=-1);errors=distances-top.ideal.numpy()
            d=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=-1)
            signed=(np.cross(x[n]-x[ca],x[c]-x[ca])*(x[cb]-x[ca])).sum(-1)
            metrics=dict(bond_rmse=float(np.sqrt(np.mean(errors**2))),peptide_mae=float(np.mean(np.abs(errors[peptide]))),
                         chirality_fraction=float(np.mean(signed*top.volumes.numpy()>0)),severe_pairs=int(np.sum(d<1)),
                         max_penetration=float(np.maximum(0,radii[pairs[:,0]]+radii[pairs[:,1]]-d).max()))
            for k,v in metrics.items():err=max(err,abs(v-row['metrics'][name]['geometry'][k]))
        raw=z['raw'];x=z['connected'];phase_errors=[];bond_errors=[];angle_errors=[];omega_errors=[];oxygen_errors=[]
        for i in range(1,len(anchors)):
            pn,pa,pc,po=anchors[i-1];n1,ca1,c1,_=anchors[i]
            for ids in [(pn,pa,pc,n1),(pc,n1,ca1,c1)]:
                phase_errors.append(float(np.max(np.abs(dihedral(*x[list(ids)])-dihedral(*raw[list(ids)])))))
            bond_errors.append(abs(np.linalg.norm(x[pc]-x[n1])-(1.341 if lock['sequence'][i]=='P' else 1.329)))
            angle_errors += [abs(angle(x[pa],x[pc],x[n1])+.4473),abs(angle(x[pc],x[n1],x[ca1])+.5203)]
            omega_errors.append(float(np.max(np.abs(dihedral(x[pa],x[pc],x[n1],x[ca1])-[-1,0]))))
            oxygen_errors.append(float(np.max(np.abs(dihedral(x[n1],x[pa],x[pc],x[po])-[-1,0]))))
        checks=dict(metric_max_abs=err,phi_psi_phase_max_abs=max(phase_errors),cn_length_max_abs=max(bond_errors),
                    connection_cosine_max_abs=max(angle_errors),trans_omega_max_abs=max(omega_errors),carbonyl_plane_max_abs=max(oxygen_errors))
        assert all(v<1e-6 for v in checks.values()),checks
        rows.append(dict(arm=row['arm'],seed=row['seed'],**checks))
    write_json(root/'audit.json',dict(complete=True,cases=rows,source_sha256=sha256(Path(__file__)),report_sha256=sha256(root/'report.json'),
                                    interpretation='coordinate/constraint audit only; no model quality or utility certification'))
    print(json.dumps(rows))
if __name__=='__main__':main()
