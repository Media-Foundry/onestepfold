#!/usr/bin/env python3
"""Score saved local initialization and atom-centered changes; no model execution."""
import argparse
import concurrent.futures
import json
from pathlib import Path

import numpy as np

from fastglycan.independent_geometry_eval import experimental_quality
from fastglycan.independent_geometry_summary import atom_lddt, distribution
from fastglycan.paired_teacher_protocol import sha256, write_json

parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
root = args.root
assert (root / 'exit.json').exists()
original = json.loads((root / 'report.json').read_text())
panel = json.loads((root / 'panel32.json').read_text())
assert len(panel) == 32 and not any(row['errors'] for row in original['rows'])
args.out.mkdir(exist_ok=False)
write_json(args.out / 'lock.json', dict(
    report_sha256=sha256(root / 'report.json'),
    panel_sha256=sha256(root / 'panel32.json'),
    script_sha256=sha256(Path(__file__)),
    scope='posthoc saved-coordinate scoring; no new predictions, repair, or gate',
))


def score_protein(protein):
    group = protein['group_id']
    folder = root / 'proteins' / group
    packet = Path(protein['chemistry']['packet_dir']) / 'mapping.npz'
    assert sha256(packet) == protein['chemistry']['files']['mapping.npz']
    with np.load(packet) as handle:
        mapping = dict(handle)
    reports = {m: json.loads((folder / m / 'report.json').read_text()) for m in ['mean', 'tail']}
    mask = mapping['mask']
    residues = mapping['residue_ids'][mask]
    backbone = np.isin(mapping['atom_names'][mask], ['N', 'CA', 'C', 'O'])
    rows = []
    for seed in [300007, 300017, 300023]:
        old = next(x for x in original['rows'] if x['group_id'] == group and x['seed'] == seed)
        arrays = {}
        for method in ['mean', 'tail']:
            item = next(x for x in reports[method]['cases'] if x['seed'] == seed)
            assert item['success']
            path = folder / method / 'cases' / f"{item['case']:02d}" / 'coordinates.npz'
            assert sha256(path) == item['coordinates_sha256']
            with np.load(path) as handle:
                arrays[method] = dict(handle)
        assert np.array_equal(arrays['mean']['initial'], arrays['tail']['initial'])
        coordinates = dict(raw=arrays['mean']['raw'], initial=arrays['mean']['initial'],
                           mean=arrays['mean']['final'], tail=arrays['tail']['final'])
        quality = dict(old['quality'])
        quality['initial'] = experimental_quality(coordinates['initial'], mapping, protein['sequence'])
        per_atom = {stage: atom_lddt(x[mask], mapping['coordinates'][mask], residues)
                    for stage, x in coordinates.items()}
        valid = np.isfinite(per_atom['raw'])
        assert all(np.array_equal(np.isfinite(x), valid) for x in per_atom.values())
        for stage, values in per_atom.items():
            assert np.isclose(values[valid].mean(), quality[stage]['all_atom_lddt'], atol=1e-12, rtol=0)
        classes = {}
        for label, selected in [('backbone_centres', backbone), ('sidechain_centres', ~backbone)]:
            selected = selected & valid
            fraction = float(selected.sum() / valid.sum())
            classes[label] = dict(observed_atom_fraction=fraction,
                scores={stage: float(x[selected].mean()) if selected.any() else None
                        for stage, x in per_atom.items()},
                contribution_vs_raw={stage: float((x[selected] - per_atom['raw'][selected]).sum() / valid.sum())
                                     for stage, x in per_atom.items()})
        rows.append(dict(group_id=group, pdb_id=protein['pdb_id'], seed=seed,
                         quality=quality, atom_centres=classes))
    write_json(args.out / (group + '.json'), rows)
    print(protein['pdb_id'], 'scored', flush=True)
    return rows


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    rows = [row for batch in pool.map(score_protein, panel) for row in batch]
proteins = []
metrics = ['all_atom_lddt', 'ca_lddt', 'tm_score_ca_observed', 'ca_rmsd']
for protein in panel:
    selected = [x for x in rows if x['group_id'] == protein['group_id']]
    assert len(selected) == 3
    means = {stage: {metric: float(np.mean([x['quality'][stage][metric] for x in selected]))
                     for metric in metrics} for stage in ['raw', 'initial', 'mean', 'tail']}
    contributions = {label: {stage: float(np.mean([x['atom_centres'][label]['contribution_vs_raw'][stage]
                                                 for x in selected]))
                             for stage in means}
                     for label in ['backbone_centres', 'sidechain_centres']}
    proteins.append(dict(group_id=protein['group_id'], pdb_id=protein['pdb_id'],
                         quality=means, contribution_vs_raw=contributions))
summary = {}
for before, after in [('raw', 'initial'), ('initial', 'mean'), ('initial', 'tail'), ('mean', 'tail')]:
    name = after + '_minus_' + before
    summary[name] = {}
    for metric in metrics:
        values = np.asarray([p['quality'][after][metric] - p['quality'][before][metric] for p in proteins])
        record = distribution(values)
        rng = np.random.default_rng(20260929)
        record['bootstrap95'] = np.quantile(values[rng.integers(0, 32, (10000, 32))].mean(1), [.025, .975]).tolist()
        summary[name][metric] = record
write_json(args.out / 'report.json', dict(complete=True, instances=96, proteins=proteins,
    summary=summary, original_screen=original['screen'], rows=rows,
    scope='posthoc stage/atom-centred description; locked validation result unchanged'))
