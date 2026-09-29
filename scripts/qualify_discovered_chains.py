#!/usr/bin/env python3
"""Build a bounded source-only homooligomer shortlist, then native chemical checks."""
import argparse,concurrent.futures,hashlib,json,multiprocessing
from pathlib import Path
import gemmi
from preflight_isolated_chemistry import check


def source_context(row,block):
    conn=block.get_mmcif_category('_struct_conn.');source=row['source_label_asym_id'];unsupported=[]
    for i,kind in enumerate(conn.get('conn_type_id',[])):
        if not (kind.startswith('covale') or kind=='disulf'):continue
        c1=conn['ptnr1_label_asym_id'][i];c2=conn['ptnr2_label_asym_id'][i]
        if source not in [c1,c2]:continue
        a1=conn['ptnr1_label_atom_id'][i];a2=conn['ptnr2_label_atom_id'][i];r1=conn['ptnr1_label_seq_id'][i];r2=conn['ptnr2_label_seq_id'][i]
        if not (c1==c2==source and str(r1).isdigit() and str(r2).isdigit() and abs(int(r1)-int(r2))==1 and {a1,a2}=={'C','N'}):
            unsupported.append(dict(kind=kind,chains=[c1,c2],atoms=[a1,a2],residues=[r1,r2]))
    poly=block.get_mmcif_category('_entity_poly.');asym=block.get_mmcif_category('_struct_asym.')
    proteins={poly['entity_id'][i]:''.join(poly['pdbx_seq_one_letter_code_can'][i].split()) for i,t in enumerate(poly['type']) if t.startswith('polypeptide')}
    seqs={a:proteins[e] for a,e in zip(asym['id'],asym['entity_id']) if e in proteins}
    composition=row['source_assembly_composition'];sources=composition['source_asym_ids'];partner_seqs=[seqs[s] for s in sources if s in seqs]
    assert seqs[source]==row['sequence']
    protein_only=composition['nucleic_acid_chain_instance_count']==composition['other_polymer_chain_instance_count']==0
    homo=protein_only and bool(partner_seqs) and all(s==row['sequence'] for s in partner_seqs) and composition['protein_chain_instance_count']>1
    return dict(homooligomer=homo,protein_only=protein_only,protein_instances=composition['protein_chain_instance_count'],protein_source_chains=len(partner_seqs),unique_protein_sequences=len(set(partner_seqs)),unsupported_connections=unsupported)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--discovery',type=Path,required=True);p.add_argument('--base',type=Path,required=True);a=p.parse_args();r=a.root;r.mkdir(exist_ok=False)
    rows=json.loads((a.discovery/'chemistry_candidates.json').read_text());edges={tuple(x) for x in json.loads((a.discovery/'pair_edges.json').read_text())}
    retained=json.loads((a.base/'validation_source_extension_v1_1_20260930/incomplete_panel.json').read_text())
    contexts=[];cache={};first={}
    for row in rows:
        pdb=row['pdb_id']
        if pdb not in cache:cache[pdb]=gemmi.cif.read(str(a.base/'Dataset/raw/pdb_mmcif'/pdb[1:3]/(pdb+'.cif.gz'))).sole_block()
        context=source_context(row,cache[pdb]);contexts.append(dict(variant_id=row['variant_id'],group_id=row['group_id'],pdb_id=pdb,**context))
        if context['homooligomer'] and not context['unsupported_connections'] and row['group_id'] not in first:first[row['group_id']]=dict(row,source_context=context)
    (r/'contexts.json').write_text(json.dumps(contexts,indent=2)+'\n')
    ordered=sorted(first.values(),key=lambda x:hashlib.sha256(('anchored-full-discovery-v5:20260930:'+x['group_id']).encode()).hexdigest())
    selected=[];rejected=[]
    for row in ordered:
        conflict=next((x['group_id'] for x in retained+selected if set(x['accessions'])&set(row['accessions']) or tuple(sorted((x['group_id'],row['group_id']))) in edges),None)
        if conflict:rejected.append(dict(group_id=row['group_id'],conflict=conflict));continue
        selected.append(row)
        if len(selected)==8:break
    (r/'shortlist.json').write_text(json.dumps(selected,indent=2)+'\n')
    (r/'lock.json').write_text(json.dumps(dict(groups_with_supported_homooligomer=len(first),shortlisted=len(selected),peer_conflicts=rejected,panel_admission=False,source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a.discovery/'chemistry_candidates.json',a.discovery/'pair_edges.json',r/'shortlist.json',Path(__file__)]}),indent=2)+'\n')
    print('supported homo groups, shortlisted',len(first),len(selected),flush=True)
    (r/'chemistry').mkdir()
    args=[(row,r/'chemistry',a.base,a.discovery/'variants_data'/row['variant_id']) for row in selected]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as ex:results=list(ex.map(check,args))
    report=dict(complete=True,total=len(results),passed=sum(x['passed'] for x in results),rows=results,panel_admission=False,folding_started=False)
    (r/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('native chemistry passed',report['passed'],flush=True)


if __name__=='__main__':main()
