#!/usr/bin/env python3
"""Independent HSP parsing, greedy split reconstruction, GT/mask source audit."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
from fastglycan.paired_teacher_protocol import sha256, write_json
from onestepfold.data.gt_materializer import ATOM37_INDEX


def audit_adapter_sources(root):
    lock=json.loads((root/'selection_lock.json').read_text());source=json.loads((root/'source_lock.json').read_text())
    search=json.loads((root/'search_lock.json').read_text())
    assert sha256(root/'source_lock.json')==search['source_lock_sha256']
    for file,key in [('selection.json','selection_sha256'),('preflight.json','preflight_sha256'),('data_manifest.json','data_manifest_sha256'),('search_lock.json','search_lock_sha256')]:
        assert sha256(root/file)==lock[key]
    assert sha256(root/'pool.json')==search['pool_sha256']
    for file,key in [('pool.fasta','pool_fasta_sha256'),('references.fasta','references_fasta_sha256')]:assert sha256(root/file)==search[key]
    for path,digest in {**source['hashes'],**lock['search_hashes']}.items():assert sha256(Path(path))==digest
    for path in root.glob('command_*.stderr'):assert not path.read_text().strip()
    manifest=json.loads((root/'data_manifest.json').read_text())
    for name,digest in manifest.items():assert sha256(root/name)==digest
    pool=json.loads((root/'pool.json').read_text());refs=source['references'];n_hsps=0;bad=set();edges=set()
    assert len(pool)==len({r['group_id'] for r in pool})
    for file,subjects in [('references_hsps.tsv',refs),('pool_hsps.tsv',pool)]:
        with (root/file).open() as handle:
            for line in handle:
                q,s,ql,sl,e,qa,sa=line.rstrip().split('\t');i,j=int(q[1:]),int(s[1:])
                assert int(ql)==len(pool[i]['sequence']) and int(sl)==len(subjects[j]['sequence'])
                assert len(qa)==len(sa)
                pairs=[(x,y) for x,y in zip(qa,sa) if x!='-' and y!='-'];n=len(pairs);n_hsps+=1
                assert n<=min(int(ql),int(sl)) and float(e)>=0
                excluded=n>=50 and (float(e)<=1e-5 or (float(e)<=.001 and n/min(int(ql),int(sl))>=.7 and sum(x==y for x,y in pairs)/n>=.3))
                if excluded:
                    if file=='references_hsps.tsv':bad.add(i)
                    elif i!=j:edges.add(tuple(sorted((i,j))))
    archived=json.loads((root/'search_summary.json').read_text())
    assert bad==set(archived['reference_excluded_indices']) and edges=={tuple(x) for x in archived['pool_pair_edges']}
    outcomes={r['group_id']:r for r in json.loads((root/'preflight.json').read_text())}
    expected=[];counts=[0,0]
    for r in pool:
        s=r['stratum'];i=r['pool_index'];g=r['group_id']
        if i in bad or counts[s]>=80:continue
        assert g in outcomes,'eligible quota candidate was not preflighted'
        if not outcomes[g]['passed']:continue
        if any(r['pdb_id']==p['pdb_id'] or set(r['accessions']).intersection(p['accessions']) or tuple(sorted((i,p['pool_index']))) in edges for p in expected):continue
        expected.append(r|dict(role='validation' if counts[s]%5==0 else 'train'));counts[s]+=1
    selected=json.loads((root/'selection.json').read_text())
    assert [(r['group_id'],r['role']) for r in selected]==[(r['group_id'],r['role']) for r in expected]
    assert counts==lock['stratum_counts'] and lock['complete']==(counts==[80,80])
    reference_ids={r['group_id'] for r in refs};rows=[];role_counts={'train':0,'validation':0}
    for r in selected:
        g=r['group_id'];role_counts[r['role']]+=1
        assert g not in reference_ids and r['pdb_id'].lower() not in source['excluded_pdbs'] and not set(r['accessions']).intersection(source['excluded_accessions'])
        assert r['pool_index'] not in bad and r['group_id']==pool[r['pool_index']]['group_id']
        packet=root/'chemistry'/g;data=root/'data/examples'/g
        report=json.loads((packet/'report.json').read_text());assert report['passed'] and not report['unsupported_source_connections']
        metadata=json.loads((data/'gt.json').read_text());assert len(metadata['chains'])==1 and metadata['chains'][0]['sequence']==r['sequence']
        with np.load(packet/'mapping.npz') as m,np.load(data/'gt.npz') as gt:
            ri=m['residue_ids'].astype(int)-1;ai=np.array([ATOM37_INDEX[str(n)] for n in m['atom_names']])
            observed=gt['residue_mask'][ri]&gt['atom37_mask'][ri,ai]
            assert np.array_equal(observed,m['mask']) and observed.mean()>=.90
            assert np.array_equal(m['coordinates'][observed],gt['atom37_positions'][ri,ai][observed])
            assert np.isfinite(m['coordinates'][observed]).all() and np.all(m['coordinates'][~observed]==0)
            assert observed[np.isin(m['atom_names'],['N','CA','C','O'])].all()
            assert len(set(zip(m['chain_ids'],m['residue_ids'],m['atom_names'])))==len(ri)
            atoms=len(ri);seen=int(observed.sum())
        rows.append(dict(group_id=g,pdb_id=r['pdb_id'],role=r['role'],length=len(r['sequence']),
            native_atoms=atoms,observed_atoms=seen,missing_atoms=atoms-seen,observed_heavy_fraction=seen/atoms,
            assembly_protein_instances=r['source_assembly_composition']['protein_chain_instance_count']))
    for a,b in itertools.combinations(selected,2):
        assert a['pdb_id']!=b['pdb_id'] and not set(a['accessions']).intersection(b['accessions'])
        assert tuple(sorted((a['pool_index'],b['pool_index']))) not in edges
    assert role_counts==lock['role_counts']
    if lock['complete']:assert role_counts==dict(train=128,validation=32)
    write_json(root/'audit.json',dict(verified_sources=True,selection_complete=lock['complete'],rows=rows,
        role_counts=role_counts,hsps_reparsed=n_hsps,data_files_verified=len(manifest),
        selection_lock_sha256=sha256(root/'selection_lock.json'),script_sha256=sha256(Path(__file__)),
        no_model_outputs_read=True,training_started=False))
    print(json.dumps(dict(verified=True,selection_complete=lock['complete'],roles=role_counts,hsps=n_hsps)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);audit_adapter_sources(p.parse_args().root)
