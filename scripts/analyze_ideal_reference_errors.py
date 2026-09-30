#!/usr/bin/env python3
"""Hash-bound, additive analysis of existing whole-ideal C4 prediction artifacts."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile

import numpy as np

from fastglycan.connection_audit import measure_connections
from fastglycan.lddt_attribution import lddt_attribution
from fastglycan.paired_teacher_protocol import sha256, write_json


def analyze_ideal_reference_errors(source, output):
    output.mkdir(exist_ok=False,parents=True);(output/'atoms').mkdir()
    manifest=json.loads((source/'artifact_manifest.json').read_text())
    assert sha256(source/'artifacts.tar.gz')==manifest['archive_sha256']
    with tarfile.open(source/'artifacts.tar.gz') as archive:
        files={x.name:archive.extractfile(x).read() for x in archive if x.isfile()}
    assert set(files)==set(manifest['files'])
    assert all(hashlib.sha256(v).hexdigest()==manifest['files'][k] for k,v in files.items())
    report=json.loads((source/'report.json').read_text());audit=json.loads((source/'audit.json').read_text())
    assert audit['report_sha256']==sha256(source/'report.json') and audit['verified']==28 and audit['paired']==14
    assert report['lock_sha256']==sha256(source/'lock.json')
    assert json.loads((source/'pipeline_exit.json').read_text())['returncode']==0
    selection=json.loads(files['source/selection.json']);rows=[];residue_rows=[];case_rows=[];skipped=[]
    contrasts=[('native_local','raw'),('native_final','raw'),('ideal_local','raw'),('ideal_final','raw'),
               ('native_final','native_local'),('ideal_final','ideal_local'),('ideal_local','native_local'),('ideal_final','native_final')]
    max_replay=0.;max_partition=0.
    for index in range(0,32,2):
        left,right=report['rows'][index:index+2];item=selection[index//4]
        if not left['success']:
            assert left['not_run'] and right['not_run'];skipped.append(dict(pdb_id=item['pdb_id'],seed=left['seed'],source_failure=left['source_failure']));continue
        datasets=[]
        for row in [left,right]:
            content=files[f'cases/{row["index"]:02d}/coordinates.npz']
            assert hashlib.sha256(content).hexdigest()==row['coordinates_sha256']
            datasets.append(dict(np.load(io.BytesIO(content))))
        native,ideal=datasets;names=native['atom_names'];res=native['residue_ids'];gt=native['target'];seq=item['sequence']
        assert all(np.array_equal(native[k],ideal[k]) for k in ['raw','target','atom_names','residue_ids'])
        coordinates=dict(raw=native['raw'],native_local=native['local'],native_final=native['final'],ideal_local=ideal['local'],ideal_final=ideal['final'])
        anchors=np.array([[int(np.flatnonzero((res==r)&(names==n))[0]) for n in ['N','CA','C','O']] for r in range(1,len(seq)+1)])
        raw_con=measure_connections(coordinates['raw'],anchors,seq);gt_con=measure_connections(gt,anchors,seq)
        active=np.any(np.stack([np.abs(x) for x in raw_con['residuals'].values()])>np.array(left['connection_onsets']),axis=0)
        mismatch=raw_con['nearest_omega_sign']!=gt_con['nearest_omega_sign']
        def neighbourhood(edges):
            near=set()
            for j in np.flatnonzero(edges):near.update(range(max(1,j),min(len(seq),j+3)+1))
            return np.isin(res,list(near))
        bone=np.isin(names,['N','CA','C','O'])
        centre_groups=dict(atom_class=np.where(bone,names,np.where(names=='OXT','OXT','sidechain')),
            amino_acid=np.array([seq[r-1] for r in res]),
            position=np.where((res==1)|(res==len(seq)),'terminal','interior'),
            raw_connection_active=np.where(neighbourhood(active),'near','other'),
            raw_branch_mismatch=np.where(neighbourhood(mismatch),'near','other'))
        values={name:lddt_attribution(x,gt,res) for name,x in coordinates.items()}
        raw=values['raw'];a,b=raw['pairs'].T;sep=np.abs(res[a]-res[b])
        pair_groups=dict(pair_type=np.where(bone[a]&bone[b],'backbone_backbone',np.where(bone[a]|bone[b],'backbone_other','other_other')),
            separation=np.where(sep==1,'1',np.where(sep<=4,'2-4','5+')))
        case=dict(pdb_id=item['pdb_id'],group_id=item['group_id'],seed=left['seed'],source_slot=index//4,
                  atoms=len(res),valid_atoms=int(raw['valid'].sum()),pairs=len(a),raw_active_edges=int(active.sum()),raw_branch_mismatches=int(mismatch.sum()))
        for stage,v in values.items():
            origin=left if stage.startswith('native') or stage=='raw' else right
            label='raw' if stage=='raw' else stage.split('_')[1]
            expected=origin['metrics'][label]['all_atom_lddt'];max_replay=max(max_replay,abs(v['score']-expected));assert abs(v['score']-expected)<1e-12
            case[stage]=v['score']
            saved=dict(per_atom=v['per_atom'],valid=v['valid'],counts=v['counts'],names=names,residue_ids=res)
            np.savez_compressed(output/'atoms'/f'{index//2:02d}_{stage}.npz',**saved)
            for space,groups in [('atom',centre_groups),('pair',pair_groups)]:
                for partition,labels in groups.items():
                    subtotal=0.
                    for group in np.unique(labels):
                        mask=labels==group
                        if space=='atom':
                            mask=mask&v['valid'];weight=mask.sum()/v['valid'].sum();c=v['atom_contribution'][mask].sum()
                        else:weight=v['pair_weights'][mask].sum();c=v['pair_contribution'][mask].sum()
                        subtotal+=c
                        rows.append(dict(**{k:case[k] for k in ['pdb_id','seed','source_slot']},stage=stage,space=space,partition=partition,group=str(group),
                                         count=int(mask.sum()),support_weight=float(weight),contribution=float(c),conditional_score=float(c/weight) if weight>0 else None))
                    max_partition=max(max_partition,abs(subtotal-v['score']))
            for k,t in enumerate([.5,1.,2.,4.]):
                rows.append(dict(**{n:case[n] for n in ['pdb_id','seed','source_slot']},stage=stage,space='pair',partition='threshold',group=str(t),
                                 count=len(a),support_weight=.25,contribution=float(v['threshold_contribution'][:,k].sum()),conditional_score=float(v['threshold_contribution'][:,k].sum()*4)))
        case_rows.append(case)
        for r,aa in enumerate(seq,1):
            mask=(res==r)&raw['valid'];record=dict(pdb_id=item['pdb_id'],seed=left['seed'],residue=r,amino_acid=aa,atoms=int(mask.sum()),
                near_raw_active=bool(neighbourhood(active)[res==r].any()),near_raw_branch_mismatch=bool(neighbourhood(mismatch)[res==r].any()))
            for stage,v in values.items():record[stage]=float(v['per_atom'][mask].mean());record[stage+'_contribution']=float(v['atom_contribution'][mask].sum())
            residue_rows.append(record)
    assert len(case_rows)==14 and len(skipped)==2 and max_partition<1e-12
    lookup={(r['pdb_id'],r['seed'],r['stage'],r['space'],r['partition'],r['group']):r for r in rows}
    partitions=sorted(set((r['space'],r['partition'],r['group']) for r in rows));pdbs=sorted(set(r['pdb_id'] for r in case_rows))
    delta_rows=[]
    for new,old in contrasts:
        for space,partition,group in partitions:
            for pdb in pdbs:
                deltas=[];supports=[];counts=[]
                for seed in [12345,54321]:
                    x=lookup.get((pdb,seed,new,space,partition,group));y=lookup.get((pdb,seed,old,space,partition,group))
                    assert (x is None)==(y is None)
                    deltas.append(x['contribution']-y['contribution'] if x else 0.)
                    supports.append(x['support_weight'] if x else 0.);counts.append(x['count'] if x else 0)
                delta_rows.append(dict(contrast=new+'-'+old,pdb_id=pdb,space=space,partition=partition,group=group,delta_contribution=float(np.mean(deltas)),support_weight=float(np.mean(supports)),count=float(np.mean(counts))))
    summary=[]
    for new,old in contrasts:
        for space,partition,group in partitions:
            selected=[r for r in delta_rows if r['contrast']==new+'-'+old and (r['space'],r['partition'],r['group'])==(space,partition,group)]
            assert len(selected)==7
            summary.append(dict(contrast=new+'-'+old,space=space,partition=partition,group=group,
                delta_contribution=float(np.mean([r['delta_contribution'] for r in selected])),
                support_weight=float(np.mean([r['support_weight'] for r in selected])),
                proteins_with_support=sum(r['count']>0 for r in selected)))
    for name,entries in [('partitions',rows),('residues',residue_rows),('cases',case_rows),('protein_partitions',delta_rows),('summary',summary)]:
        with (output/(name+'.csv')).open('w',newline='') as out:
            w=csv.DictWriter(out,fieldnames=list(entries[0]),lineterminator='\n');w.writeheader();w.writerows(entries)
    totals={new+'-'+old:float(np.mean([c[new]-c[old] for c in case_rows])) for new,old in contrasts}
    for contrast,total in totals.items():
        for space,partition in sorted(set((r['space'],r['partition']) for r in summary)):
            found=sum(r['delta_contribution'] for r in summary if r['contrast']==contrast and r['space']==space and r['partition']==partition)
            assert abs(total-found)<1e-12
    hashes={str(p):sha256(p) for p in [source/n for n in ['artifact_manifest.json','artifacts.tar.gz','report.json','audit.json','lock.json','pipeline_exit.json']]+[Path(__file__),Path('src/fastglycan/lddt_attribution.py'),Path('docs/mini_ideal_reference_error_partition_v1.md')]}
    write_json(output/'report.json',dict(complete=True,source=str(source),hashes=hashes,cases=14,proteins=7,stages=5,
        skipped=skipped,max_source_score_error=max_replay,max_partition_error=max_partition,totals=totals,
        summary=summary,scope='observational additive partitions; fixed original scores; no objective-term causal attribution'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();analyze_ideal_reference_errors(a.source,a.output)
