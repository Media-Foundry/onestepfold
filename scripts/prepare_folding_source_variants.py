#!/usr/bin/env python3
"""Isolate and qualify alternate records without changing current training data."""
import argparse
import collections
import concurrent.futures
import hashlib
import json
import math
import multiprocessing
from pathlib import Path
import subprocess
import time

from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.sequence_isolation import read_hsps
from fastglycan.source_variants import canonical_hsp_index, select_isolated_variants


def prepare_folding_source_variants(root):
    assert not (root/'source_lock.json').exists()
    base=root.parent;inventory=base/'folding_unseen_source_inventory_v1_20260930'
    execution=json.loads((inventory/'execution.json').read_text())
    assert execution['complete'] and execution['inventory_sha256']==sha256(inventory/'inventory.json')
    census=json.loads((inventory/'inventory.json').read_text());assert census['complete']
    for p,d in census['inputs'].items():assert sha256(Path(p))==d
    extension=base/'folding_source_extension_v1_20260930'
    old=json.loads((extension/'source_lock.json').read_text())
    used=json.loads((extension/'selection.json').read_text());assert len(used)==455
    refs={r['group_id']:dict(group_id=r['group_id'],sequence=r['sequence']) for r in old['references']}
    for r in used:
        if r['group_id'] in refs:assert refs[r['group_id']]['sequence']==r['sequence']
        refs[r['group_id']]=dict(group_id=r['group_id'],sequence=r['sequence'])
    pdbs=set(old['excluded_pdbs'])|{r['pdb_id'].lower() for r in used}
    accessions=set(old['excluded_accessions'])|{a for r in used for a in r['accessions']}
    variants=collections.defaultdict(list)
    for r in census['variants']:
        assert r['group_id']==hashlib.sha256(r['sequence'].encode()).hexdigest()
        assert r['group_id'] not in refs and r['pdb_id'].lower() not in pdbs
        assert not set(r['accessions'])&accessions
        variants[r['group_id']].append(r)
    assert len(variants)==113 and sum(map(len,variants.values()))==234
    prefix='folding-alternate-source-v1:20260930:'
    groups=[]
    for i,g in enumerate(sorted(variants,key=lambda g:hashlib.sha256((prefix+g).encode()).hexdigest())):
        rows=sorted(variants[g],key=lambda r:(r['resolution_high_angstrom'],r['pdb_id'],r['source_label_asym_id'],r['assembly_id']))
        assert len({r['sequence'] for r in rows})==1
        groups.append(dict(index=i,group_id=g,sequence=rows[0]['sequence'],variants=rows))
    inputs={str(inventory/name):sha256(inventory/name) for name in ['inventory.json','execution.json']}
    inputs.update(census['inputs'])
    inputs[str(root/'protocol.md')]=sha256(root/'protocol.md')
    for r in census['variants']:
        p=base/'Dataset/raw/pdb_mmcif'/r['pdb_id'][1:3]/(r['pdb_id']+'.cif.gz')
        inputs[str(p)]=sha256(p)
    engineering=[min(used,key=lambda r:(len(r['sequence']),r['group_id'])),
        max(used,key=lambda r:(len(r['sequence']),r['group_id']))]
    manifest=json.loads((extension/'data_manifest.json').read_text())
    inputs[str(extension/'data_manifest.json')]=sha256(extension/'data_manifest.json')
    for row in engineering:
        for name in ['gt.npz','gt.json']:
            path=Path(row['source'])/name
            assert sha256(path)==manifest[f'data/examples/{row["group_id"]}/{name}']
            inputs[str(path)]=sha256(path)
    for record in old['tools'].values():
        assert sha256(Path(record['path']))==record['sha256']
        assert subprocess.check_output([record['path'],'-version'],text=True)==record['version']
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']}
    write_json(root/'source_lock.json',dict(groups=groups,engineering_rows=engineering,references=[refs[g] for g in sorted(refs)],
        excluded_pdbs=sorted(pdbs),excluded_accessions=sorted(accessions),input_hashes=inputs,hashes=hashes,
        tools=old['tools'],effective_dbsize=old['effective_dbsize'],workers=8,rank_prefix=prefix,
        protocol_sha256=sha256(root/'protocol.md'),script_sha256=sha256(Path(__file__)),
        scope='source-only; first qualifying alternative per sequence; reserve, do not train or predict'))


def search_folding_source_variants(root):
    assert not (root/'search_complete.json').exists()
    lock=json.loads((root/'source_lock.json').read_text())
    for p,d in lock['hashes'].items():assert sha256(Path(p))==d
    commands=[]
    for name,prefix,rows in [('pool','p',lock['groups']),('references','r',lock['references'])]:
        (root/f'{name}.fasta').write_text(''.join(f'>{prefix}{i}\n{r["sequence"]}\n' for i,r in enumerate(rows)))
        commands.append([lock['tools']['makeblastdb']['path'],'-in',str(root/f'{name}.fasta'),'-dbtype','prot',
            '-parse_seqids','-out',str(root/f'{name}_db')])
    for name in ['references','pool']:
        commands.append([lock['tools']['blastp']['path'],'-task','blastp','-query',str(root/'pool.fasta'),
            '-db',str(root/f'{name}_db'),'-out',str(root/f'{name}_hsps.tsv'),'-word_size','3','-matrix','BLOSUM62',
            '-gapopen','11','-gapextend','1','-seg','yes','-comp_based_stats','2','-evalue','.001',
            '-max_target_seqs',str(max(len(lock['groups']),len(lock['references']))),'-num_threads','8',
            '-dbsize',str(lock['effective_dbsize']),'-outfmt','6 qseqid sseqid qlen slen evalue qseq sseq'])
    write_json(root/'search_lock.json',dict(source_lock_sha256=sha256(root/'source_lock.json'),commands=commands,
        fasta_hashes={name:sha256(root/f'{name}.fasta') for name in ['pool','references']}))
    for i,cmd in enumerate(commands):
        with (root/f'command_{i}.stdout').open('w') as out,(root/f'command_{i}.stderr').open('w') as err:
            subprocess.run(cmd,stdout=out,stderr=err,check=True)
        assert not (root/f'command_{i}.stderr').read_text().strip(), 'search warning needs explicit review'
    write_json(root/'search_complete.json',dict(complete=True,search_lock_sha256=sha256(root/'search_lock.json'),
        source_lock_sha256=sha256(root/'source_lock.json'),hashes={name:sha256(root/f'{name}_hsps.tsv') for name in ['pool','references']}))


def qualify_folding_variant_group(args):
    from prepare_diffusion_training_sources import qualify_adapter_source
    group,root=args;root=Path(root);attempts=[];chosen=None
    for i,row in enumerate(group['variants']):
        folder=root/'attempts'/f'{group["index"]:03d}_{i:03d}'
        (folder/'chemistry').mkdir(parents=True,exist_ok=False)
        result=qualify_adapter_source((row,root.parent,folder))
        assert result['group_id']==row['group_id'] and result['pdb_id']==row['pdb_id']
        attempts.append(dict(result,variant_index=i,source_label_asym_id=row['source_label_asym_id']))
        if result['passed']:
            chosen=dict(row,source=result['source'],chemistry_packet=result['chemistry_packet'],
                source_mmcif_sha256=result['source_mmcif_sha256'],observed_heavy_fraction=result['observed_heavy_fraction'],
                role='reserved_source',variant_index=i)
            break
    return dict(group_id=group['group_id'],attempts=attempts,chosen=chosen)


def audit_folding_variant_packets(rows, root):
    import numpy as np
    import torch
    from onestepfold.data.gt_materializer import ATOM37_INDEX
    manifest={}
    for row in rows:
        data=Path(row['source']);packet=Path(row['chemistry_packet'])
        meta=json.loads((data/'gt.json').read_text());chem=json.loads((packet/'report.json').read_text())
        assert len(meta['chains'])==1 and meta['chains'][0]['sequence']==row['sequence']
        assert meta['qa']['backbone4_coverage']==1 and meta['qa']['chain_break_count']==meta['qa']['modified_residue_count']==0
        assert chem['passed'] and not chem['unsupported_source_connections']
        atoms=torch.load(packet/'native.pt',map_location='cpu',weights_only=False)['atoms']
        with np.load(data/'gt.npz') as gt,np.load(packet/'mapping.npz') as m:
            for field,attr in [('atom_names','atom_name'),('residue_ids','res_id'),('chain_ids','chain_id')]:
                assert np.array_equal(m[field],getattr(atoms,attr))
            ri=m['residue_ids'].astype(int)-1;ai=np.array([ATOM37_INDEX[str(a)] for a in m['atom_names']])
            mask=gt['residue_mask'][ri]&gt['atom37_mask'][ri,ai]
            assert np.array_equal(mask,m['mask']) and mask.mean()>=.90
            assert mask[np.isin(m['atom_names'],['N','CA','C','O'])].all()
            assert np.array_equal(m['coordinates'][mask],gt['atom37_positions'][ri,ai][mask])
            assert np.isfinite(m['coordinates'][mask]).all() and np.all(m['coordinates'][~mask]==0)
        for folder in [data,packet]:
            for p in folder.iterdir():
                if p.is_file():manifest[str(p.relative_to(root))]=sha256(p)
    return manifest


def qualify_folding_source_variants(root):
    import numpy as np
    import torch
    from migrate_expanded_sources_hpc3 import hpc3_source_worker_init
    from prepare_diffusion_training_sources import qualify_adapter_source
    begin=time.monotonic();torch.set_num_threads(1);assert not torch.cuda.is_available()
    assert not (root/'qualification.json').exists()
    lock=json.loads((root/'source_lock.json').read_text());done=json.loads((root/'search_complete.json').read_text())
    assert done['complete'] and done['source_lock_sha256']==sha256(root/'source_lock.json')
    assert done['search_lock_sha256']==sha256(root/'search_lock.json')
    for p,d in {**lock['input_hashes'],**lock['hashes']}.items():assert sha256(Path(p))==d
    engineering=[]
    for i,row in enumerate(lock['engineering_rows']):
        folder=root/'engineering'/str(i);(folder/'chemistry').mkdir(parents=True,exist_ok=False)
        result=qualify_adapter_source((row,root.parent,folder));assert result['passed'],result
        with np.load(Path(row['source'])/'gt.npz') as previous,np.load(Path(result['source'])/'gt.npz') as rebuilt:
            assert set(previous.files)==set(rebuilt.files)
            assert all(np.array_equal(previous[k],rebuilt[k]) for k in previous.files)
        assert json.loads((Path(row['source'])/'gt.json').read_text())==json.loads((Path(result['source'])/'gt.json').read_text())
        engineering.append(dict(group_id=row['group_id'],length=len(row['sequence']),passed=True,gt_replay_exact=True))
    write_json(root/'engineering.json',dict(complete=True,cases=engineering,model_calls=0))
    bad=set();edges=set();independent_bad=set();independent_edges=set();hsps=0
    for name,subjects in [('references',lock['references']),('pool',lock['groups'])]:
        file=root/f'{name}_hsps.tsv';assert sha256(file)==done['hashes'][name]
        for h in read_hsps(file):
            i,j=int(h.query[1:]),int(h.subject[1:])
            if h.evidence()['excluded']:
                if name=='references':bad.add(i)
                elif i!=j:edges.add(tuple(sorted((i,j))))
        for line in file.read_text().splitlines():
            q,s,ql,sl,e,qa,sa=line.split('\t');hsps+=1
            i=canonical_hsp_index(q,'p',len(lock['groups']))
            j=canonical_hsp_index(s,'r' if name=='references' else 'p',len(subjects))
            assert int(ql)==len(lock['groups'][i]['sequence']) and int(sl)==len(subjects[j]['sequence'])
            assert len(qa)==len(sa) and math.isfinite(float(e)) and float(e)>=0
            pairs=[(a,b) for a,b in zip(qa,sa) if a!='-' and b!='-'];n=len(pairs)
            assert n<=min(int(ql),int(sl))
            reject=n>=50 and (float(e)<=1e-5 or (float(e)<=.001 and n/min(int(ql),int(sl))>=.7 and sum(a==b for a,b in pairs)/n>=.3))
            if reject:
                if name=='references':independent_bad.add(i)
                elif i!=j:independent_edges.add(tuple(sorted((i,j))))
    assert (bad,edges)==(independent_bad,independent_edges)
    eligible=[g for g in lock['groups'] if g['index'] not in bad]
    write_json(root/'admission_lock.json',dict(source_lock_sha256=sha256(root/'source_lock.json'),
        search_complete_sha256=sha256(root/'search_complete.json'),eligible=[g['group_id'] for g in eligible],
        excluded_by_reference=len(bad),hsps_independently_reparsed=hsps))
    (root/'worker_threads').mkdir()
    with concurrent.futures.ProcessPoolExecutor(max_workers=8,mp_context=multiprocessing.get_context('spawn'),
        initializer=hpc3_source_worker_init,initargs=(str(root),)) as pool:
        results=list(pool.map(qualify_folding_variant_group,[(g,str(root)) for g in eligible]))
    assert [r['group_id'] for r in results]==[g['group_id'] for g in eligible]
    write_json(root/'preflight.json',results)
    qualified=[r['chosen'] for r in results if r['chosen'] is not None]
    for row in qualified:
        cif=root.parent/'Dataset/raw/pdb_mmcif'/row['pdb_id'][1:3]/(row['pdb_id']+'.cif.gz')
        assert row['source_mmcif_sha256']==lock['input_hashes'][str(cif)]==sha256(cif)
    group_edges={tuple(sorted((lock['groups'][i]['group_id'],lock['groups'][j]['group_id']))) for i,j in edges}
    selected,rejected=select_isolated_variants(qualified,group_edges)
    manifest=audit_folding_variant_packets(qualified,root)
    for a in selected:
        assert a['group_id'] not in {r['group_id'] for r in lock['references']}
        assert a['pdb_id'].lower() not in lock['excluded_pdbs'] and not set(a['accessions'])&set(lock['excluded_accessions'])
    for i,a in enumerate(selected):
        for b in selected[i+1:]:
            assert tuple(sorted((a['group_id'],b['group_id']))) not in group_edges
            assert a['pdb_id'].lower()!=b['pdb_id'].lower() and not set(a['accessions'])&set(b['accessions'])
    write_json(root/'qualified_sources.json',qualified);write_json(root/'isolated_sources.json',selected)
    write_json(root/'data_manifest.json',manifest)
    write_json(root/'qualification.json',dict(complete=True,source_lock_sha256=sha256(root/'source_lock.json'),
        admission_lock_sha256=sha256(root/'admission_lock.json'),preflight_sha256=sha256(root/'preflight.json'),
        engineering_sha256=sha256(root/'engineering.json'),
        isolated_sources_sha256=sha256(root/'isolated_sources.json'),data_manifest_sha256=sha256(root/'data_manifest.json'),
        candidate_groups=len(lock['groups']),eligible_groups=len(eligible),qualified_groups=len(qualified),
        isolated_groups=len(selected),mutual_rejections=rejected,visited_records=sum(len(r['attempts']) for r in results),
        failed_groups=[r['group_id'] for r in results if r['chosen'] is None],seconds=time.monotonic()-begin,
        scope='Source reservation only, same support rules; not a final validation panel, pretraining exclusion, or folding result'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['prepare','search','qualify'],required=True);a=p.parse_args()
    {'prepare':prepare_folding_source_variants,'search':search_folding_source_variants,
     'qualify':qualify_folding_source_variants}[a.mode](a.root.resolve())
