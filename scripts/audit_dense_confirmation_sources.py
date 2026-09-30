#!/usr/bin/env python3
"""Independent fresh32 identity/HSP, ordering and observed-GT audit."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
from fastglycan.paired_teacher_protocol import sha256, write_json
from onestepfold.data.gt_materializer import ATOM37_INDEX


def audit_dense_confirmation_sources(root):
    selection=json.loads((root/'selection_lock.json').read_text());lock=json.loads((root/'source_lock.json').read_text())
    assert selection['source_lock_sha256']==sha256(root/'source_lock.json')
    for file,key in [('selection.json','selection_sha256'),('preflight.json','preflight_sha256'),('data_manifest.json','data_manifest_sha256'),('candidate_order.json','candidate_order_sha256')]:assert sha256(root/file)==selection[key]
    for p,d in lock['hashes'].items():assert sha256(Path(p))==d
    parent=Path(lock['parent']);old=json.loads((parent/'source_lock.json').read_text());search=json.loads((parent/'search_lock.json').read_text())
    for p,d in old['hashes'].items():assert sha256(Path(p))==d
    for name,key in [('pool.fasta','pool_fasta_sha256'),('references.fasta','references_fasta_sha256')]:assert sha256(parent/name)==search[key]
    for p in parent.glob('command_*.stderr'):assert not p.read_text().strip()
    for name,tool in old['tools'].items():assert sha256(Path(tool['path']))==tool['sha256']
    pool=json.loads((parent/'pool.json').read_text());prior=lock['prior_rows'];assert len(prior)==160
    assert prior==json.loads((parent/'selection.json').read_text())
    refs=old['references'];bad=set();edges=set();nhsp=0
    for file,subjects in [('references_hsps.tsv',refs),('pool_hsps.tsv',pool)]:
        with (parent/file).open() as handle:
            for line in handle:
                q,s,ql,sl,e,qa,sa=line.rstrip().split('\t');i,j=int(q[1:]),int(s[1:])
                assert int(ql)==len(pool[i]['sequence']) and int(sl)==len(subjects[j]['sequence']) and len(qa)==len(sa)
                pairs=[(a,b) for a,b in zip(qa,sa) if a!='-' and b!='-'];n=len(pairs);nhsp+=1
                assert n<=min(int(ql),int(sl)) and float(e)>=0
                excluded=n>=50 and (float(e)<=1e-5 or (float(e)<=.001 and n/min(int(ql),int(sl))>=.7 and sum(a==b for a,b in pairs)/n>=.3))
                if excluded:
                    if file=='references_hsps.tsv':bad.add(i)
                    elif i!=j:edges.add(tuple(sorted((i,j))))
    archived=json.loads((root/'isolation_summary.json').read_text())
    assert bad==set(archived['reference_bad']) and edges=={tuple(x) for x in archived['pair_edges']}
    eligible=[]
    for r in pool:
        if r['pool_index'] in bad:continue
        conflict=any(r['group_id']==p['group_id'] or r['pdb_id']==p['pdb_id'] or set(r['accessions']).intersection(p['accessions']) or tuple(sorted((r['pool_index'],p['pool_index']))) in edges for p in prior)
        assert conflict==(r['group_id'] in archived['prior_conflicts'])
        if not conflict:eligible.append(r)
    ordered=sorted(eligible,key=lambda r:(r['stratum'],hashlib.sha256((lock['rank_prefix']+r['group_id']).encode()).hexdigest()))
    assert ordered==json.loads((root/'candidate_order.json').read_text())
    outcomes={r['group_id']:r for r in json.loads((root/'preflight.json').read_text())};expected=[];counts=[0,0]
    for r in ordered:
        if counts[r['stratum']]>=16:continue
        assert r['group_id'] in outcomes
        if not outcomes[r['group_id']]['passed']:continue
        if any(r['pdb_id']==p['pdb_id'] or set(r['accessions']).intersection(p['accessions']) or tuple(sorted((r['pool_index'],p['pool_index']))) in edges for p in expected):continue
        expected.append(r);counts[r['stratum']]+=1
    selected=json.loads((root/'selection.json').read_text());assert [r['group_id'] for r in selected]==[r['group_id'] for r in expected]
    assert counts==selection['stratum_counts'] and selection['complete']==(counts==[16,16])
    manifest=json.loads((root/'data_manifest.json').read_text())
    for name,digest in manifest.items():assert sha256(root/name)==digest
    rows=[]
    for r in selected:
        assert r['role']=='validation' and r['confirmation_cohort']=='dense_v1'
        assert r['pdb_id'].lower() not in old['excluded_pdbs'] and not set(r['accessions']).intersection(old['excluded_accessions'])
        assert r['group_id'] not in {p['group_id'] for p in refs}
        g=r['group_id'];packet=root/'chemistry'/g;data=root/'data/examples'/g
        report=json.loads((packet/'report.json').read_text());assert report['passed'] and not report['unsupported_source_connections']
        meta=json.loads((data/'gt.json').read_text());assert len(meta['chains'])==1 and meta['chains'][0]['sequence']==r['sequence']
        with np.load(packet/'mapping.npz') as m,np.load(data/'gt.npz') as gt:
            ri=m['residue_ids'].astype(int)-1;ai=np.array([ATOM37_INDEX[str(n)] for n in m['atom_names']])
            seen=gt['residue_mask'][ri]&gt['atom37_mask'][ri,ai]
            assert seen.dtype==np.bool_ and np.array_equal(seen,m['mask']) and seen.mean()>=.9
            assert np.array_equal(m['coordinates'][seen],gt['atom37_positions'][ri,ai][seen])
            assert np.isfinite(m['coordinates'][seen]).all() and np.all(m['coordinates'][~seen]==0)
            assert seen[np.isin(m['atom_names'],['N','CA','C','O'])].all()
            assert len(set(zip(m['chain_ids'],m['residue_ids'],m['atom_names'])))==len(ri)
            rows.append(dict(group_id=g,pdb_id=r['pdb_id'],length=len(r['sequence']),stratum=r['stratum'],native_atoms=len(ri),
                observed_atoms=int(seen.sum()),observed_fraction=float(seen.mean()),
                assembly_protein_instances=r['source_assembly_composition']['protein_chain_instance_count']))
    for a,b in itertools.combinations(selected,2):
        assert a['pdb_id']!=b['pdb_id'] and not set(a['accessions']).intersection(b['accessions'])
        assert tuple(sorted((a['pool_index'],b['pool_index']))) not in edges
    write_json(root/'audit.json',dict(verified_sources=True,selection_complete=selection['complete'],rows=rows,
        hsps_reparsed=nhsp,data_files_verified=len(manifest),prior_proteins_excluded=160,
        selection_lock_sha256=sha256(root/'selection_lock.json'),no_model_outputs_read=True,
        script_sha256=sha256(Path(__file__)),training_started=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);audit_dense_confirmation_sources(p.parse_args().root)
