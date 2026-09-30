#!/usr/bin/env python3
"""Source-only bounded pilot; no model scores or training calls."""
import argparse
import concurrent.futures
import hashlib
import json
import multiprocessing
from pathlib import Path
import subprocess
import time
import traceback

import numpy as np
from fastglycan.adapter_sources import scan_adapter_sources
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.sequence_isolation import read_hsps
from onestepfold.data.gt_materializer import materialize_entry, ATOM37_INDEX
from preflight_isolated_chemistry import check


def qualify_adapter_source(args):
    row,base,root=args;g=row['group_id'];folder=root/'data/examples'/g
    folder.mkdir(parents=True,exist_ok=False);result=dict(group_id=g,pdb_id=row['pdb_id'],passed=False)
    try:
        cif=base/'Dataset/raw/pdb_mmcif'/row['pdb_id'][1:3]/(row['pdb_id']+'.cif.gz')
        arrays,meta=materialize_entry(row,cif);second,meta2=materialize_entry(row,cif)
        assert meta==meta2 and all(np.array_equal(v,second[k]) for k,v in arrays.items())
        qa=meta['qa'];assert qa['backbone4_coverage']==1 and qa['chain_break_count']==qa['modified_residue_count']==0
        ids=[ATOM37_INDEX[n] for n in ['N','CA','C','O']]
        assert arrays['residue_mask'].all() and arrays['atom37_mask'][:,ids].all()
        assert np.isfinite(arrays['atom37_positions'][:,ids]).all()
        sgmask=arrays['residue_mask'] & arrays['atom37_mask'][:,ATOM37_INDEX['SG']]
        sg=arrays['atom37_positions'][sgmask,ATOM37_INDEX['SG']].astype(float)
        if len(sg)>1:
            distances=np.linalg.norm(sg[:,None]-sg[None],axis=-1)
            assert not np.any(distances[np.triu_indices(len(sg),1)]<2.3),'observed SG proximity outside supported unlinked graph'
        np.savez_compressed(folder/'gt.npz',**arrays);write_json(folder/'gt.json',meta)
        write_json(folder/'input_provenance.json',dict(sequence=row['sequence'],raw_gt_rebuild_exact=True,source_mmcif_sha256=sha256(cif)))
        write_json(folder/'prepared.json',dict(complete=True,files_sha256={n:sha256(folder/n) for n in ['gt.json','gt.npz','input_provenance.json']}))
        chemistry=check((row,root/'chemistry',base,root/'data'));result['chemistry']=chemistry
        assert chemistry['passed'],chemistry.get('error')
        with np.load(root/'chemistry'/g/'mapping.npz') as mapped:
            coverage=float(mapped['mask'].mean());assert coverage>=.90,'native heavy-atom observation fraction below .90'
            assert np.all(mapped['coordinates'][~mapped['mask']]==0)
        result.update(passed=True,source=str(folder),chemistry_packet=str(root/'chemistry'/g),
                      observed_heavy_fraction=coverage,source_mmcif_sha256=sha256(cif))
    except Exception:result['error']=traceback.format_exc()
    write_json(folder/'source_preflight.json',result)
    return result


def prepare_adapter_sources(base,root):
    assert not (root/'source_lock.json').exists();start=time.monotonic()
    root.mkdir(parents=True,exist_ok=True);(root/'chemistry').mkdir()
    old=base/'connection_calibration_v1_20260930';prior=json.loads((old/'source_lock.json').read_text())
    assert sha256(old/'source_lock.json')==json.loads((old/'selection_lock.json').read_text())['source_lock_sha256']
    refs={r['group_id']:r for r in prior['references']}
    historical=json.loads((base/'anchored_independent_v1_20260929/screen_lock.json').read_text())
    pdbs=set(historical['excluded_pdbs']);accessions=set(historical['excluded_accessions'])
    paths=[old/'source_lock.json',old/'selection_lock.json',base/'anchored_independent_v1_20260929/screen_lock.json']
    for path in [base/'independent32_v2_20260930/panel32.json',base/'local_fit_gt_source_v1_20260930/selection.json',
                 base/'connection_calibration_extension_v1_20260930/selection.json',base/'fresh_contact_source_v1_20260930/selection.json']:
        paths.append(path)
        for r in json.loads(path.read_text()):
            refs[r['group_id']]=r;pdbs.add(r['pdb_id'].lower());accessions.update(r['accessions'])
    preflight=base/'diffusion_adapter_preflight_v1_20260930/lock.json';paths.append(preflight)
    r=json.loads(preflight.read_text())['row'];assert r['pdb_id']=='1u07'
    refs[r['group_id']]=r;pdbs.add(r['pdb_id']);accessions.update(r['accessions'])
    reference_rows=[dict(group_id=g,sequence=refs[g]['sequence']) for g in sorted(refs)]
    shards=sorted((base/'catalog_v1').glob('shard-*.jsonl.gz'));assert len(shards)==256
    hashes={str(p):sha256(p) for p in paths+shards}
    hashes.update({str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']})
    write_json(root/'source_lock.json',dict(hashes=hashes,protocol='mini_diffusion_training_sources_v1',
        planned_train=128,planned_validation=32,bins=[[50,255],[256,1024]],pool_cap_per_bin=2048,
        excluded_pdbs=sorted(pdbs),excluded_accessions=sorted(accessions),references=reference_rows,
        tools=prior['tools'],effective_dbsize=prior['original_effective_dbsize'],folding_started=False))
    reps={};screen_counts=dict(source_eligible_records=0,historical_identity_records=0)
    with concurrent.futures.ProcessPoolExecutor(max_workers=16) as executor:
        for part in executor.map(scan_adapter_sources,shards):
            for r in part:
                screen_counts['source_eligible_records']+=1;g=r['group_id']
                if g in refs or r['pdb_id'].lower() in pdbs or accessions.intersection(r['accessions']):
                    screen_counts['historical_identity_records']+=1;continue
                key=(r['resolution_high_angstrom'],r['pdb_id'],r['source_label_asym_id'],r['assembly_id'])
                if g not in reps or key<(reps[g]['resolution_high_angstrom'],reps[g]['pdb_id'],reps[g]['source_label_asym_id'],reps[g]['assembly_id']):reps[g]=r
    pool=[]
    for stratum in [0,1]:
        ranked=sorted((r for r in reps.values() if r['stratum']==stratum),key=lambda r:hashlib.sha256(('diffusion-sources-v1:20260930:'+r['group_id']).encode()).hexdigest())
        pool.extend(ranked[:2048])
    for i,r in enumerate(pool):r['pool_index']=i
    write_json(root/'pool.json',pool);write_json(root/'source_census.json',dict(**screen_counts,eligible_groups=len(reps),pool=len(pool),pool_counts=[sum(r['stratum']==s for r in pool) for s in [0,1]]))
    tools=prior['tools']
    for info in tools.values():assert sha256(Path(info['path']))==info['sha256']
    for name,prefix,rows in [('references','r',reference_rows),('pool','p',pool)]:
        (root/f'{name}.fasta').write_text(''.join(f'>{prefix}{i}\n{r["sequence"]}\n' for i,r in enumerate(rows)))
    commands=[]
    for name in ['references','pool']:
        commands.append([tools['makeblastdb']['path'],'-in',str(root/f'{name}.fasta'),'-dbtype','prot','-parse_seqids','-out',str(root/f'{name}_db')])
        commands.append([tools['blastp']['path'],'-task','blastp','-query',str(root/'pool.fasta'),'-db',str(root/f'{name}_db'),
            '-out',str(root/f'{name}_hsps.tsv'),'-word_size','3','-matrix','BLOSUM62','-gapopen','11','-gapextend','1',
            '-seg','yes','-comp_based_stats','2','-evalue','.001','-max_target_seqs',str(max(len(reference_rows),len(pool))),
            '-num_threads','16','-dbsize',str(prior['original_effective_dbsize']),'-outfmt','6 qseqid sseqid qlen slen evalue qseq sseq'])
    write_json(root/'search_lock.json',dict(source_lock_sha256=sha256(root/'source_lock.json'),pool_sha256=sha256(root/'pool.json'),
        references_fasta_sha256=sha256(root/'references.fasta'),pool_fasta_sha256=sha256(root/'pool.fasta'),commands=commands))
    print(json.dumps(dict(stage='search',pool=len(pool),references=len(reference_rows))),flush=True)
    for i,command in enumerate(commands):
        with (root/f'command_{i}.stdout').open('w') as out,(root/f'command_{i}.stderr').open('w') as err:
            subprocess.run(command,stdout=out,stderr=err,check=True)
        assert not (root/f'command_{i}.stderr').read_text().strip(),'search stderr requires audit'
    bad={int(h.query[1:]) for h in read_hsps(root/'references_hsps.tsv') if h.evidence()['excluded']}
    edges={tuple(sorted((int(h.query[1:]),int(h.subject[1:])))) for h in read_hsps(root/'pool_hsps.tsv') if h.query!=h.subject and h.evidence()['excluded']}
    write_json(root/'search_summary.json',dict(reference_excluded_indices=sorted(bad),pool_pair_edges=sorted(edges)))
    eligible=[r for r in pool if r['pool_index'] not in bad]
    selected=[];outcomes=[];rejected=[];counts=[0,0]
    with concurrent.futures.ProcessPoolExecutor(max_workers=8,mp_context=multiprocessing.get_context('spawn')) as executor:
        for begin in range(0,len(eligible),32):
            batch=[r for r in eligible[begin:begin+32] if counts[r['stratum']]<80]
            if not batch:continue
            results=list(executor.map(qualify_adapter_source,[(r,base,root) for r in batch]));outcomes.extend(results)
            for r,result in zip(batch,results):
                if not result['passed']:
                    rejected.append(dict(group_id=r['group_id'],reason='source_or_native_preflight'));continue
                if counts[r['stratum']]>=80:continue
                conflict=next((s['group_id'] for s in selected if r['pdb_id']==s['pdb_id'] or set(r['accessions']).intersection(s['accessions']) or tuple(sorted((r['pool_index'],s['pool_index']))) in edges),None)
                if conflict:
                    rejected.append(dict(group_id=r['group_id'],reason='selected_identity_or_hsp',conflict=conflict));continue
                role='validation' if counts[r['stratum']]%5==0 else 'train'
                selected.append(r|dict(role=role,source=result['source'],chemistry_packet=result['chemistry_packet'],observed_heavy_fraction=result['observed_heavy_fraction']))
                counts[r['stratum']]+=1
            write_json(root/'preflight.json',outcomes);write_json(root/'selection_provisional.json',selected)
            write_json(root/'progress.json',dict(stage='native_preflight',evaluated=len(outcomes),eligible=len(eligible),selected=len(selected),counts=counts))
            if counts==[80,80]:break
    write_json(root/'selection.json',selected);write_json(root/'rejections.json',rejected)
    files={str(p.relative_to(root)):sha256(p) for folder in ['data','chemistry'] for p in (root/folder).rglob('*') if p.is_file()}
    write_json(root/'data_manifest.json',files)
    write_json(root/'selection_lock.json',dict(complete=counts==[80,80],selected=len(selected),stratum_counts=counts,
        role_counts={role:sum(r['role']==role for r in selected) for role in ['train','validation']},
        selection_sha256=sha256(root/'selection.json'),preflight_sha256=sha256(root/'preflight.json'),
        data_manifest_sha256=sha256(root/'data_manifest.json'),search_lock_sha256=sha256(root/'search_lock.json'),
        search_hashes={str(root/f'{name}_hsps.tsv'):sha256(root/f'{name}_hsps.tsv') for name in ['references','pool']},
        seconds=time.monotonic()-start,folding_started=False,training_started=False))
    print(json.dumps(dict(stage='complete',counts=counts,selected=len(selected))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    a=p.parse_args();prepare_adapter_sources(a.base,a.root)
