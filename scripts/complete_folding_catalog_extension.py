#!/usr/bin/env python3
"""Bounded native preparation and independently reparsed selection of the remainder."""
import argparse
import concurrent.futures
import itertools
import json
import multiprocessing
from pathlib import Path
import time
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.sequence_isolation import read_hsps
from onestepfold.data.gt_materializer import ATOM37_INDEX
from prepare_diffusion_training_sources import qualify_adapter_source
from migrate_expanded_sources_hpc3 import hpc3_source_worker_init


def complete_folding_catalog_extension(root):
    torch.set_num_threads(1)
    assert not torch.cuda.is_available() and not (root/'selection_lock.json').exists()
    begin = time.monotonic()
    lock = json.loads((root/'source_lock.json').read_text()); parent = Path(lock['parent'])
    search = json.loads((root/'search_lock.json').read_text())
    complete = json.loads((root/'search_complete.json').read_text())
    assert complete['complete'] and complete['search_lock_sha256'] == sha256(root/'search_lock.json')
    assert search['source_lock_sha256'] == sha256(root/'source_lock.json')
    assert search['pool_sha256'] == sha256(root/'pool.json')
    for name, digest in complete['search_hashes'].items():
        assert sha256(root/f'{name}_hsps.tsv') == digest
    assert sha256(parent/'expanded_audit.json') == lock['parent_audit_sha256']
    assert sha256(parent/'selection_lock.json') == lock['parent_selection_lock_sha256']
    parent_lock = json.loads((parent/'selection_lock.json').read_text())
    assert sha256(parent/'selection.json') == parent_lock['selection_sha256']
    assert sha256(parent/'data_manifest.json') == parent_lock['data_manifest_sha256']
    pool = json.loads((root/'pool.json').read_text())
    prior = json.loads((parent/'selection.json').read_text())
    assert len(prior) == lock['inherited']
    bad = {int(h.query[1:]) for h in read_hsps(root/'references_hsps.tsv') if h.evidence()['excluded']}
    edges = {tuple(sorted((int(h.query[1:]),int(h.subject[1:]))))
             for h in read_hsps(root/'pool_hsps.tsv') if h.query != h.subject and h.evidence()['excluded']}
    eligible = [r for r in pool if r['extension_index'] not in bad]
    (root/'chemistry').mkdir(); (root/'data/examples').mkdir(parents=True); (root/'worker_threads').mkdir()
    write_json(root/'admission_lock.json',dict(script_sha256=sha256(Path(__file__)),
        search_complete_sha256=sha256(root/'search_complete.json'),
        parent_selection_lock_sha256=sha256(parent/'selection_lock.json'),eligible=len(eligible),
        workers=12,needed=lock['needed'],no_training=True))
    with concurrent.futures.ProcessPoolExecutor(max_workers=12,
        mp_context=multiprocessing.get_context('spawn'),initializer=hpc3_source_worker_init,
        initargs=(str(root),)) as workers:
        outcomes = list(workers.map(qualify_adapter_source,[(r,root.parent,root) for r in eligible]))
    assert [r['group_id'] for r in outcomes] == [r['group_id'] for r in eligible]
    write_json(root/'preflight.json',outcomes)
    by_id = {r['group_id']:r for r in outcomes}; additions = []
    for r in eligible:
        if len(additions) >= lock['needed'] or not by_id[r['group_id']]['passed']:
            continue
        if any(r['pdb_id'] == s['pdb_id'] or set(r['accessions']).intersection(s['accessions'])
               or tuple(sorted((r['extension_index'],s['extension_index']))) in edges for s in additions):
            continue
        additions.append(r)
    # Independently parse alignment strings and rebuild the greedy selection.
    independent_bad = set(); independent_edges = set(); nhsps = 0
    for name, subjects in [('references',lock['references']),('pool',pool)]:
        for line in (root/f'{name}_hsps.tsv').read_text().splitlines():
            q,s,ql,sl,e,qa,sa = line.split('\t'); i,j = int(q[1:]),int(s[1:])
            assert int(ql) == len(pool[i]['sequence']) and int(sl) == len(subjects[j]['sequence'])
            assert len(qa) == len(sa)
            pairs = [(a,b) for a,b in zip(qa,sa) if a != '-' and b != '-']; n = len(pairs); nhsps += 1
            assert n <= min(int(ql),int(sl)) and float(e) >= 0
            rejected = n >= 50 and (float(e) <= 1e-5 or (float(e) <= .001
                and n/min(int(ql),int(sl)) >= .7 and sum(a == b for a,b in pairs)/n >= .3))
            if rejected:
                if name == 'references': independent_bad.add(i)
                elif i != j: independent_edges.add(tuple(sorted((i,j))))
    assert bad == independent_bad and edges == independent_edges
    rebuilt = []
    for r in pool:
        if r['extension_index'] in independent_bad or len(rebuilt) == lock['needed']:
            continue
        assert r['group_id'] in by_id
        if not by_id[r['group_id']]['passed']:
            continue
        if any(r['pdb_id'] == s['pdb_id'] or set(r['accessions']).intersection(s['accessions'])
               or tuple(sorted((r['extension_index'],s['extension_index']))) in independent_edges for s in rebuilt):
            continue
        rebuilt.append(r)
    assert rebuilt == additions
    parent_manifest = json.loads((parent/'data_manifest.json').read_text())
    # Explicit read-only source references; no data duplication or mutation.
    for r in prior:
        for folder in ['chemistry','data/examples']:
            destination = root/folder/r['group_id']; target = parent/folder/r['group_id']
            for p in target.iterdir():
                if p.is_file(): assert sha256(p) == parent_manifest[str(p.relative_to(parent))]
            destination.symlink_to(target,target_is_directory=True)
    selected = [r | dict(source=str(root/'data/examples'/r['group_id']),
        chemistry_packet=str(root/'chemistry'/r['group_id']),extension_inherited=True) for r in prior]
    new_audit = []
    for r in additions:
        g = r['group_id']; packet = root/'chemistry'/g; data = root/'data/examples'/g
        native = torch.load(packet/'native.pt',map_location='cpu',weights_only=False)['atoms']
        report = json.loads((packet/'report.json').read_text())
        meta = json.loads((data/'gt.json').read_text())
        assert report['passed'] and not report['unsupported_source_connections']
        assert len(meta['chains']) == 1 and meta['chains'][0]['sequence'] == r['sequence']
        assert meta['qa']['backbone4_coverage'] == 1 and meta['qa']['chain_break_count'] == meta['qa']['modified_residue_count'] == 0
        provenance = json.loads((data/'input_provenance.json').read_text())
        cif = root.parent/'Dataset/raw/pdb_mmcif'/r['pdb_id'][1:3]/(r['pdb_id']+'.cif.gz')
        assert sha256(cif) == provenance['source_mmcif_sha256']
        with np.load(packet/'mapping.npz') as m,np.load(data/'gt.npz') as gt:
            for field, attr in [('atom_names','atom_name'),('chain_ids','chain_id'),('residue_ids','res_id')]:
                assert np.array_equal(m[field],getattr(native,attr))
            ri = m['residue_ids'].astype(int)-1; ai = np.array([ATOM37_INDEX[str(n)] for n in m['atom_names']])
            seen = gt['residue_mask'][ri] & gt['atom37_mask'][ri,ai]
            assert np.array_equal(seen,m['mask']) and seen.mean() >= .9
            assert np.array_equal(m['coordinates'][seen],gt['atom37_positions'][ri,ai][seen])
            assert np.isfinite(m['coordinates'][seen]).all() and np.all(m['coordinates'][~seen] == 0)
            assert seen[np.isin(m['atom_names'],['N','CA','C','O'])].all()
            assert len(set(zip(m['chain_ids'],m['residue_ids'],m['atom_names']))) == len(ri)
            new_audit.append(dict(group_id=g,pdb_id=r['pdb_id'],length=len(r['sequence']),
                native_atoms=len(ri),observed_atoms=int(seen.sum()),assembly_protein_instances=r['source_assembly_composition']['protein_chain_instance_count']))
        selected.append(r | dict(role='train',extension_inherited=False,source=str(data),
            chemistry_packet=str(packet),observed_heavy_fraction=by_id[g]['observed_heavy_fraction']))
    assert len({r['group_id'] for r in selected}) == len(selected)
    for r in additions:
        assert r['group_id'] not in {s['group_id'] for s in lock['references']}
        assert r['pdb_id'].lower() not in lock['excluded_pdbs']
        assert not set(r['accessions']).intersection(lock['excluded_accessions'])
    for a,b in itertools.combinations(additions,2):
        assert a['pdb_id'] != b['pdb_id'] and not set(a['accessions']).intersection(b['accessions'])
        assert tuple(sorted((a['extension_index'],b['extension_index']))) not in independent_edges
    write_json(root/'selection.json',selected)
    # Enumerate selected directories explicitly so inherited symlink targets are included.
    manifest = {str(p.relative_to(root)):sha256(p) for r in selected for folder in ['chemistry','data/examples']
                for p in (root/folder/r['group_id']).iterdir() if p.is_file()}
    write_json(root/'data_manifest.json',manifest)
    write_json(root/'selection_lock.json',dict(complete=len(selected)==512,selected=len(selected),
        inherited=len(prior),additional=len(additions),shortfall=512-len(selected),
        selection_sha256=sha256(root/'selection.json'),data_manifest_sha256=sha256(root/'data_manifest.json'),
        admission_lock_sha256=sha256(root/'admission_lock.json'),training_started=False))
    write_json(root/'audit.json',dict(verified_sources=True,selection_complete=len(selected)==512,
        selection_lock_sha256=sha256(root/'selection_lock.json'),selected=len(selected),new_rows=new_audit,
        parent_audit_sha256=sha256(parent/'expanded_audit.json'),hsps_independently_reparsed=nhsps,
        eligible=len(eligible),qualified=sum(r['passed'] for r in outcomes),additional=len(additions),
        shortfall=512-len(selected),seconds=time.monotonic()-begin,training_started=False,
        scope='Separate HSP parser and source-mapping assertions; not an independent code implementation of the native chemistry preflight'))


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    complete_folding_catalog_extension(p.parse_args().root.resolve())
