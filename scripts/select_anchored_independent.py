#!/usr/bin/env python3
"""Bounded source-only screening; no predictions or experimental scores are selected."""
import argparse
import concurrent.futures
import csv
import gzip
import hashlib
import json
import multiprocessing
import time
from pathlib import Path

import numpy as np
from onestepfold.data.sequence_identity import _new_homology_aligner, calculate_pairwise_identity

REFERENCES = []
ALIGNER = None
BINS = [(50, 127), (128, 255), (256, 511), (512, 1024)]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def near(first, second, aligner):
    p = calculate_pairwise_identity(first, second, aligner=aligner)
    return p.aligned_residue_count >= 50 and p.residue_identity >= .30 and p.shorter_sequence_coverage >= .70


def initialize_worker():
    global ALIGNER
    ALIGNER = _new_homology_aligner()


def audit_candidate(row):
    start = time.monotonic()
    for i, ref in enumerate(REFERENCES):
        if near(row['sequence'], ref['sequence'], ALIGNER):
            return dict(group_id=row['group_id'], passed=False, first_near=ref['group_id'], checked=i+1,
                        seconds=time.monotonic()-start)
    return dict(group_id=row['group_id'], passed=True, checked=len(REFERENCES), seconds=time.monotonic()-start)


def screen_structure(folder, row):
    prepared = json.loads((folder/'prepared.json').read_text())
    if not prepared['complete']:
        return 'incomplete_packet'
    for name in ['gt.json', 'gt.npz', 'input_provenance.json']:
        if digest(folder/name) != prepared['files_sha256'][name]:
            raise ValueError('source packet hash mismatch: ' + str(folder/name))
    meta = json.loads((folder/'gt.json').read_text())
    qa = meta['qa']
    if len(meta['chains']) != 1 or meta['chains'][0]['sequence'] != row['sequence']:
        return 'not_single_matching_chain'
    if qa['modified_residue_count'] or qa['chain_break_count'] or qa['backbone4_coverage'] < 1:
        return 'modified_broken_or_missing_backbone'
    # Disulfides are unsupported; identify observed SG contacts independently of
    # the native graph, which does not infer experimental crosslinks from sequence.
    from onestepfold.data.gt_materializer import ATOM37_INDEX
    with np.load(folder/'gt.npz') as arrays:
        mask = arrays['atom37_mask'][:, ATOM37_INDEX['SG']] & arrays['residue_mask']
        sg = arrays['atom37_positions'][mask, ATOM37_INDEX['SG']].astype(float)
        if len(sg) > 1:
            distances = np.linalg.norm(sg[:, None] - sg[None], axis=-1)
            if np.any(distances[np.triu_indices(len(sg), 1)] < 2.3):
                return 'observed_disulfide_or_sg_overlap'
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--workers', type=int, default=192)
    a = p.parse_args(); root = a.root; base = a.base
    if (root/'screen_lock.json').exists():
        raise ValueError('immutable screening root already locked')
    started = time.monotonic(); sources = {}
    def load(path):
        sources[str(path)] = digest(path)
        if path.suffix == '.gz':
            with gzip.open(path, 'rt') as f: return [json.loads(line) for line in f if line.strip()]
        return json.loads(path.read_text())
    data = base/'scratch_structure_data_v1_20260927'
    rows = load(data/'selection.json')
    accepted = load(data/'acceptance.json')
    assert accepted['complete']
    excluded = {r['group_id']: r for r in rows if r['split'] != 'train' or r['selection_index'] < 8192}
    teacher_files = sorted((base/'stage1b/teacher_pairs_v3/input').glob('*/metadata.jsonl.gz'))
    assert len(teacher_files) == 16
    teachers = [r for f in teacher_files for r in load(f)]
    assert len(teachers) == 16000 and len({r['group_id'] for r in teachers}) == 16000
    excluded.update({r['group_id']: r for r in teachers})
    extra = load(root/'input/development_ids.json')
    precision = load(base/'c4_s1_precision_crosshost_v1_20260927/manifest.json')
    excluded.update(precision)
    gates = load(base/'mini_sequence_gates_v1_20260928/gate_cases_v2.json')
    needed = set(extra['group_ids']) | {r['group'] for r in gates['cases']}
    catalog = {r['group_id']: r for r in load(base/'splits_v1/groups.jsonl.gz')}
    for g in sorted(needed):
        if g not in excluded:
            if g not in catalog: raise ValueError('unresolved development ID: ' + g)
            excluded[g] = catalog[g]
    # Catalog-only entries may not carry a representative PDB. Extra IDs retain
    # their source PDB IDs; all source records contribute conservative exclusions.
    pdbs = {str(r['pdb_id']).lower() for r in excluded.values() if r.get('pdb_id')} | set(extra['pdb_ids'])
    for r in gates['cases']: pdbs.add(r['pdb'].lower())
    sifts = base/'Dataset/raw/sifts/2026-09-08/pdb_chain_uniprot.csv.gz'
    sources[str(sifts)] = digest(sifts); accessions = {}
    with gzip.open(sifts, 'rt') as f:
        for row in csv.DictReader(line for line in f if not line.startswith('#')):
            accessions.setdefault(row['PDB'].lower(), set()).add(row['SP_PRIMARY'])
    denied_accessions = set().union(*(accessions.get(p, set()) for p in pdbs))
    references = []
    for g, r in sorted(excluded.items()):
        seq = r.get('sequence') or catalog.get(g, {}).get('sequence')
        if not seq: raise ValueError('no development sequence: ' + g)
        references.append(dict(group_id=g, sequence=seq))
    global REFERENCES
    REFERENCES = references
    rejection = {}; pools = []; screened = []
    eligible = [r for r in rows if r['split'] == 'train' and r['group_id'] not in excluded]
    rank = lambda r: hashlib.sha256(('anchored-independent-v1:20260929:' + r['group_id']).encode()).hexdigest()
    for bi, (lo, hi) in enumerate(BINS):
        selected = []
        for r in sorted((r for r in eligible if lo <= len(r['sequence']) <= hi), key=rank):
            reason = None; pdb = r['pdb_id'].lower(); acc = accessions.get(pdb, set())
            if pdb in pdbs: reason = 'development_pdb'
            elif not acc: reason = 'missing_sifts'
            elif acc & denied_accessions: reason = 'development_accession'
            elif not set(r['sequence']) <= set('ACDEFGHIKLMNPQRSTVWY'): reason = 'nonstandard_sequence'
            else: reason = screen_structure(data/'examples'/r['group_id'], r)
            screened.append(dict(group_id=r['group_id'], stratum=bi, exclusion=reason))
            if reason:
                rejection[reason] = rejection.get(reason, 0) + 1
                continue
            selected.append(dict(r, stratum=bi, accessions=sorted(acc)))
            if len(selected) == 64: break
        pools.extend(selected)
    write(root/'references.json', references)
    write(root/'screened.json', screened)
    write(root/'pool.json', pools)
    lock = dict(protocol_sha256=digest(root/'code/docs/mini_anchored_independent_v1.md'),
                source_sha256=digest(Path(__file__)), sources=sources, excluded_sequences=len(references),
                excluded_pdbs=sorted(pdbs), excluded_accessions=sorted(denied_accessions),
                pool_sha256=digest(root/'pool.json'), references_sha256=digest(root/'references.json'),
                strata=BINS, workers=a.workers, rejection_counts=rejection, gpu_inference_started=False)
    write(root/'screen_lock.json', lock)
    print(json.dumps(dict(stage='homology', pool=len(pools), references=len(references), rejections=rejection)), flush=True)
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers, mp_context=multiprocessing.get_context('fork'),
                                               initializer=initialize_worker) as executor:
        jobs = [executor.submit(audit_candidate, r) for r in pools]
        for job in concurrent.futures.as_completed(jobs):
            results.append(job.result())
            write(root/'homology_progress.json', dict(completed=len(results), total=len(pools), passed=sum(r['passed'] for r in results)))
    write(root/'homology.json', results)
    by_id = {r['group_id']: r for r in results}; chosen = []; pair_rejections = []
    aligner = _new_homology_aligner()
    for bi in range(4):
        count = 0
        for r in (r for r in pools if r['stratum'] == bi and by_id[r['group_id']]['passed']):
            conflict = next((s['group_id'] for s in chosen if set(s['accessions']) & set(r['accessions']) or
                             near(r['sequence'], s['sequence'], aligner)), None)
            if conflict:
                pair_rejections.append(dict(group_id=r['group_id'], conflict=conflict)); continue
            chosen.append(r); count += 1
            if count == 8: break
    write(root/'selection_provisional.json', chosen)
    write(root/'screen_report.json', dict(complete=True, panel_size_satisfied=len(chosen)==32,
        selected=len(chosen), strata_counts=[sum(r['stratum']==i for r in chosen) for i in range(4)],
        pair_rejections=pair_rejections, seconds=time.monotonic()-started,
        selection_sha256=digest(root/'selection_provisional.json'), lock_sha256=digest(root/'screen_lock.json'),
        status='native chemistry preflight and immutable inference lock still required', gpu_inference_started=False))


if __name__ == '__main__':
    main()
