#!/usr/bin/env python3
"""Additive saved-output quality and objective accounting, no new inference."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile

import numpy as np
import torch

from fastglycan.connection_audit import measure_connections, TOLERANCES
from fastglycan.lddt_attribution import lddt_attribution
from fastglycan.paired_teacher_protocol import sha256, write_json


def analyze_joint_tradeoffs(source, output):
    output.mkdir(parents=True, exist_ok=False)
    manifest=json.loads((source/'artifact_manifest.json').read_text())
    assert sha256(source/'artifacts.tar.gz')==manifest['archive_sha256']
    with tarfile.open(source/'artifacts.tar.gz') as tar:
        files={m.name:tar.extractfile(m).read() for m in tar if m.isfile()}
    assert set(files)==set(manifest['files'])
    assert all(hashlib.sha256(b).hexdigest()==manifest['files'][n] for n,b in files.items())
    report=json.loads((source/'report.json').read_text());audit=json.loads((source/'audit.json').read_text())
    assert audit['report_sha256']==sha256(source/'report.json') and audit['verified']==28 and audit['paired']==14
    assert report['lock_sha256']==sha256(source/'lock.json')
    assert json.loads((source/'pipeline_exit.json').read_text())['returncode']==0
    assert json.loads((source/'lock.json').read_text())['initialization_contract']=='calibrated_c4_sidechain_repulsion_start_v1'
    selection=json.loads(files['source/selection.json'])
    contrasts=[('start','local'),('warm_final','start'),('zero_final','local'),
               ('warm_final','zero_final'),('warm_final','raw'),('zero_final','raw')]
    rows=[];cases=[];objectives=[];skipped=[];max_score=0.;max_objective=0.
    for index in range(0,32,2):
        left,right=report['rows'][index:index+2];item=selection[index//4]
        if not left['success']:
            assert left['not_run'] and right['not_run'];skipped.append(dict(pdb_id=item['pdb_id'],seed=left['seed'],reason=left['source_failure']));continue
        data=[];qs=[]
        for row in [left,right]:
            for filename,key in [('coordinates.npz','coordinates_sha256'),('values.pt','values_sha256')]:
                assert hashlib.sha256(files[f'cases/{row["index"]:02d}/{filename}']).hexdigest()==row[key]
            data.append(dict(np.load(io.BytesIO(files[f'cases/{row["index"]:02d}/coordinates.npz']))))
            qs.append(torch.load(io.BytesIO(files[f'cases/{row["index"]:02d}/values.pt']),weights_only=True,map_location='cpu')['final'])
        old,new=data;names=old['atom_names'];res=old['residue_ids'];seq=item['sequence']
        for k in ['raw','local','target','output_reference','atom_names','residue_ids']:assert np.array_equal(old[k],new[k])
        coords=dict(raw=old['raw'],local=old['local'],start=new['start'],zero_final=old['final'],warm_final=new['final'])
        origin=dict(raw=(left,'raw'),local=(left,'local'),start=(right,'start'),zero_final=(left,'final'),warm_final=(right,'final'))
        base=dict(pdb_id=item['pdb_id'],seed=left['seed'],source_slot=index//4)
        for metric in ['aa','ca']:
            choose=np.ones(len(res),bool) if metric=='aa' else names=='CA'
            rn=res[choose];nn=names[choose];target=old['target'][choose];raw=old['raw'][choose]
            for stage,x in coords.items():
                value=lddt_attribution(x[choose],target,rn);a,b=value['pairs'].T
                expected=origin[stage][0]['metrics'][origin[stage][1]]['all_atom_lddt' if metric=='aa' else 'ca_lddt']
                max_score=max(max_score,abs(value['score']-expected));assert abs(value['score']-expected)<1e-12
                bone=np.isin(nn,['N','CA','C','O']);sep=np.abs(rn[a]-rn[b])
                kind=np.where(bone[a]&bone[b],'BB',np.where(bone[a]|bone[b],'BO','OO'))
                separation=np.where(sep==1,'1',np.where(sep<=4,'2-4','5+'))
                groups=dict(pair_type=kind,separation=separation,cross=np.char.add(np.char.add(kind,':'),separation))
                dist=np.linalg.norm(x[choose][a]-x[choose][b],axis=1)
                raw_error=np.abs(dist-np.linalg.norm(raw[a]-raw[b],axis=1));w=value['pair_weights']
                cases.append(dict(**base,metric=metric,stage=stage,score=value['score'],
                    gt_distance_mae=float(w@value['error']),raw_distance_mae=float(w@raw_error)))
                for partition,labels in groups.items():
                    subtotal=0.
                    for label in np.unique(labels):
                        mask=labels==label;contribution=float(value['pair_contribution'][mask].sum());subtotal+=contribution
                        rows.append(dict(**base,metric=metric,stage=stage,partition=partition,group=str(label),count=int(mask.sum()),
                            support=float(w[mask].sum()),score=contribution,
                            gt_distance_mae=float(w[mask]@value['error'][mask]),raw_distance_mae=float(w[mask]@raw_error[mask])))
                    assert abs(subtotal-value['score'])<1e-12
                for t,threshold in enumerate([.5,1.,2.,4.]):
                    rows.append(dict(**base,metric=metric,stage=stage,partition='threshold',group=str(threshold),count=len(a),
                        support=.25,score=float(value['threshold_contribution'][:,t].sum()),gt_distance_mae=None,raw_distance_mae=None))
        anchors=np.array([[np.flatnonzero((res==r)&(names==n))[0] for n in ['N','CA','C','O']] for r in range(1,len(seq)+1)])
        branch=measure_connections(old['raw'],anchors,seq)['nearest_omega_sign']
        for arm,d,q,row in zip(['zero','warm'],data,qs,[left,right],strict=True):
            q=[v.numpy() for v in q];x=d['final'];delta=((x-d['raw'])**2).sum(1)
            rot=np.concatenate([v[:,3:6] for v in q]);torsion=np.concatenate([v[:,6:].ravel() for v in q])
            parts=dict(anchor=float(delta.mean()),rotation=float(.1*(rot**2).sum(1).mean()),
                       torsion=float(.01*(1-np.cos(torsion)).mean()) if torsion.size else 0.)
            edges=measure_connections(x,anchors,seq,branch)['residuals']
            onsets=np.asarray(row['connection_onsets']);ct=0.
            for j,(term,tol) in enumerate(TOLERANCES.items()):
                value=float(100*np.maximum((np.abs(edges[term])-onsets[j])/(.5*tol),0).dot(np.maximum((np.abs(edges[term])-onsets[j])/(.5*tol),0))/len(edges[term]))
                parts['connection_'+term]=value;ct+=value
            history=row['history'][-1];assert history['rho']==100.
            assert abs(ct-100*history['terms']['connection'])<1e-8
            for key in ['repulsion','tail']:parts[key]=100*history['terms'][key]
            parts['budget']=100*(max(float(delta.mean())-4,0)**2+max(float(delta[names=='CA'].mean())-1,0)**2)
            value=sum(parts.values());expected=row['final_cross_objectives']['calibrated']
            max_objective=max(max_objective,abs(value-expected));assert abs(value-expected)<1e-8
            objectives.append(dict(**base,arm=arm,**parts,total=value))
    assert len(cases)==140 and len(objectives)==28 and len(skipped)==2
    proteins=sorted({r['pdb_id'] for r in cases});lookup={(r['pdb_id'],r['seed'],r['metric'],r['stage'],r['partition'],r['group']):r for r in rows}
    keys=sorted({(r['metric'],r['partition'],r['group']) for r in rows});deltas=[];summary=[]
    for new,old in contrasts:
        for metric,partition,group in keys:
            per=[]
            for pdb in proteins:
                entries=[]
                for seed in [12345,54321]:
                    a=lookup.get((pdb,seed,metric,new,partition,group));b=lookup.get((pdb,seed,metric,old,partition,group));assert (a is None)==(b is None)
                    entries.append({k:(a[k]-b[k] if a else 0.) for k in ['score','gt_distance_mae','raw_distance_mae'] if partition!='threshold' or k=='score'})
                record=dict(contrast=new+'-'+old,metric=metric,partition=partition,group=group,pdb_id=pdb,
                    **{k:float(np.mean([e[k] for e in entries])) for k in entries[0]})
                deltas.append(record);per.append(record)
            summary.append({k:v for k,v in per[0].items() if k not in ['pdb_id','score','gt_distance_mae','raw_distance_mae']}|
                {k:float(np.mean([p[k] for p in per])) for k in ['score','gt_distance_mae','raw_distance_mae'] if k in per[0]})
    for name,records in [('partitions',rows),('cases',cases),('objectives',objectives),('protein_contrasts',deltas),('summary',summary)]:
        with (output/(name+'.csv')).open('w',newline='') as out:
            fields=list(dict.fromkeys(k for r in records for k in r));w=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(records)
    hashes={str(p):sha256(p) for p in [source/n for n in ['artifact_manifest.json','artifacts.tar.gz','report.json','audit.json','lock.json','pipeline_exit.json']]+[Path(__file__),Path('src/fastglycan/lddt_attribution.py'),Path('docs/mini_joint_tradeoff_attribution_v1.md')]}
    write_json(output/'report.json',dict(complete=True,source=str(source),hashes=hashes,contrasts=contrasts,
        cases=14,proteins=7,stages=5,metrics=['aa','ca'],skipped=skipped,max_source_score_error=max_score,
        max_objective_error=max_objective,summary=summary,
        repulsion_scope='frozen terms reused from independently audited source; other objective terms recomputed',
        scope='descriptive attribution; no new inference, solving, GT-dependent selection or acceptance change'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();analyze_joint_tradeoffs(a.source,a.output)
