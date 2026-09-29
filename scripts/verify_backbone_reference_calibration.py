#!/usr/bin/env python3
"""Independent scalar/corner reconstruction without calibration/span modules."""
import argparse
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import tarfile

import numpy as np


def verify_backbone_reference_calibration(root, source):
    digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=json.loads((root/'report.json').read_text())
    fit=json.loads((root/'fitted_backbone_reference.json').read_text())
    for path,value in json.loads((root/'input_lock.json').read_text())['hashes'].items():
        assert digest(path)==value,path
    for path,value in report['output_sha256'].items():assert digest(root/path)==value
    assert digest(root/'fitted_backbone_reference.json')==report['fitted_sha256']
    manifest=json.loads((source/'measurement/source_evidence_manifest.json').read_text())
    assert digest(source/'measurement/source_evidence.tar.gz')==manifest['archive_sha256']
    with tarfile.open(source/'measurement/source_evidence.tar.gz') as archive:
        data={m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    for name,value in data.items():assert hashlib.sha256(value).hexdigest()==manifest['files'][name]['sha256']
    panel=json.loads(data['extension/selection.json'])
    rows=list(csv.DictReader((root/'residues.csv').open()))
    by_key={(r['group_id'],int(r['residue'])):r for r in rows};assert len(by_key)==len(rows)
    original=[];max_geometry_error=0.;max_span_error=0.;corners=0
    span_rows=list(csv.DictReader((root/'spans.csv').open()))
    spans={(r['group_id'],r['variant'],int(r['left_residue'])):r for r in span_rows}
    assert len(spans)==len(span_rows)
    metrics=['n_ca','ca_c','c_o','n_ca_c_degrees','ca_c_o_degrees']
    for item in panel:
        prefix='selected_gt/'+item['group_id']+'/'
        assert hashlib.sha256(data[prefix+'gt.npz']).hexdigest()==item['gt_sha256']
        z=np.load(io.BytesIO(data[prefix+'gt.npz']))
        # Explicit frozen atom37 schema indices, independent of primary import.
        assert z['residue_mask'].all() and z['atom37_mask'][:,[0,1,2,4]].all()
        x=z['atom37_positions'][:,[0,1,2,4]].astype(float);seq=item['sequence']
        for i,p in enumerate(x):
            values=[float(np.sqrt(np.sum((p[a]-p[b])**2))) for a,b in [(0,1),(1,2),(2,3)]]
            for a,b,c in [(0,1,2),(1,2,3)]:
                u,v=p[a]-p[b],p[c]-p[b]
                values.append(float(np.degrees(np.arctan2(np.linalg.norm(np.cross(u,v)),np.dot(u,v)))))
            saved=by_key[(item['group_id'],i+1)]
            assert saved['role']==item['role'] and saved['amino_acid']==seq[i]
            assert (saved['terminal']=='True')==(i in [0,len(seq)-1])
            max_geometry_error=max(max_geometry_error,max(abs(float(saved[k])-v) for k,v in zip(metrics,values)))
            original.append(dict(group_id=item['group_id'],role=item['role'],aa=seq[i],
                terminal=i in [0,len(seq)-1],**dict(zip(metrics,values))))
        if item['role']!='held_out':continue
        for i in range(len(seq)-1):
            points=np.stack([x[i,1],x[i,2],x[i+1,0],x[i+1,1]])
            axis=points[2]-points[1];axis/=np.linalg.norm(axis)
            u=points[0]-points[1];v=points[3]-points[2]
            u-=np.dot(u,axis)*axis;v-=np.dot(v,axis)*axis
            sign=1 if np.dot(u,v)>0 else -1
            span=np.linalg.norm(points[3]-points[0])
            for label in ['native_reference','calibration_median']:
                lookup=fit['reference_values'] if label=='native_reference' else {
                    aa:{k:value['median'] for k,value in f['metrics'].items()}
                    for aa,f in fit['parameters'].items() if f['supported']}
                if seq[i] not in lookup or seq[i+1] not in lookup:continue
                a=lookup[seq[i]]['ca_c'];c=lookup[seq[i+1]]['n_ca'];b0=1.341 if seq[i+1]=='P' else 1.329
                bounds=[(b0-.030001,b0+.030001),(-.4473-.040001,-.4473+.040001),
                    (-.5203-.040001,-.5203+.040001),
                    (1-.100001**2/2,1) if sign>0 else (-1,-1+.100001**2/2)]
                distances=[]
                for b,u,v,q in itertools.product(*bounds):
                    left=np.array([a*u,a*np.sqrt(1-u*u),0.])
                    right=np.array([b-c*v,c*np.sqrt(1-v*v)*q,c*np.sqrt(1-v*v)*np.sqrt(1-q*q)])
                    distances.append(np.linalg.norm(right-left));corners+=1
                gap=max(min(distances)-span,span-max(distances),0.)
                saved=spans[(item['group_id'],label,i+1)]
                max_span_error=max(max_span_error,abs(gap-float(saved['gap'])))
                assert (gap>1e-6)==(saved['outside']=='True')
    assert len(original)==len(rows) and max_geometry_error<1e-10 and max_span_error<1e-10
    fit_checks=0
    for aa,estimate in fit['parameters'].items():
        subset=[r for r in original if r['role']=='calibration' and r['aa']==aa and not r['terminal']]
        assert len(subset)==estimate['residues'] and len({r['group_id'] for r in subset})==estimate['proteins']
        assert estimate['supported']==(len(subset)>=30 and len({r['group_id'] for r in subset})>=8)
        if not estimate['supported']:continue
        for metric in metrics:
            for name,q in [('q05',.05),('median',.5),('q95',.95)]:
                assert abs(np.quantile([r[metric] for r in subset],q)-estimate['metrics'][metric][name])<1e-10
                fit_checks+=1
    for metric in metrics:
        differences=[];baseline=[];candidate=[]
        for gid in sorted({r['group_id'] for r in original if r['role']=='held_out'}):
            subset=[r for r in original if r['group_id']==gid and not r['terminal'] and fit['parameters'][r['aa']]['supported']]
            b=np.mean([abs(fit['reference_values'][r['aa']][metric]-r[metric]) for r in subset])
            c=np.mean([abs(fit['parameters'][r['aa']]['metrics'][metric]['median']-r[metric]) for r in subset])
            baseline.append(b);candidate.append(c);differences.append(c-b)
        s=report['metrics'][metric];differences=np.array(differences)
        assert abs(np.mean(baseline)-s['equal_protein_reference_mae'])<1e-10
        assert abs(np.mean(candidate)-s['equal_protein_fitted_mae'])<1e-10
        assert abs(differences.mean()-s['paired_mae_change'])<1e-10
        rng=np.random.default_rng(9302030);means=[]
        for _ in range(2000):means.append(differences[rng.integers(0,len(differences),len(differences))].mean())
        np.testing.assert_allclose(np.quantile(means,[.025,.975]),s['bootstrap95'],rtol=0,atol=1e-10)
    for variant,s in report['span_necessary_conditions'].items():
        subset=[r for r in span_rows if r['variant']==variant and r['paired_supported']=='True']
        assert len(subset)==s['edges'] and sum(r['outside']=='True' for r in subset)==s['outside']
        assert len({r['group_id'] for r in subset if r['outside']=='True'})==s['proteins_with_violation']
    result=dict(complete=True,structures=len(panel),residues_verified=len(rows),
        fit_quantiles_verified=fit_checks,held_metric_bootstraps_verified=5,
        geometry_max_abs=max_geometry_error,span_max_abs=max_span_error,cartesian_corners=corners,
        report_sha256=digest(root/'report.json'),script_sha256=digest(__file__),
        scope='independent scalar/Cartesian reconstruction and split/statistics verification; not new raw-source remapping')
    assert not (root/'audit.json').exists()
    (root/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--source',type=Path,required=True)
    a=p.parse_args();verify_backbone_reference_calibration(a.root,a.source)
