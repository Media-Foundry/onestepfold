#!/usr/bin/env python3
"""Outcome-blind source selection for experimental backbone calibration."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.sequence_isolation import read_hsps
from onestepfold.data.gt_materializer import ATOM37_INDEX


def prepare_connection_calibration():
    p = argparse.ArgumentParser()
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--root', type=Path, required=True)
    a = p.parse_args(); b, root = a.base, a.root
    assert not (root / 'source_lock.json').exists()
    sources = {}
    def load(path):
        sources[str(path)] = sha256(path)
        return json.loads(path.read_text())
    data = b / 'scratch_structure_data_v1_20260927'
    rows = load(data / 'selection.json')
    assert load(data / 'acceptance.json')['complete']
    old = b / 'anchored_independent_v1_20260929'
    refs = load(old / 'references.json'); oldlock = load(old / 'screen_lock.json')
    refmap = {r['group_id']: r for r in refs}
    assert len(refmap) == 21070
    dbsize = sum(len(r['sequence']) for r in refs)
    pdbs, accs = set(oldlock['excluded_pdbs']), set(oldlock['excluded_accessions'])
    for path in [b / 'independent32_v2_20260930/panel32.json',
                 b / 'local_fit_gt_source_v1_20260930/selection.json']:
        for r in load(path):
            refmap[r['group_id']] = r
            pdbs.add(r['pdb_id'].lower()); accs.update(r['accessions'])
    rank = lambda r: hashlib.sha256(('connection-calibration-v1:20260930:' + r['group_id']).encode()).hexdigest()
    pool, census = [], []
    for stratum in [0, 1]:
        n = 0
        candidates = [r for r in rows if r['split'] == 'train' and
                      r.get('resolution_high_angstrom') is not None and
                      0 < r['resolution_high_angstrom'] <= 2 and
                      int(r['resolution_high_angstrom'] > 1.5) == stratum and
                      50 <= len(r['sequence']) <= 1024]
        for r in sorted(candidates, key=rank):
            g = r['group_id']; reason = None
            if g in refmap or r['pdb_id'].lower() in pdbs:
                reason = 'historical_or_reserved_identity'
            elif not set(r['sequence']) <= set('ACDEFGHIKLMNPQRSTVWY'):
                reason = 'noncanonical_sequence'
            else:
                try:
                    f = data / 'examples' / g
                    prep = load(f / 'prepared.json'); assert prep['complete']
                    for name in ['gt.json', 'gt.npz']:
                        assert sha256(f / name) == prep['files_sha256'][name]
                        sources[str(f / name)] = prep['files_sha256'][name]
                    m = load(f / 'gt.json'); qa = m['qa']
                    assert len(m['chains']) == 1 and m['chains'][0]['sequence'] == r['sequence']
                    chain = m['chains'][0]
                    accessions = sorted({x['sp_primary'] for x in chain['sifts_provenance']})
                    if not accessions or accs.intersection(accessions):
                        reason = 'missing_or_excluded_accession'
                    elif 'X-RAY DIFFRACTION' not in m['experimental']['methods']:
                        reason = 'not_xray'
                    elif qa['backbone4_coverage'] != 1 or qa['chain_break_count'] or qa['modified_residue_count']:
                        reason = 'incomplete_broken_or_modified_backbone'
                    else:
                        labels = [int(x['label_seq_id']) for x in chain['residues']]
                        assert labels == list(range(1, len(r['sequence']) + 1))
                        with np.load(f / 'gt.npz') as z:
                            ix = [ATOM37_INDEX[x] for x in ['N', 'CA', 'C', 'O']]
                            assert z['residue_mask'].all() and z['atom37_mask'][:, ix].all()
                            assert np.isfinite(z['atom37_positions'][:, ix]).all()
                        pool.append(r | dict(stratum=stratum, accessions=accessions,
                            source=str(f), hidden_context=m['hidden_context'],
                            metadata_sha256=sha256(f / 'gt.json'), gt_sha256=sha256(f / 'gt.npz')))
                        n += 1
                except Exception as exc:
                    reason = 'source_error: ' + repr(exc)
            census.append(dict(group_id=g, stratum=stratum, reason=reason))
            if n == 512:
                break
    write_json(root / 'pool.json', pool); write_json(root / 'census.json', census)
    refs = [refmap[g] for g in sorted(refmap)]
    for name, prefix, records in [('references', 'r', refs), ('pool', 'p', pool)]:
        (root / (name + '.fasta')).write_text(''.join(f'>{prefix}{i}\n{r["sequence"]}\n' for i, r in enumerate(records)))
    calibration = load(b / 'isolation_calibration_v2_1_20260930/lock.json')
    tools = calibration['tools']
    for info in tools.values():
        assert sha256(Path(info['path'])) == info['sha256']
    make, blast = tools['makeblastdb']['path'], tools['blastp']['path']
    commands = []
    for name in ['references', 'pool']:
        commands.append([make, '-in', str(root / (name + '.fasta')), '-dbtype', 'prot',
                         '-parse_seqids', '-out', str(root / (name + '_db'))])
        commands.append([blast, '-task', 'blastp', '-query', str(root / 'pool.fasta'),
                         '-db', str(root / (name + '_db')), '-out', str(root / (name + '_hsps.tsv')),
                         '-word_size', '3', '-matrix', 'BLOSUM62', '-gapopen', '11', '-gapextend', '1',
                         '-seg', 'yes', '-comp_based_stats', '2', '-evalue', '.001',
                         '-max_target_seqs', str(max(len(refs), len(pool))), '-num_threads', '16',
                         '-dbsize', str(dbsize), '-outfmt', '6 qseqid sseqid qlen slen evalue qseq sseq'])
    for file in (root / 'code').rglob('*'):
        if file.is_file() and file.suffix in ['.py', '.md']:
            sources[str(file)] = sha256(file)
    write_json(root / 'source_lock.json', dict(sources=sources, tools=tools, commands=commands,
        original_effective_dbsize=dbsize, actual_augmented_dbsize=sum(len(r['sequence']) for r in refs),
        references=[dict(group_id=r['group_id'], sequence=r['sequence']) for r in refs],
        pool_sha256=sha256(root / 'pool.json'), protocol='mini_connection_calibration_v1',
        no_connection_measurements=True))
    print(json.dumps(dict(stage='blast', pool=len(pool), references=len(refs))), flush=True)
    for i, command in enumerate(commands):
        with (root / f'command_{i}.stdout').open('w') as out, (root / f'command_{i}.stderr').open('w') as err:
            subprocess.run(command, stdout=out, stderr=err, check=True)
        assert not (root / f'command_{i}.stderr').read_text().strip(), 'Search stderr requires audit'
    near = {}; pairs = set()
    for h in read_hsps(root / 'references_hsps.tsv'):
        if h.evidence()['excluded']:
            near.setdefault(int(h.query[1:]), []).append(dict(reference=refs[int(h.subject[1:])]['group_id'], **h.evidence()))
    for h in read_hsps(root / 'pool_hsps.tsv'):
        i, j = int(h.query[1:]), int(h.subject[1:])
        if i != j and h.evidence()['excluded']:
            pairs.add(tuple(sorted((i, j))))
    chosen, used, used_pdb, used_acc, counts, rejects = [], [], set(), set(), [0, 0], []
    for i, r in enumerate(pool):
        s = r['stratum']
        if counts[s] >= 32:
            continue
        reason = None
        if i in near:
            reason = 'reference_hsp'
        elif r['pdb_id'] in used_pdb or used_acc.intersection(r['accessions']):
            reason = 'panel_identity'
        elif any(tuple(sorted((i, j))) in pairs for j in used):
            reason = 'panel_hsp'
        if reason:
            rejects.append(dict(group_id=r['group_id'], reason=reason)); continue
        chosen.append(r | dict(role='calibration' if counts[s] % 2 == 0 else 'held_out', pool_index=i))
        used.append(i); used_pdb.add(r['pdb_id']); used_acc.update(r['accessions']); counts[s] += 1
    write_json(root / 'reference_exclusions.json', near)
    write_json(root / 'panel_rejections.json', rejects)
    write_json(root / 'selection.json', chosen)
    hashes = {str(f): sha256(f) for f in root.iterdir() if f.is_file()}
    write_json(root / 'selection_lock.json', dict(source_lock_sha256=sha256(root / 'source_lock.json'),
        selected=len(chosen), strata_counts=counts, selection_sha256=sha256(root / 'selection.json'),
        sources=hashes, no_connection_measurements=True, complete=counts == [32, 32]))
    print(json.dumps(dict(stage='selected', selected=len(chosen), strata=counts)), flush=True)


if __name__ == '__main__':
    prepare_connection_calibration()
