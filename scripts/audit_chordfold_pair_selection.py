"""Reproduce metadata-only pair selection; no model outputs or displacement scores."""
import argparse
import hashlib
from pathlib import Path
from collections import defaultdict,Counter
import json
from fastglycan.paired_teacher_protocol import sha256,write_json


def audit_chord_pair_selection(data,inventory,preselection,output):
    rows=json.loads((data/'selection.json').read_text())
    eligible=[r for r in rows if r['split']=='train' and 80<=len(r['sequence'])<=180
        and r['resolution_high_angstrom'] is not None and r['resolution_high_angstrom']<=2.5
        and set(r['sequence'])<=set('ACDEFGHIKLMNPQRSTVWY')]
    buckets=defaultdict(list);pairs=[];seen=set()
    for i,b in enumerate(eligible):
        s=b['sequence']
        for pos in range(len(s)):
            key=(len(s),pos,s[:pos]+s[pos+1:])
            for j in buckets[key]:
                a=eligible[j]
                if a['sequence']==s or a['pdb_id']==b['pdb_id'] or (j,i) in seen:continue
                seen.add((j,i));pairs.append(dict(a=a,b=b,position=pos))
            buckets[key].append(i)
    original=json.loads(inventory.read_text())
    ids=lambda x:(x['a']['group_id'],x['b']['group_id'],x['position'])
    assert {ids(p) for p in pairs}=={ids(p) for p in original},'candidate inventory differs'
    ranked=sorted(pairs,key=lambda p:hashlib.sha256(('chordfold-pair-v1:20261001:'+p['a']['group_id']+p['b']['group_id']).encode()).hexdigest())
    chosen=[];used=set();reject=Counter();metadata_hashes={}
    for pair in ranked:
        metas=[]
        for key in ['a','b']:
            p=data/'examples'/pair[key]['group_id']/'gt.json';metadata_hashes[str(p)]=sha256(p);metas.append(json.loads(p.read_text()))
        if any(len(m['chains'])!=1 or m['chains'][0]['sequence']!=pair[k]['sequence'] for k,m in zip(['a','b'],metas)):
            reject['chain']+=1;continue
        if any(m['qa']['backbone4_coverage']!=1 or m['qa']['chain_break_count'] or m['qa']['modified_residue_count'] for m in metas):
            reject['backbone']+=1;continue
        if any(any(m['hidden_context'][k] for k in ['ion_atom_count','ligand_atom_count','nucleic_acid_atom_count','other_polymer_atom_count']) for m in metas):
            reject['context']+=1;continue
        accessions=[{s['sp_primary'] for s in m['chains'][0]['sifts_provenance']} for m in metas];shared=accessions[0]&accessions[1]
        if not shared or shared&used:reject['accession']+=1;continue
        used|=shared;chosen.append(pair)
        if len(chosen)==4:break
    expected=json.loads(preselection.read_text())['pairs']
    assert [ids(p) for p in chosen]==[ids(p) for p in expected],'frozen preselection differs'
    write_json(output,dict(complete=True,eligible=len(eligible),candidate_pairs=len(pairs),rejections=dict(reject),
        selected=[dict(source=p['a']['pdb_id'],target=p['b']['pdb_id'],position=p['position']) for p in chosen],
        inputs={str(p):sha256(p) for p in [data/'selection.json',inventory,preselection]},metadata_hashes=metadata_hashes,
        accessed_predictions=False))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['data','inventory','preselection','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();audit_chord_pair_selection(a.data,a.inventory,a.preselection,a.output)
