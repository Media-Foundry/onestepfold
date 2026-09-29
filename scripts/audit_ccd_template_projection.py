#!/usr/bin/env python3
"""Compare whole native/CCD-ideal local references on frozen observed residues."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile

import numpy as np
import torch

from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.backbone_reference_calibration import measure_backbone_local_geometry, BACKBONE_METRICS
from onestepfold.data.gt_materializer import ATOM37_INDEX


def audit_ccd_template_projection(source, templates_path, previous_reference, output):
    torch.set_num_threads(1)
    assert not output.exists();output.mkdir(parents=True);(output/'coordinates').mkdir()
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    write=lambda name,x:(output/name).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
    code=Path(__file__).resolve().parents[1]
    paths=[Path(__file__),templates_path,previous_reference,
        code/'docs/mini_ccd_ideal_template_audit_v1.md',code/'src/fastglycan/articulated_output.py',
        code/'src/fastglycan/articulated_reference.py',code/'src/fastglycan/backbone_reference_calibration.py',
        code/'src/onestepfold/data/gt_materializer.py',source/'measurement/source_evidence.tar.gz',
        source/'measurement/source_evidence_manifest.json',source/'extension/selection.json']
    write('input_lock.json',dict(hashes={str(p.resolve()):sha(p) for p in paths},
        scope='GT oracle local representation only; no inference or solver'))
    document=json.loads(templates_path.read_text());templates=document['records']
    old=json.loads(previous_reference.read_text())
    for p,h in old['hashes'].items():assert document['hashes'][p]==h
    adapters={};geometry={};checks=[]
    rng=np.random.default_rng(9302032);q,_=np.linalg.qr(rng.normal(size=(3,3)));q[:,-1]*=np.linalg.det(q)
    for aa,t in templates.items():
        assert sha(templates_path.parent/(t['ccd']+'.cif'))==t['component_sha256']
        names=t['atom_names'];lookup={n:i for i,n in enumerate(names)}
        variants={t['ccd']+':'+','.join(names):dict(atom_names=names,bonds=t['bonds'])}
        metrics={};models={};volumes={};row=dict(amino_acid=aa,atoms=len(names),replays={},equivariance={},stereo={})
        for label in ['native','ideal']:
            x=np.array(t[label]);model=ArticulatedOutput(x,names,np.ones(len(x),dtype=int),aa,variants).double()
            with torch.no_grad():
                native_replay=model(torch.tensor(x));rotated=model(torch.tensor(x@q+3))
            error=float(np.max(np.abs(native_replay['coordinate'].numpy()-x)))
            equiv=float(np.max(np.abs(rotated['coordinate'].numpy()-(x@q+3))))
            assert error<1e-10 and equiv<1e-10 and not int(native_replay['fallback_counts'].sum())
            row['replays'][label]=error;row['equivariance'][label]=equiv;models[label]=model
            metrics[label]={k:float(v) for k,v in measure_backbone_local_geometry(x[[lookup[n] for n in ['N','CA','C','O']]]).items()}
            centres=[]
            if aa!='G':centres.append(('CA',['CA','N','C','CB']))
            if aa in 'IT':centres.append(('CB',['CB','CA','CG1' if aa=='I' else 'OG1','CG2']))
            volumes[label]={}
            for name,n in centres:
                c,a,b,d=x[[lookup[k] for k in n]]
                volumes[label][name]=float(np.dot(np.cross(a-c,b-c),d-c))
        for name,value in volumes['native'].items():
            opposite=volumes['ideal'][name]
            row['stereo'][name]=dict(native=value,ideal=opposite,same_sign=value*opposite>0,ccd=t['stereo'][name])
            assert value*opposite>0
        row['passed']=True;checks.append(row);adapters[aa]=models;geometry[aa]=metrics
        old_n=old['records'][aa]['coordinates']
        np.testing.assert_array_equal(np.array(t['native'])[[lookup[n] for n in ['N','CA','C','O']]],old_n)
    write('template_checks.json',dict(complete=True,checks=checks,backbone_geometry=geometry))
    manifest=json.loads((source/'measurement/source_evidence_manifest.json').read_text())
    assert sha(source/'measurement/source_evidence.tar.gz')==manifest['archive_sha256']
    with tarfile.open(source/'measurement/source_evidence.tar.gz') as archive:
        blobs={m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    assert set(blobs)==set(manifest['files'])
    for n,b in blobs.items():assert hashlib.sha256(b).hexdigest()==manifest['files'][n]['sha256']
    assert blobs['extension/selection.json']==(source/'extension/selection.json').read_bytes()
    panel=json.loads(blobs['extension/selection.json']);assert len(panel)==64
    residues=[];scalar_errors=[];structures=[]
    for item in panel:
        seq=item['sequence'];gid=item['group_id'];prefix='selected_gt/'+gid+'/'
        assert hashlib.sha256(blobs[prefix+'gt.npz']).hexdigest()==item['gt_sha256']
        data=np.load(io.BytesIO(blobs[prefix+'gt.npz']))
        assert data['residue_mask'].all()
        bb=[ATOM37_INDEX[n] for n in ['N','CA','C','O']]
        assert data['atom37_mask'][:,bb].all()
        values=measure_backbone_local_geometry(data['atom37_positions'][1:-1,bb].astype(float))
        for i,aa in enumerate(seq[1:-1],1):
            for label in ['native','ideal']:
                scalar_errors.append(dict(group_id=gid,pdb_id=item['pdb_id'],role=item['role'],residue=i+1,
                    amino_acid=aa,reference=label,**{k:geometry[aa][label][k]-float(v[i-1]) for k,v in values.items()}))
        arrays={};missing=0;count=0
        for aa,t in templates.items():
            atom_ids=[ATOM37_INDEX[n] for n in t['atom_names']]
            indices=[i for i in range(1,len(seq)-1) if seq[i]==aa]
            complete=[i for i in indices if data['atom37_mask'][i,atom_ids].all()]
            missing+=len(indices)-len(complete)
            if not complete:continue
            x=data['atom37_positions'][np.array(complete)[:,None],atom_ids].astype(float)
            arrays[aa+'_gt']=x;arrays[aa+'_residues']=np.array(complete)+1
            backbone=np.isin(t['atom_names'],['N','CA','C','O']);side=~backbone
            outputs={}
            for label in ['native','ideal']:
                with torch.no_grad():answer=adapters[aa][label](torch.tensor(x))
                assert not int(answer['fallback_counts'].sum())
                y=answer['coordinate'].numpy();outputs[label]=y;arrays[aa+'_'+label]=y
                ca=t['atom_names'].index('CA');assert np.max(np.abs(y[:,ca]-x[:,ca]))<1e-10
            for j,i in enumerate(complete):
                row=dict(group_id=gid,pdb_id=item['pdb_id'],role=item['role'],residue=i+1,amino_acid=aa,atoms=len(atom_ids))
                for label,y in outputs.items():
                    squared=((y[j]-x[j])**2).sum(-1)
                    row[label+'_heavy']=float(np.sqrt(squared.mean()))
                    row[label+'_backbone']=float(np.sqrt(squared[backbone].mean()))
                    row[label+'_sidechain']=float(np.sqrt(squared[side].mean())) if side.any() else None
                residues.append(row);count+=1
        assert count+missing==len(seq)-2
        file=output/'coordinates'/(gid+'.npz');np.savez_compressed(file,**arrays)
        structures.append(dict(group_id=gid,pdb_id=item['pdb_id'],role=item['role'],internal_residues=len(seq)-2,
            complete_residues=count,missing_sidechain_residues=missing,coordinates_sha256=sha(file)))
    per_protein=[]
    for item in structures:
        row=dict(item)
        local=[r for r in residues if r['group_id']==item['group_id']]
        scalar=[r for r in scalar_errors if r['group_id']==item['group_id']]
        for label in ['native','ideal']:
            for metric in ['heavy','backbone','sidechain']:
                values=[r[label+'_'+metric] for r in local if r[label+'_'+metric] is not None]
                row[label+'_'+metric]=float(np.mean(values))
            for metric in BACKBONE_METRICS:
                row[label+'_'+metric+'_mae']=float(np.mean([abs(r[metric]) for r in scalar if r['reference']==label]))
        per_protein.append(row)
    summary={}
    for role in ['calibration','held_out']:
        selected=[r for r in per_protein if r['role']==role];assert len(selected)==32
        summaries={}
        for metric in ['heavy','backbone','sidechain']+[k+'_mae' for k in BACKBONE_METRICS]:
            native=np.array([r['native_'+metric] for r in selected]);ideal=np.array([r['ideal_'+metric] for r in selected]);delta=ideal-native
            rng=np.random.default_rng(9302032);draw=delta[rng.integers(0,32,size=(2000,32))].mean(axis=1)
            summaries[metric]=dict(native_mean=float(native.mean()),ideal_mean=float(ideal.mean()),
                delta=float(delta.mean()),bootstrap95=np.quantile(draw,[.025,.975]).tolist(),improved_proteins=int((delta<0).sum()))
        summary[role]=dict(proteins=32,internal_residues=sum(r['internal_residues'] for r in selected),
            complete_residues=sum(r['complete_residues'] for r in selected),
            missing_sidechain_residues=sum(r['missing_sidechain_residues'] for r in selected),metrics=summaries)
    by_type={}
    for aa in templates:
        selected=[r for r in residues if r['role']=='held_out' and r['amino_acid']==aa]
        by_type[aa]=dict(residues=len(selected),proteins=len({r['group_id'] for r in selected}),
            native_heavy=float(np.mean([r['native_heavy'] for r in selected])),
            ideal_heavy=float(np.mean([r['ideal_heavy'] for r in selected])))
    for name,records in [('residues.csv',residues),('per_protein.csv',per_protein),('backbone_errors.csv',scalar_errors)]:
        with (output/name).open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(records[0]),lineterminator='\n');writer.writeheader();writer.writerows(records)
    held=summary['held_out']['metrics']
    result=dict(complete=True,structures=structures,summary=summary,held_by_amino_acid=by_type,
        candidate=all(r['passed'] for r in checks) and held['heavy']['delta']<0 and held['backbone']['delta']<0,
        template_checks_sha256=sha(output/'template_checks.json'),input_lock_sha256=sha(output/'input_lock.json'),
        output_sha256={n:sha(output/n) for n in ['residues.csv','per_protein.csv','backbone_errors.csv']},
        scope='experimental-coordinate oracle local projection; no protein inference, whole-chain correction or design claim')
    write('report.json',result)
    print(json.dumps(dict(candidate=result['candidate'],summary=summary),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['source','templates','previous-reference','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();audit_ccd_template_projection(a.source,a.templates,a.previous_reference,a.output)
