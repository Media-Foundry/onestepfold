#!/usr/bin/env python3
"""Exhaust the unchanged catalog admission universe beyond the old4096 pool."""
import argparse
import concurrent.futures
import hashlib
import json
import multiprocessing
from pathlib import Path
import subprocess
import time
from fastglycan.adapter_sources import scan_adapter_sources
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_folding_catalog_extension(root, parent):
    assert not (root/'source_lock.json').exists()
    begin = time.monotonic(); base = root.parent
    audit = json.loads((parent/'expanded_audit.json').read_text())
    assert audit['verified_sources'] and audit['selection_lock_sha256'] == sha256(parent/'selection_lock.json')
    selected = json.loads((parent/'selection.json').read_text())
    assert len(selected) == audit['selected'] < 512
    original = parent/'origin/old'
    old = json.loads((original/'source_lock.json').read_text())
    pool = json.loads((original/'pool.json').read_text())
    known = selected + json.loads((original/'selection.json').read_text()) + json.loads((parent/'origin/fresh/selection.json').read_text())
    refs = {r['group_id']:dict(group_id=r['group_id'],sequence=r['sequence']) for r in old['references'] + known}
    pdbs = set(old['excluded_pdbs']) | {r['pdb_id'].lower() for r in known}
    accessions = set(old['excluded_accessions']) | {a for r in known for a in r['accessions']}
    old_groups = {r['group_id'] for r in pool}
    shards = sorted((base/'catalog_v1').glob('shard-*.jsonl.gz'))
    assert len(shards) == 256
    # Exact catalog bytes from the original pre-fault source lock, not a new crawl.
    old_shards = {Path(p).name:d for p,d in old['hashes'].items() if '/catalog_v1/shard-' in p}
    assert len(old_shards) == 256
    for p in shards:
        assert sha256(p) == old_shards[p.name], p
    tools = {}
    for name, record in old['tools'].items():
        path = base/'tools/blast_2.17.0/ncbi-blast-2.17.0+'/ 'bin'/name
        assert sha256(path) == record['sha256']
        version = subprocess.check_output([str(path),'-version'],text=True)
        assert version == record['version']
        tools[name] = dict(path=str(path),sha256=record['sha256'],version=version)
    lock = dict(protocol='mini_folding_catalog_extension_v1',parent=str(parent),
        parent_audit_sha256=sha256(parent/'expanded_audit.json'),
        parent_selection_lock_sha256=sha256(parent/'selection_lock.json'),
        original_source_sha256=sha256(original/'source_lock.json'),
        old_pool_sha256=sha256(original/'pool.json'),inherited=len(selected),needed=512-len(selected),
        references=[refs[k] for k in sorted(refs)],excluded_pdbs=sorted(pdbs),
        excluded_accessions=sorted(accessions),tools=tools,effective_dbsize=old['effective_dbsize'],
        catalog_hashes={str(p):old_shards[p.name] for p in shards},
        script_sha256=sha256(Path(__file__)),protocol_sha256=sha256(root/'mini_folding_catalog_extension_v1.md'),
        rank_prefix='folding-catalog-remainder-v1:20260930:',workers=12,training_started=False)
    write_json(root/'source_lock.json',lock)
    representatives = {}; records = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=12,mp_context=multiprocessing.get_context('spawn')) as workers:
        for part in workers.map(scan_adapter_sources,shards):
            for r in part:
                records += 1; g = r['group_id']
                if g in old_groups or g in refs or r['pdb_id'].lower() in pdbs or accessions.intersection(r['accessions']):
                    continue
                key = (r['resolution_high_angstrom'],r['pdb_id'],r['source_label_asym_id'],r['assembly_id'])
                if g not in representatives or key < (representatives[g]['resolution_high_angstrom'],representatives[g]['pdb_id'],representatives[g]['source_label_asym_id'],representatives[g]['assembly_id']):
                    representatives[g] = r
    candidates = sorted(representatives.values(),key=lambda r:hashlib.sha256((lock['rank_prefix']+r['group_id']).encode()).hexdigest())
    # This pool has its own index namespace; never compare it to old pool indices.
    for i,r in enumerate(candidates):
        r['extension_index'] = i
    write_json(root/'pool.json',candidates)
    write_json(root/'census.json',dict(source_eligible_records=records,candidates=len(candidates),
        prior_train=len(selected),needed=lock['needed'],old_pool_excluded=len(old_groups),seconds=time.monotonic()-begin))
    commands = []
    for name,prefix,rows in [('references','r',lock['references']),('pool','p',candidates)]:
        (root/f'{name}.fasta').write_text(''.join(f'>{prefix}{i}\n{r["sequence"]}\n' for i,r in enumerate(rows)))
        if not candidates:
            continue
        commands.append([tools['makeblastdb']['path'],'-in',str(root/f'{name}.fasta'),'-dbtype','prot','-parse_seqids','-out',str(root/f'{name}_db')])
        commands.append([tools['blastp']['path'],'-task','blastp','-query',str(root/'pool.fasta'),'-db',str(root/f'{name}_db'),
            '-out',str(root/f'{name}_hsps.tsv'),'-word_size','3','-matrix','BLOSUM62','-gapopen','11','-gapextend','1',
            '-seg','yes','-comp_based_stats','2','-evalue','.001','-max_target_seqs',str(max(len(lock['references']),len(candidates))),
            '-num_threads','12','-dbsize',str(lock['effective_dbsize']),'-outfmt','6 qseqid sseqid qlen slen evalue qseq sseq'])
    write_json(root/'search_lock.json',dict(source_lock_sha256=sha256(root/'source_lock.json'),
        pool_sha256=sha256(root/'pool.json'),commands=commands,
        fasta_hashes={name:sha256(root/f'{name}.fasta') for name in ['references','pool']}))
    for i,command in enumerate(commands):
        with (root/f'command_{i}.stdout').open('w') as out,(root/f'command_{i}.stderr').open('w') as err:
            subprocess.run(command,stdout=out,stderr=err,check=True)
        assert not (root/f'command_{i}.stderr').read_text().strip()
    if not candidates:
        for name in ['references','pool']:
            (root/f'{name}_hsps.tsv').write_text('')
    write_json(root/'search_complete.json',dict(complete=True,candidates=len(candidates),
        search_lock_sha256=sha256(root/'search_lock.json'),
        search_hashes={name:sha256(root/f'{name}_hsps.tsv') for name in ['references','pool']},
        seconds=time.monotonic()-begin,source_preparation_complete=False,training_started=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--parent',type=Path,required=True)
    args = p.parse_args();prepare_folding_catalog_extension(args.root.resolve(),args.parent.resolve())
