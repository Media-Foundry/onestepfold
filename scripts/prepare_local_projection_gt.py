#!/usr/bin/env python3
"""Source-only screen and immutable eight-protein development selection; no fits."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np

from fastglycan.experimental_metrics import validate_experimental_record, prediction_atom37
from fastglycan.sequence_isolation import read_hsps
from onestepfold.data.gt_materializer import ATOM37_INDEX


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    ap = argparse.ArgumentParser()
    for key in ('root', 'bundle', 'structures', 'panel', 'calibration', 'blast', 'protocol'):
        ap.add_argument('--' + key, type=Path, required=True)
    a = ap.parse_args()
    a.root.mkdir(parents=True, exist_ok=False)
    bundle = json.loads((a.bundle / 'bundle_manifest.json').read_text())
    assert bundle['complete'] and len(bundle['selection']) == 640
    reserved = json.loads(a.panel.read_text())
    assert len(reserved) == 32
    reference_fasta = a.calibration / 'references.fasta'
    old_lock = json.loads((a.calibration / 'lock.json').read_text())
    assert digest(reference_fasta) == old_lock['references_fasta_sha256']
    dbsize = sum(len(line.strip()) for line in reference_fasta.read_text().splitlines()
                 if not line.startswith('>'))
    # Short stable BLAST IDs avoid identifier truncation; retain reversible aliases.
    aliases = {f's{i}': r['group_id'] for i, r in enumerate(bundle['selection'])}
    aliases.update({f'q{i}': r['group_id'] for i, r in enumerate(reserved)})
    for name, prefix, rows in [('sources', 's', bundle['selection']), ('reserved', 'q', reserved)]:
        (a.root / (name + '.fasta')).write_text(''.join(
            f'>{prefix}{i}\n{r["sequence"]}\n' for i, r in enumerate(rows)))
    tools = {}
    for name in ['blastp', 'makeblastdb']:
        path = a.blast / name
        assert digest(path) == old_lock['tools'][name]['sha256']
        tools[name] = dict(path=str(path), sha256=digest(path),
                           version=subprocess.check_output([str(path), '-version'], text=True))
    commands = [
        [str(a.blast / 'makeblastdb'), '-in', str(a.root / 'sources.fasta'), '-dbtype', 'prot',
         '-parse_seqids', '-out', str(a.root / 'db')],
        [str(a.blast / 'blastp'), '-task', 'blastp', '-query', str(a.root / 'reserved.fasta'),
         '-db', str(a.root / 'db'), '-out', str(a.root / 'isolation.tsv'), '-word_size', '3',
         '-matrix', 'BLOSUM62', '-gapopen', '11', '-gapextend', '1', '-seg', 'yes',
         '-comp_based_stats', '2', '-evalue', '.001', '-max_target_seqs', '640',
         '-num_threads', '4', '-dbsize', str(dbsize),
         '-outfmt', '6 qseqid sseqid qlen slen evalue qseq sseq'],
    ]
    write(a.root / 'preparation_lock.json', dict(
        bundle=str(a.bundle), structures=str(a.structures),
        inputs={str(p): digest(p) for p in [a.bundle / 'bundle_manifest.json', a.panel,
                a.protocol, Path(__file__), a.calibration / 'lock.json', reference_fasta]},
        tools=tools, commands=commands, dbsize=dbsize, aliases=aliases,
        scope='source selection only; no model prediction quality or fitted output selection'))
    for i, command in enumerate(commands):
        with (a.root / f'command_{i}.stdout').open('w') as out, \
                (a.root / f'command_{i}.stderr').open('w') as err:
            subprocess.run(command, stdout=out, stderr=err, check=True)
    assert not (a.root / 'command_1.stderr').read_text().strip(), 'BLAST stderr requires audit'
    near = {}
    for hsp in read_hsps(a.root / 'isolation.tsv'):
        evidence = hsp.evidence()
        if evidence['excluded']:
            near.setdefault(aliases[hsp.subject], []).append(
                dict(reserved_group=aliases[hsp.query], **evidence))
    predictions = {}
    for worker in range(4):
        report = json.loads((a.bundle / f'worker_{worker}/report.json').read_text())
        assert report['complete'] and report['weights_unchanged']
        assert report['bundle_manifest_sha256'] == digest(a.bundle / 'bundle_manifest.json')
        for row in report['predictions']:
            if row['condition'] == 'native_reference':
                key = (row['group_id'], row['noise'])
                assert key not in predictions
                predictions[key] = row
    groups = {r['group_id'] for r in reserved}
    pdbs = {r['pdb_id'].lower() for r in reserved}
    accessions = {x for r in reserved for x in r['accessions']}
    census, eligible = [], []
    for record in sorted(bundle['selection'], key=lambda r: r['group_id']):
        g, seq = record['group_id'], record['sequence']
        row = dict(group_id=g, pdb_id=record['pdb_id'], length=len(seq), reasons=[])
        reasons = row['reasons']
        if not 64 <= len(seq) <= 384:
            reasons.append('length_outside_development_range')
        if g in groups or record['pdb_id'].lower() in pdbs or g in near:
            reasons.append('reserved_identity_or_hsp')
        if reasons:
            census.append(row)
            continue
        try:
            folder = a.bundle / 'data' / g
            for name in ['gt.npz', 'inventory.npz', 'prepared.json']:
                assert digest(folder / name) == bundle['data_files'][g][name]
            prepared = json.loads((folder / 'prepared.json').read_text())
            gtjson = a.structures / 'examples' / g / 'gt.json'
            assert digest(gtjson) == prepared['files_sha256']['gt.json']
            meta = json.loads(gtjson.read_text())
            gt, inv = dict(np.load(folder / 'gt.npz')), dict(np.load(folder / 'inventory.npz'))
            validate_experimental_record(gt, meta, seq, record['sample_id'])
            assert meta['pdb_id'].lower() == record['pdb_id'].lower()
            acc = sorted({x['sp_primary'] for c in meta['chains'] for x in c['sifts_provenance']})
            row['accessions'] = acc
            if accessions.intersection(acc):
                reasons.append('reserved_accession')
            qa = meta['qa']
            if qa['backbone4_coverage'] != 1 or qa['chain_break_count'] or qa['modified_residue_count']:
                reasons.append('unsupported_backbone_or_modified_residue')
            # Construct indices only; never read unobserved coordinates for fitting.
            ri = inv['residue_id'] - 1
            ai = np.array([ATOM37_INDEX[n] for n in inv['atom_name']])
            assert ri.min() == 0 and ri.max() == len(seq) - 1
            observed = gt['atom37_mask'][ri, ai] & gt['residue_mask'][ri]
            row.update(native_atoms=len(ri), observed_native_atoms=int(observed.sum()))
            if not observed.all():
                reasons.append('missing_native_heavy_atom')
            if not reasons:
                coords = gt['atom37_positions'][ri, ai]
                _, mask = prediction_atom37(inv | {'coordinate': coords}, seq)
                assert int(mask.sum()) == len(ri) and np.isfinite(coords).all()
                sg = coords[inv['atom_name'] == 'SG']
                if len(sg) > 1 and np.any(np.linalg.norm(sg[:, None] - sg[None, :], axis=-1)[
                        np.triu_indices(len(sg), 1)] < 2.5):
                    reasons.append('apparent_disulfide')
            if not reasons:
                native = []
                for seed in [12345, 54321]:
                    pred = predictions[g, seed]
                    assert pred['counts'] == dict(trunk=1, structure=1, confidence=0)
                    assert pred['sampling']['noise_schedule'] == [2560., 0.]
                    params = pred['sampling']['parameters']
                    assert params['gamma0'] == 0 and params['step_scale_eta'] == 1
                    assert params['noise_scale_lambda'] == 1.003
                    path = a.bundle / pred['path']
                    assert path.resolve().is_relative_to(a.bundle.resolve())
                    assert digest(path) == pred['sha256']
                    x = np.load(path)
                    assert x.shape == (len(ri), 3) and np.isfinite(x).all()
                    native.append(pred)
                eligible.append(record | dict(accessions=acc, native_predictions=native,
                    gt_metadata=str(gtjson), gt_metadata_sha256=digest(gtjson),
                    native_atom_count=len(ri), hidden_context=meta['hidden_context'],
                    assembly_id=meta['assembly_id']))
        except Exception as exc:
            reasons.append('preflight_error: ' + repr(exc))
        census.append(row)
    selected, used_pdb, used_acc = [], set(), set()
    for record in eligible:
        if record['pdb_id'] in used_pdb or used_acc.intersection(record['accessions']):
            continue
        selected.append(record)
        used_pdb.add(record['pdb_id']); used_acc.update(record['accessions'])
        if len(selected) == 8:
            break
    write(a.root / 'census.json', census)
    write(a.root / 'excluded_hsps.json', near)
    write(a.root / 'selection.json', selected)
    for record in selected:
        dest = a.root / 'data' / record['group_id']
        dest.mkdir(parents=True)
        for name in ['gt.npz', 'inventory.npz', 'prepared.json']:
            shutil.copy2(a.bundle / 'data' / record['group_id'] / name, dest / name)
        shutil.copy2(record['gt_metadata'], dest / 'gt.json')
        for pred in record['native_predictions']:
            shutil.copy2(a.bundle / pred['path'], dest / f'native_{pred["noise"]}.npy')
    hashes = {str(p.relative_to(a.root)): digest(p) for p in sorted((a.root / 'data').rglob('*'))
              if p.is_file()} if selected else {}
    write(a.root / 'summary.json', dict(complete=len(selected) == 8, source_count=len(census),
        eligible_count=len(eligible), selected_count=len(selected), selected=[
            {k: r[k] for k in ['group_id', 'pdb_id', 'sequence_length', 'split']} for r in selected],
        excluded_hsp_groups=len(near), files_sha256=hashes,
        selection_sha256=digest(a.root / 'selection.json'),
        chemical_reference_preflight='pending; no fitting or model inference executed',
        no_independent_validation_claim=True))
    print(json.dumps(dict(eligible=len(eligible), selected=len(selected), directory=str(a.root))))
    assert len(selected) == 8, 'insufficient eligible sources; do not relax selection'


if __name__ == '__main__':
    main()
