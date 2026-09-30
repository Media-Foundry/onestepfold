#!/usr/bin/env python3
"""Independent source/order/HSP audit, including honest incomplete-set reporting."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json
from onestepfold.data.gt_materializer import ATOM37_INDEX


def audit_expanded_folding_sources(root):
    torch.set_num_threads(1)
    selection_lock = json.loads((root/'selection_lock.json').read_text())
    migration = json.loads((root/'migration_lock.json').read_text())
    assert selection_lock['migration_lock_sha256'] == sha256(root/'migration_lock.json')
    for name, digest in migration['hashes'].items():
        assert sha256(root/name) == digest, name
    execution = json.loads((root/'folding_resume_lock.json').read_text())
    assert execution['migration_sha256'] == sha256(root/'migration_lock.json')
    assert execution['script_sha256'] == sha256(root/'run_folding_source_shard.py')
    assert execution['protocol_sha256'] == sha256(root/'mini_folding_mainline_resume_v1.md')
    original = root/'origin/old'
    old_lock = json.loads((original/'source_lock.json').read_text())
    failed_lock = json.loads((root/'origin/failed/source_lock.json').read_text())
    assert sha256(root/'origin/failed/source_lock.json') == migration['old_source_lock_sha256']
    pool = json.loads((original/'pool.json').read_text())
    prior = json.loads((original/'selection.json').read_text())
    fresh = json.loads((root/'origin/fresh/selection.json').read_text())
    assert len(prior) == 160 and len(fresh) == 32
    assert failed_lock['prior_rows'] == prior + fresh
    assert len(pool) == len({r['group_id'] for r in pool})
    for i, row in enumerate(pool):
        assert row['pool_index'] == i
    # Reparse raw alignments rather than reuse preparation's HSP helper/results.
    excluded = set(); edges = set(); hsp_count = 0
    for name, subjects in [('references_hsps.tsv', old_lock['references']), ('pool_hsps.tsv', pool)]:
        for line in (original/name).read_text().splitlines():
            q, s, qlen, slen, evalue, qa, sa = line.split('\t')
            i, j = int(q[1:]), int(s[1:])
            assert int(qlen) == len(pool[i]['sequence'])
            assert int(slen) == len(subjects[j]['sequence']) and len(qa) == len(sa)
            pairs = [(a,b) for a,b in zip(qa,sa) if a != '-' and b != '-']
            n = len(pairs); hsp_count += 1
            assert n <= min(int(qlen), int(slen)) and float(evalue) >= 0
            reject = n >= 50 and (float(evalue) <= 1e-5 or (
                float(evalue) <= .001 and n/min(int(qlen),int(slen)) >= .7
                and sum(a == b for a,b in pairs)/n >= .3))
            if reject:
                if name == 'references_hsps.tsv':
                    excluded.add(i)
                elif i != j:
                    edges.add(tuple(sorted((i,j))))
    eligible = []
    for row in pool:
        if row['pool_index'] in excluded:
            continue
        if any(row['group_id'] == p['group_id'] or row['pdb_id'] == p['pdb_id']
               or set(row['accessions']).intersection(p['accessions'])
               or tuple(sorted((row['pool_index'],p['pool_index']))) in edges
               for p in prior + fresh):
            continue
        eligible.append(row)
    ordered = sorted(eligible, key=lambda r: hashlib.sha256(
        ('diffusion-expand512-v1:20260930:'+r['group_id']).encode()).hexdigest())
    assert sha256(root/'origin/failed/candidate_order.json') == migration['order_sha256']
    assert ordered == json.loads((root/'origin/failed/candidate_order.json').read_text())
    outcomes = {}
    for index in (0,1):
        shard = json.loads((root/f'shard_{index}.json').read_text())
        assert shard['complete'] and shard['index'] == index and shard['workers'] == 12
        assert shard['lock_sha256'] == sha256(root/'migration_lock.json')
        assert shard['execution_lock_sha256'] == sha256(root/'folding_resume_lock.json')
        assert [r['group_id'] for r in shard['outcomes']] == [r['group_id'] for r in ordered[index::2]]
        for r in shard['outcomes']:
            assert r['group_id'] not in outcomes
            outcomes[r['group_id']] = r
    assert len(outcomes) == len(ordered)
    additions = []
    for row in ordered:
        if len(additions) >= 384 or not outcomes[row['group_id']]['passed']:
            continue
        if any(row['pdb_id'] == p['pdb_id'] or set(row['accessions']).intersection(p['accessions'])
               or tuple(sorted((row['pool_index'],p['pool_index']))) in edges for p in additions):
            continue
        additions.append(row)
    inherited = [r for r in prior if r['role'] == 'train']
    assert len(inherited) == 128
    selected = json.loads((root/'selection.json').read_text())
    assert [r['group_id'] for r in selected] == [r['group_id'] for r in inherited + additions]
    assert selection_lock['complete'] == (len(additions) == 384)
    assert selection_lock['additional'] == len(additions) and selection_lock['selected'] == len(selected)
    assert sha256(root/'selection.json') == selection_lock['selection_sha256']
    assert sha256(root/'data_manifest.json') == selection_lock['data_manifest_sha256']
    manifest = json.loads((root/'data_manifest.json').read_text())
    for name, digest in manifest.items():
        assert sha256(root/name) == digest, name
    transfer = json.loads((root/'manifest.json').read_text())
    inherited_files = 0
    for row in inherited:
        for folder in ['data/examples','chemistry']:
            for p in (root/folder/row['group_id']).rglob('*'):
                if p.is_file():
                    key = 'inherited/'+str(p.relative_to(root))
                    assert sha256(p) == transfer[key]['sha256']
                    inherited_files += 1
    rows = []
    cif_hashes = json.loads((root/'cif_hashes.json').read_text())
    old_reference_ids = {r['group_id'] for r in old_lock['references']}
    for r in selected:
        assert r['role'] == 'train' and 50 <= len(r['sequence']) <= 1024
        assert r['group_id'] not in old_reference_ids and r['pool_index'] not in excluded
        assert r['pdb_id'].lower() not in old_lock['excluded_pdbs']
        assert not set(r['accessions']).intersection(old_lock['excluded_accessions'])
        g = r['group_id']; packet = root/'chemistry'/g; data = root/'data/examples'/g
        report = json.loads((packet/'report.json').read_text())
        assert report['passed'] and not report['unsupported_source_connections']
        provenance = json.loads((data/'input_provenance.json').read_text())
        cif = root.parent/'Dataset/raw/pdb_mmcif'/r['pdb_id'][1:3]/(r['pdb_id']+'.cif.gz')
        assert sha256(cif) == provenance['source_mmcif_sha256']
        if not r['inherited']:
            assert sha256(cif) == cif_hashes[r['pdb_id']]
        meta = json.loads((data/'gt.json').read_text())
        assert len(meta['chains']) == 1 and meta['chains'][0]['sequence'] == r['sequence']
        assert meta['qa']['backbone4_coverage'] == 1
        assert meta['qa']['chain_break_count'] == meta['qa']['modified_residue_count'] == 0
        native = torch.load(packet/'native.pt', map_location='cpu', weights_only=False)['atoms']
        with np.load(packet/'mapping.npz') as m, np.load(data/'gt.npz') as gt:
            for field, attr in [('atom_names','atom_name'),('residue_ids','res_id'),('chain_ids','chain_id')]:
                assert np.array_equal(m[field], getattr(native,attr)), (g,field)
            ri = m['residue_ids'].astype(int)-1
            ai = np.array([ATOM37_INDEX[str(n)] for n in m['atom_names']])
            seen = gt['residue_mask'][ri] & gt['atom37_mask'][ri,ai]
            assert np.array_equal(seen,m['mask']) and seen.mean() >= .9
            assert np.array_equal(m['coordinates'][seen],gt['atom37_positions'][ri,ai][seen])
            assert np.isfinite(m['coordinates'][seen]).all() and np.all(m['coordinates'][~seen] == 0)
            assert seen[np.isin(m['atom_names'],['N','CA','C','O'])].all()
            assert len(set(zip(m['chain_ids'],m['residue_ids'],m['atom_names']))) == len(ri)
            rows.append(dict(group_id=g,pdb_id=r['pdb_id'],inherited=r['inherited'],
                length=len(r['sequence']),native_atoms=len(ri),observed_atoms=int(seen.sum()),
                assembly_protein_instances=r['source_assembly_composition']['protein_chain_instance_count']))
    for a,b in itertools.combinations(selected + [r for r in prior if r['role']=='validation'] + fresh,2):
        assert a['group_id'] != b['group_id'] and a['pdb_id'] != b['pdb_id']
        assert not set(a['accessions']).intersection(b['accessions'])
        assert tuple(sorted((a['pool_index'],b['pool_index']))) not in edges
    result = dict(verified_sources=True,selection_complete=selection_lock['complete'],
        selected=len(selected),additional=len(additions),shortfall=384-len(additions),rows=rows,
        hsps_reparsed=hsp_count,candidates=len(ordered),data_files_verified=len(manifest),
        inherited_files_verified=inherited_files,validation_proteins_excluded=64,
        selection_lock_sha256=sha256(root/'selection_lock.json'),script_sha256=sha256(Path(__file__)),
        no_model_outputs_read=True,training_started=False)
    write_json(root/'expanded_audit.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True)
    audit_expanded_folding_sources(p.parse_args().root.resolve())
