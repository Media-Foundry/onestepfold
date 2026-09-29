#!/usr/bin/env python3
"""Fill the high-resolution calibration source gap from the full raw catalog."""
import argparse
import concurrent.futures
import gzip
import hashlib
import json
import multiprocessing
from pathlib import Path
import subprocess
import traceback

import numpy as np

from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.sequence_isolation import read_hsps
from onestepfold.data.gt_materializer import materialize_entry, ATOM37_INDEX


def scan_calibration_shard(path):
    result = []
    with gzip.open(path, 'rt') as handle:
        for line in handle:
            d = json.loads(line); e = d['experimental']; resolution = e.get('resolution_high_angstrom')
            if not resolution or not 0 < resolution <= 1.5 or e.get('model_count') != 1:
                continue
            if 'X-RAY DIFFRACTION' not in e.get('methods', []) or not e.get('initial_release_date') or e['initial_release_date'] > '2021-09-30':
                continue
            chains = {c['source_label_asym_id']: c for c in d['chains']}
            compositions = {c['assembly_id']: c for c in d['assembly_compositions']}
            for assembly in d['assemblies']:
                if assembly['definition_source'] not in ['author_determined', 'author_and_software']:
                    continue
                comp = compositions.get(assembly['assembly_id'])
                if not comp or comp['nucleic_acid_chain_instance_count'] or comp['other_polymer_chain_instance_count']:
                    continue
                proteins = [chains[x] for x in comp['source_asym_ids'] if chains[x]['is_protein']]
                if not proteins or len({c['sequence'] for c in proteins}) != 1:
                    continue
                c = min(proteins, key=lambda x: x['source_label_asym_id']); seq = c['sequence']
                if not 50 <= len(seq) <= 1024 or not set(seq) <= set('ACDEFGHIKLMNPQRSTVWY'):
                    continue
                acc = sorted({x['sp_primary'] for x in c['sifts_provenance']})
                if not acc:
                    continue
                g = hashlib.sha256(seq.encode()).hexdigest()
                result.append(dict(group_id=g, pdb_id=d['pdb_id'], sequence=seq, sequence_length=len(seq),
                    sequence_sha256=g, source_label_asym_id=c['source_label_asym_id'], entity_id=c['entity_id'],
                    chain_record=c, experimental=e, asu_observations=d['asu_observations'],
                    resolution_high_angstrom=resolution, assembly_id=assembly['assembly_id'],
                    assembly_definition_source=assembly['definition_source'], source_assembly_composition=comp,
                    accessions=acc, stratum=0, split='connection_calibration_reserved', catalog_shard=str(path)))
    return result


def materialize_calibration_source(args):
    row, base, root = args
    folder = root / 'data' / row['group_id']; folder.mkdir(parents=True, exist_ok=False)
    result = dict(group_id=row['group_id'], passed=False)
    try:
        cif = base / 'Dataset/raw/pdb_mmcif' / row['pdb_id'][1:3] / (row['pdb_id'] + '.cif.gz')
        arrays, meta = materialize_entry(row, cif)
        second, meta2 = materialize_entry(row, cif)
        assert meta == meta2 and all(np.array_equal(v, second[k]) for k, v in arrays.items())
        np.savez_compressed(folder / 'gt.npz', **arrays); write_json(folder / 'gt.json', meta)
        qa = meta['qa']
        assert qa['backbone4_coverage'] == 1 and qa['chain_break_count'] == qa['modified_residue_count'] == 0
        ids = [ATOM37_INDEX[n] for n in ['N', 'CA', 'C', 'O']]
        assert arrays['residue_mask'].all() and arrays['atom37_mask'][:, ids].all()
        assert np.isfinite(arrays['atom37_positions'][:, ids]).all()
        result.update(passed=True, source=str(folder), metadata_sha256=sha256(folder / 'gt.json'),
                      gt_sha256=sha256(folder / 'gt.npz'), source_mmcif_sha256=sha256(cif))
    except Exception:
        result['error'] = traceback.format_exc()
    write_json(folder / 'preflight.json', result)
    return result


def extend_connection_calibration():
    p = argparse.ArgumentParser()
    for key in ['base', 'root', 'previous']:
        p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); b, root = a.base, a.root
    assert not (root / 'source_lock.json').exists()
    prior = json.loads((a.previous / 'selection.json').read_text()); assert len(prior) == 43
    poolold = json.loads((a.previous / 'pool.json').read_text())
    lock = json.loads((a.previous / 'source_lock.json').read_text())
    for file, digest in lock['sources'].items():
        assert sha256(Path(file)) == digest
    refs = lock['references']; denied = {r['group_id'] for r in refs + poolold}
    old = json.loads((b / 'anchored_independent_v1_20260929/screen_lock.json').read_text())
    pdbs, accs = set(old['excluded_pdbs']), set(old['excluded_accessions'])
    for file in [a.previous / 'selection.json', b / 'independent32_v2_20260930/panel32.json',
                 b / 'local_fit_gt_source_v1_20260930/selection.json']:
        for r in json.loads(file.read_text()):
            pdbs.add(r['pdb_id'].lower()); accs.update(r['accessions'])
    shards = sorted((b / 'catalog_v1').glob('shard-*.jsonl.gz')); assert len(shards) == 256
    hashes = {str(f): sha256(f) for f in shards + [a.previous / 'selection.json', a.previous / 'source_lock.json',
              root / 'code/docs/mini_connection_calibration_extension_v1.md', Path(__file__)]}
    reps = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=16) as ex:
        for part in ex.map(scan_calibration_shard, shards):
            for r in part:
                g = r['group_id']
                if g in denied or r['pdb_id'] in pdbs or accs.intersection(r['accessions']):
                    continue
                rank = lambda x: (x['resolution_high_angstrom'], x['pdb_id'], x['source_label_asym_id'], x['assembly_id'])
                if g not in reps or rank(r) < rank(reps[g]):
                    reps[g] = r
    ranked = sorted(reps.values(), key=lambda r: hashlib.sha256(('connection-calibration-v1:20260930:' + r['group_id']).encode()).hexdigest())
    candidates = ranked[:1024]
    write_json(root / 'pool.json', candidates)
    peers = candidates + prior
    for name, prefix, rows in [('queries', 'n', candidates), ('peers', 'n', peers)]:
        (root / (name + '.fasta')).write_text(''.join(f'>{prefix}{i}\n{r["sequence"]}\n' for i, r in enumerate(rows)))
    commands = []; tools = lock['tools']
    for info in tools.values():
        assert sha256(Path(info['path'])) == info['sha256']
    blast, make = tools['blastp']['path'], tools['makeblastdb']['path']
    commands.append([make, '-in', str(root / 'peers.fasta'), '-dbtype', 'prot', '-parse_seqids', '-out', str(root / 'peers_db')])
    for label, query, db in [('references', root / 'queries.fasta', a.previous / 'references_db'),
                              ('pairs', root / 'peers.fasta', root / 'peers_db')]:
        commands.append([blast, '-task', 'blastp', '-query', str(query), '-db', str(db),
            '-out', str(root / (label + '.tsv')), '-word_size', '3', '-matrix', 'BLOSUM62',
            '-gapopen', '11', '-gapextend', '1', '-seg', 'yes', '-comp_based_stats', '2',
            '-evalue', '.001', '-max_target_seqs', str(max(len(refs), len(peers))), '-num_threads', '16',
            '-dbsize', str(lock['original_effective_dbsize']), '-outfmt', '6 qseqid sseqid qlen slen evalue qseq sseq'])
    hashes[str(root / 'pool.json')] = sha256(root / 'pool.json')
    write_json(root / 'source_lock.json', dict(hashes=hashes, eligible_groups=len(reps), pool=len(candidates),
        commands=commands, tools=tools, no_connection_measurements=True))
    print(json.dumps(dict(stage='search', eligible_groups=len(reps), pool=len(candidates))), flush=True)
    for i, command in enumerate(commands):
        with (root / f'command_{i}.stdout').open('w') as out, (root / f'command_{i}.stderr').open('w') as err:
            subprocess.run(command, stdout=out, stderr=err, check=True)
        assert not (root / f'command_{i}.stderr').read_text().strip(), 'Search stderr requires audit'
    bad = {int(h.query[1:]) for h in read_hsps(root / 'references.tsv') if h.evidence()['excluded']}
    edges = {tuple(sorted((int(h.query[1:]), int(h.subject[1:])))) for h in read_hsps(root / 'pairs.tsv')
             if h.query != h.subject and h.evidence()['excluded']}
    eligible = [(i, r) for i, r in enumerate(candidates) if i not in bad and
                not any(tuple(sorted((i, j))) in edges for j in range(len(candidates), len(peers)))]
    write_json(root / 'eligible.json', [r for _, r in eligible])
    print(json.dumps(dict(stage='materialize', eligible=len(eligible))), flush=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=16, mp_context=multiprocessing.get_context('fork')) as ex:
        outcomes = list(ex.map(materialize_calibration_source, [(r, b, root) for _, r in eligible]))
    write_json(root / 'materialization_report.json', outcomes)
    good = {r['group_id']: r for r in outcomes if r['passed']}
    chosen, used = list(prior), []
    for i, r in eligible:
        if r['group_id'] not in good or r['pdb_id'] in pdbs or accs.intersection(r['accessions']):
            continue
        if any(tuple(sorted((i, j))) in edges for j in used):
            continue
        n = sum(x['stratum'] == 0 for x in chosen)
        chosen.append(r | good[r['group_id']] | dict(role='calibration' if n % 2 == 0 else 'held_out'))
        used.append(i); pdbs.add(r['pdb_id']); accs.update(r['accessions'])
        if len(chosen) == 64:
            break
    write_json(root / 'selection.json', chosen)
    write_json(root / 'selection_lock.json', dict(complete=len(chosen) == 64, selected=len(chosen),
        role_counts={role: sum(r['role'] == role for r in chosen) for role in ['calibration', 'held_out']},
        selection_sha256=sha256(root / 'selection.json'), source_lock_sha256=sha256(root / 'source_lock.json'),
        materialization_sha256=sha256(root / 'materialization_report.json'), no_connection_measurements=True))
    print(json.dumps(dict(stage='selected', selected=len(chosen))), flush=True)


if __name__ == '__main__':
    extend_connection_calibration()
