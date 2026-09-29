#!/usr/bin/env python3
"""NumPy local-transform replay and source/statistics checks for CCD comparison."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile

import gemmi
import numpy as np

from fastglycan.articulated_output import ArticulatedOutput


def verify_ccd_template_projection(root,source,templates_path):
    digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=json.loads((root/'report.json').read_text());templates=json.loads(templates_path.read_text())['records']
    for p,h in json.loads((root/'input_lock.json').read_text())['hashes'].items():assert digest(p)==h
    for p,h in report['output_sha256'].items():assert digest(root/p)==h
    assert digest(root/'template_checks.json')==report['template_checks_sha256']
    checks=json.loads((root/'template_checks.json').read_text())
    for aa,t in templates.items():
        block=gemmi.cif.read(str(templates_path.parent/(t['ccd']+'.cif'))).sole_block()
        assert digest(templates_path.parent/(t['ccd']+'.cif'))==t['component_sha256']
        tab=block.get_mmcif_category('_chem_comp_atom.')
        ids=[tab['atom_id'].index(n) for n in t['atom_names']]
        ref=np.array([[float(tab['pdbx_model_Cartn_'+a+'_ideal'][i]) for a in ['x','y','z']] for i in ids])
        np.testing.assert_array_equal(ref,t['ideal'])
    archive=tarfile.open(source/'measurement/source_evidence.tar.gz')
    panel=json.loads(archive.extractfile('extension/selection.json').read())
    row_index={(r['group_id'],int(r['residue'])):r for r in csv.DictReader((root/'residues.csv').open())}
    replay_max=0.;metric_max=0.;bond_max=0.;measured=[];exclusions=[]

    def frame(x,n,ca,c):
        a=x[...,c,:]-x[...,ca,:];a/=np.linalg.norm(a,axis=-1,keepdims=True)
        b=x[...,n,:]-x[...,ca,:];b-=np.sum(a*b,axis=-1,keepdims=True)*a;b/=np.linalg.norm(b,axis=-1,keepdims=True)
        return np.stack([a,b,np.cross(a,b)],axis=-1)

    def phase(x,probe):
        a,b,p,d=[x[:,i] for i in probe];axis=b-a;axis/=np.linalg.norm(axis,axis=-1,keepdims=True)
        u=p-a;v=d-b;u-=np.sum(u*axis,axis=-1,keepdims=True)*axis;v-=np.sum(v*axis,axis=-1,keepdims=True)*axis
        return np.arctan2(np.sum(np.cross(u,v)*axis,axis=-1),np.sum(u*v,axis=-1))

    for item in panel:
        gid=item['group_id'];seq=item['sequence'];file=root/'coordinates'/(gid+'.npz')
        saved_info=next(r for r in report['structures'] if r['group_id']==gid)
        assert digest(file)==saved_info['coordinates_sha256']
        arrays=np.load(file);raw_bytes=archive.extractfile('selected_gt/'+gid+'/gt.npz').read()
        assert hashlib.sha256(raw_bytes).hexdigest()==item['gt_sha256']
        data=np.load(io.BytesIO(raw_bytes))
        # Explicit same archived atom37 identity contract, not primary loader.
        atom37='N CA C CB O CG CG1 CG2 OG OG1 SG CD CD1 CD2 ND1 ND2 OD1 OD2 SD CE CE1 CE2 CE3 NE NE1 NE2 OE1 OE2 CH2 NH1 NH2 OH CZ CZ2 CZ3 NZ OXT'.split()
        total=0;missing=0
        for aa,t in templates.items():
            names=t['atom_names'];ix=[atom37.index(n) for n in names]
            eligible=[i for i in range(1,len(seq)-1) if seq[i]==aa]
            valid=[i for i in eligible if data['atom37_mask'][i,ix].all()]
            missing+=len(eligible)-len(valid)
            if not valid:continue
            total+=len(valid)
            np.testing.assert_array_equal(arrays[aa+'_residues'],np.array(valid)+1)
            gt=data['atom37_positions'][np.array(valid)[:,None],ix].astype(float)
            np.testing.assert_array_equal(gt,arrays[aa+'_gt'])
            lookup={n:i for i,n in enumerate(names)};n,ca,c=[lookup[k] for k in ['N','CA','C']]
            raw_frame=frame(gt,n,ca,c);variants={t['ccd']+':'+','.join(names):dict(atom_names=names,bonds=t['bonds'])}
            results={}
            for label in ['native','ideal']:
                reference=np.array(t[label]);model=ArticulatedOutput(reference,names,np.ones(len(names),dtype=int),aa,variants)
                group=model.groups[0]  # read topology/probe metadata only; never execute torch forward
                local=(reference-reference[ca])@frame(reference,n,ca,c)
                x=np.broadcast_to(local,gt.shape).copy()
                for rotation,probe in zip(group.rotations,group.probes,strict=True):
                    angle=phase(gt,probe)-phase(x,probe)
                    origin=x[:,rotation.parent:rotation.parent+1];axis=x[:,rotation.child:rotation.child+1]-origin
                    axis/=np.linalg.norm(axis,axis=-1,keepdims=True);relative=x-origin
                    co=np.cos(angle)[:,None,None];si=np.sin(angle)[:,None,None]
                    transformed=origin+relative*co+np.cross(axis,relative)*si+np.sum(relative*axis,axis=-1,keepdims=True)*axis*(1-co)
                    x[:,rotation.moving]=transformed[:,rotation.moving]
                y=x@raw_frame.swapaxes(-1,-2)+gt[:,ca:ca+1]
                replay_max=max(replay_max,float(np.max(np.abs(y-arrays[aa+'_'+label]))))
                for a,b,_ in t['bonds']:
                    target=np.linalg.norm(reference[a]-reference[b]);current=np.linalg.norm(y[:,a]-y[:,b],axis=-1)
                    bond_max=max(bond_max,float(np.max(abs(current-target))))
                squared=((y-gt)**2).sum(-1);bone=np.isin(names,['N','CA','C','O'])
                results[label]=dict(heavy=np.sqrt(squared.mean(-1)),backbone=np.sqrt(squared[:,bone].mean(-1)),
                    sidechain=np.sqrt(squared[:,~bone].mean(-1)) if (~bone).any() else None)
            for j,i in enumerate(valid):
                row=row_index[(gid,i+1)];assert row['role']==item['role'] and row['amino_acid']==aa
                out=dict(group_id=gid,role=item['role'])
                for label in results:
                    for name,values in results[label].items():
                        value=None if values is None else float(values[j]);key=label+'_'+name
                        if value is None:assert row[key]==''
                        else:metric_max=max(metric_max,abs(value-float(row[key])))
                        out[key]=value
                measured.append(out)
        assert total==saved_info['complete_residues'] and missing==saved_info['missing_sidechain_residues']
        exclusions.append(dict(group_id=gid,complete=total,missing=missing))
    archive.close()
    assert len(measured)==len(row_index) and replay_max<1e-9 and metric_max<1e-10 and bond_max<1e-10
    for role in ['calibration','held_out']:
        ids=[r['group_id'] for r in panel if r['role']==role]
        for metric in ['heavy','backbone','sidechain']:
            means={}
            for label in ['native','ideal']:
                key=label+'_'+metric
                means[label]=np.array([np.mean([r[key] for r in measured if r['group_id']==gid and r[key] is not None]) for gid in ids])
            target=report['summary'][role]['metrics'][metric]
            for label in means:assert abs(float(means[label].mean())-target[label+'_mean'])<1e-10
            delta=means['ideal']-means['native'];rng=np.random.default_rng(9302032)
            boot=[delta[rng.integers(0,32,32)].mean() for _ in range(2000)]
            np.testing.assert_allclose(np.quantile(boot,[.025,.975]),target['bootstrap95'],rtol=0,atol=1e-10)
            assert int((delta<0).sum())==target['improved_proteins']
    result=dict(complete=True,templates=20,structures=64,residues=len(measured),projection_instances=2*len(measured),
        numpy_replay_max_abs=replay_max,metric_max_abs=metric_max,bond_invariance_max_abs=bond_max,
        roles_and_missing_atom_counts_verified=True,projection_bootstraps_verified=6,
        report_sha256=digest(root/'report.json'),script_sha256=digest(__file__),
        scope='NumPy coordinate operations; shared fixed topology/probe metadata, no independent graph-parser certification')
    assert not (root/'audit.json').exists()
    (root/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['root','source','templates']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();verify_ccd_template_projection(a.root,a.source,a.templates)
