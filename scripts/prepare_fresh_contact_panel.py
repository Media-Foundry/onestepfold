#!/usr/bin/env python3
"""Source-only isolated confirmation panel; never reads model/repair scores."""
import argparse
import concurrent.futures
import json
import multiprocessing
from pathlib import Path
import shutil
import traceback

import numpy as np

from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.sequence_isolation import read_hsps
from onestepfold.data.gt_materializer import materialize_entry
from preflight_isolated_chemistry import check


def qualify_fresh_contact_source(args):
    row, root, base = args
    g = row['group_id']; folder = root/'data/examples'/g
    folder.mkdir(parents=True, exist_ok=False)
    result = dict(group_id=g, pdb_id=row['pdb_id'], passed=False)
    try:
        source = Path(row['source'])
        for name, key in [('gt.json', 'metadata_sha256'), ('gt.npz', 'gt_sha256')]:
            assert sha256(source/name) == row[key]
        cif = base/'Dataset/raw/pdb_mmcif'/row['pdb_id'][1:3]/(row['pdb_id']+'.cif.gz')
        assert sha256(cif) == row['source_mmcif_sha256']
        arrays, meta = materialize_entry(row, cif)
        assert meta == json.loads((source/'gt.json').read_text())
        with np.load(source/'gt.npz') as archived:
            assert set(arrays) == set(archived.files)
            assert all(np.array_equal(value, archived[key]) for key, value in arrays.items())
        for name in ['gt.json', 'gt.npz']:
            shutil.copy2(source/name, folder/name)
        write_json(folder/'input_provenance.json', dict(sequence=row['sequence'],
            raw_gt_rebuild_exact=True, source_mmcif_sha256=sha256(cif)))
        write_json(folder/'prepared.json', dict(complete=True, files_sha256={
            name: sha256(folder/name) for name in ['gt.json', 'gt.npz', 'input_provenance.json']}))
        chemistry = check((row, root/'chemistry', base, root/'data'))
        result['chemistry'] = chemistry
        assert chemistry['passed'], chemistry.get('error')
        with np.load(root/'chemistry'/g/'mapping.npz') as mapped:
            assert mapped['mask'].all(), 'incomplete native heavy-atom GT'
        result.update(passed=True, source=str(folder), chemistry_packet=str(root/'chemistry'/g))
    except Exception:
        result['error'] = traceback.format_exc()
    write_json(folder/'source_preflight.json', result)
    return result


def prepare_fresh_contact_panel(base, root):
    assert not (root/'source_lock.json').exists()
    old = base/'connection_calibration_v1_20260930'
    ext = base/'connection_calibration_extension_v1_20260930'
    pool = json.loads((ext/'pool.json').read_text())
    prior = json.loads((old/'selection.json').read_text())
    calibration = json.loads((ext/'selection.json').read_text())
    assert len(calibration) == 64 and len(prior) == 43
    peers = pool + prior
    selected_ids = {r['group_id'] for r in calibration}
    selected_indices = {i for i, r in enumerate(peers) if r['group_id'] in selected_ids}
    pdbs = {r['pdb_id'] for r in calibration}
    accessions = {a for r in calibration for a in r['accessions']}
    # Parent locks bind all metadata-only reserved/development exclusion inputs.
    parent = json.loads((old/'source_lock.json').read_text())
    extension = json.loads((ext/'source_lock.json').read_text())
    for path, digest in parent['sources'].items():
        assert sha256(Path(path)) == digest
    for path, digest in extension['hashes'].items():
        assert sha256(Path(path)) == digest
    for directory in [old, ext]:
        assert all(not p.read_text().strip() for p in directory.glob('command_*.stderr'))
    bad = {int(h.query[1:]) for h in read_hsps(ext/'references.tsv') if h.evidence()['excluded']}
    edges = {tuple(sorted((int(h.query[1:]), int(h.subject[1:]))))
        for h in read_hsps(ext/'pairs.tsv') if h.query != h.subject and h.evidence()['excluded']}
    materialized = {r['group_id']: r for r in json.loads((ext/'materialization_report.json').read_text()) if r['passed']}
    candidates, exclusions = [], []
    for i, row in enumerate(pool):
        reasons = []
        if row['group_id'] in selected_ids: reasons.append('calibration_identity')
        if i in bad: reasons.append('historical_hsp')
        if row['group_id'] not in materialized: reasons.append('source_backbone_preflight')
        if row['pdb_id'] in pdbs or accessions.intersection(row['accessions']): reasons.append('calibration_pdb_accession')
        if any(tuple(sorted((i, j))) in edges for j in selected_indices): reasons.append('calibration_hsp')
        if reasons:
            exclusions.append(dict(index=i, group_id=row['group_id'], reasons=reasons))
        else:
            candidates.append(row | materialized[row['group_id']] | dict(pool_index=i))
    root.mkdir(parents=True, exist_ok=True); (root/'chemistry').mkdir()
    write_json(root/'candidates.json', candidates); write_json(root/'source_exclusions.json', exclusions)
    inputs = [old/'source_lock.json', old/'selection.json', ext/'source_lock.json', ext/'pool.json',
        ext/'selection.json', ext/'references.tsv', ext/'pairs.tsv', ext/'materialization_report.json',
        root/'candidates.json', root/'source_exclusions.json']
    inputs += [p for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py', '.md']]
    write_json(root/'source_lock.json', dict(method_commit='30301dd6', candidates=len(candidates),
        planned=8, source_hashes={str(p): sha256(p) for p in inputs},
        selection_rule='existing pool SHA order, first8 fully supported pairwise isolated',
        no_model_outputs=True, no_connection_measurements=True))
    print(json.dumps(dict(stage='source_locked', candidates=len(candidates))), flush=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context('spawn')) as executor:
        results = list(executor.map(qualify_fresh_contact_source, [(r, root, base) for r in candidates]))
    write_json(root/'preflight.json', results)
    outcomes = {r['group_id']: r for r in results}
    chosen, rejected = [], []
    for row in candidates:
        result = outcomes[row['group_id']]
        if not result['passed']:
            rejected.append(dict(group_id=row['group_id'], reason='native_chemistry_or_full_GT')); continue
        conflict = next((r['group_id'] for r in chosen if r['pdb_id'] == row['pdb_id'] or
            set(r['accessions']).intersection(row['accessions']) or
            tuple(sorted((r['pool_index'], row['pool_index']))) in edges), None)
        if conflict:
            rejected.append(dict(group_id=row['group_id'], reason='panel_isolation', conflict=conflict)); continue
        if len(chosen) < 8:
            chosen.append(row | dict(source=result['source'], chemistry=result['chemistry'],
                chemistry_packet=result['chemistry_packet']))
    write_json(root/'selection.json', chosen); write_json(root/'panel_rejections.json', rejected)
    artifacts = {str(p.relative_to(root)): sha256(p) for directory in ['chemistry', 'data']
        for p in (root/directory).rglob('*') if p.is_file()}
    write_json(root/'data_manifest.json', artifacts)
    write_json(root/'selection_lock.json', dict(complete=len(chosen)==8, planned=8, selected=len(chosen),
        candidates=len(candidates), native_full_GT_pass=sum(r['passed'] for r in results),
        selection_sha256=sha256(root/'selection.json'), preflight_sha256=sha256(root/'preflight.json'),
        source_lock_sha256=sha256(root/'source_lock.json'), manifest_sha256=sha256(root/'data_manifest.json'),
        folding_started=False, solver_started=False, noises=[400009,400031]))
    print(json.dumps(dict(stage='selected', selected=len(chosen), qualified=sum(r['passed'] for r in results))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['base', 'root']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); prepare_fresh_contact_panel(args.base, args.root)
