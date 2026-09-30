#!/usr/bin/env python3
"""Independent dense directed-pair recomputation of saved additive partitions."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile

import numpy as np
from scipy.spatial.distance import cdist

from fastglycan.connection_audit import measure_connections
from fastglycan.paired_teacher_protocol import sha256, write_json


def verify_ideal_reference_errors(root):
    result=json.loads((root/'report.json').read_text());source=Path(result['source'])
    for p,h in result['hashes'].items():assert sha256(Path(p))==h
    source_report=json.loads((source/'report.json').read_text())
    with tarfile.open(source/'artifacts.tar.gz') as tar:
        files={m.name:tar.extractfile(m).read() for m in tar if m.isfile()}
    selection=json.loads(files['source/selection.json'])
    manifest=json.loads((source/'artifact_manifest.json').read_text())
    for name,b in files.items():assert hashlib.sha256(b).hexdigest()==manifest['files'][name]
    rows=list(csv.DictReader((root/'partitions.csv').open()))
    max_atom=0.;max_partition=0.;checked=0;matrix_count=0
    case_scores={}
    for index in range(0,32,2):
        left,right=source_report['rows'][index:index+2]
        if not left['success']:continue
        old=dict(np.load(io.BytesIO(files[f'cases/{index:02d}/coordinates.npz'])))
        new=dict(np.load(io.BytesIO(files[f'cases/{index+1:02d}/coordinates.npz'])))
        names=old['atom_names'];res=old['residue_ids'];seq=selection[index//4]['sequence']
        target=cdist(old['target'],old['target'])
        valid=(res[:,None]!=res[None,:])&(target<15);degree=valid.sum(1);keep=degree>0
        factor=np.divide(valid,degree[:,None],out=np.zeros_like(target),where=degree[:,None]>0)/keep.sum()
        bone=np.isin(names,['N','CA','C','O']);sep=np.abs(res[:,None]-res[None,:])
        anchors=np.array([[np.flatnonzero((res==r)&(names==n))[0] for n in ['N','CA','C','O']] for r in range(1,len(seq)+1)])
        raw=measure_connections(old['raw'],anchors,seq);gt=measure_connections(old['target'],anchors,seq)
        edge_sets=dict(raw_connection_active=np.flatnonzero(np.any(np.stack([np.abs(v) for v in raw['residuals'].values()])>np.asarray(left['connection_onsets']),axis=0)),raw_branch_mismatch=np.flatnonzero(raw['nearest_omega_sign']!=gt['nearest_omega_sign']))
        masks={}
        for key,edges in edge_sets.items():
            near=np.zeros(len(res),bool)
            for j in edges:near|=(res>=j)&(res<=j+3)
            masks[key]=near
        coords=dict(raw=old['raw'],native_local=old['local'],native_final=old['final'],ideal_local=new['local'],ideal_final=new['final'])
        for stage,x in coords.items():
            error=np.abs(cdist(x,x)-target)
            per_threshold=np.stack([(error<t).astype(float)*factor/4 for t in [.5,1.,2.,4.]])
            contribution=per_threshold.sum(0);per=contribution.sum(1)*keep.sum()
            saved=dict(np.load(root/'atoms'/f'{index//2:02d}_{stage}.npz'))
            assert np.array_equal(saved['counts'],degree) and np.array_equal(saved['valid'],keep)
            max_atom=max(max_atom,float(np.max(np.abs(per-saved['per_atom']))));matrix_count+=1
            case_scores[(left['pdb_id'],left['seed'],stage)]=float(contribution.sum())
            records=[r for r in rows if r['pdb_id']==left['pdb_id'] and int(r['seed'])==left['seed'] and r['stage']==stage]
            for row in records:
                p,g=row['partition'],row['group']
                if row['space']=='atom':
                    if p=='atom_class':mask=(names==g) if g!='sidechain' else ~bone&(names!='OXT')
                    elif p=='amino_acid':mask=np.array([seq[r-1]==g for r in res])
                    elif p=='position':mask=((res==1)|(res==len(seq))) if g=='terminal' else ((res>1)&(res<len(seq)))
                    else:mask=masks[p] if g=='near' else ~masks[p]
                    mask &= keep;score=contribution[mask].sum();weight=mask.sum()/keep.sum();count=mask.sum()
                elif p=='threshold':
                    k=[.5,1.,2.,4.].index(float(g));score=per_threshold[k].sum();weight=.25;count=valid.sum()//2
                else:
                    if p=='pair_type':
                        mask=(bone[:,None]&bone[None,:]) if g=='backbone_backbone' else (~bone[:,None]&~bone[None,:]) if g=='other_other' else (bone[:,None]!=bone[None,:])
                    else:mask=(sep==1) if g=='1' else ((sep>=2)&(sep<=4)) if g=='2-4' else (sep>=5)
                    score=contribution[mask].sum();weight=factor[mask].sum();count=(valid&mask).sum()//2
                max_partition=max(max_partition,abs(float(score)-float(row['contribution'])),abs(float(weight)-float(row['support_weight'])))
                assert int(count)==int(row['count'])
                if weight:assert abs(float(score/weight)-float(row['conditional_score']))<1e-12
                checked+=1
    assert matrix_count==70 and max_atom<1e-12 and max_partition<1e-12
    # Check CSV aggregations and totals independently from the per-case rows.
    summary=list(csv.DictReader((root/'summary.csv').open()))
    for entry in summary:
        new,old=entry['contrast'].split('-');diff=[]
        for pdb in sorted(set(k[0] for k in case_scores)):
            seed_values=[]
            for seed in [12345,54321]:
                def lookup(stage):
                    candidates=[r for r in rows if r['pdb_id']==pdb and int(r['seed'])==seed and r['stage']==stage and all(r[k]==entry[k] for k in ['space','partition','group'])]
                    assert len(candidates)<=1
                    return float(candidates[0]['contribution']) if candidates else 0.
                seed_values.append(lookup(new)-lookup(old))
            diff.append(np.mean(seed_values))
        assert abs(np.mean(diff)-float(entry['delta_contribution']))<1e-12
    write_json(root/'audit.json',dict(complete=True,report_sha256=sha256(root/'report.json'),script_sha256=sha256(Path(__file__)),
        atom_vectors_verified=matrix_count,partition_rows_verified=checked,summary_rows_verified=len(summary),
        max_atom_error=max_atom,max_partition_error=max_partition,
        scope='independent dense directed-pair arithmetic; shared source chemistry and connection-measure helper'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    verify_ideal_reference_errors(p.parse_args().root)
