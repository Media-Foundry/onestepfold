"""Independent coordinate scoring, split-aware summaries and checkpoint replay."""
import argparse
import gzip
import json
import time
from pathlib import Path

import numpy as np
import torch

from fastglycan import stage0_confirm_runtime as rt
from fastglycan.adapter_supervision import build_adapter_supervision
from fastglycan.backbone_sequence_task import backbone_target_pairs, backbone_target_loss
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.functional_response_rank import (
    ranking_fidelity, prepare_fidelity_pairs, response_structure_metrics, response_geometry,
)
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_metrics import distance_response_summary, summarize_editor_sites, paired_parent_interval
from fastglycan.reference_editor_multiref import validate_multiref_plan


def score_multiref_run(root, run_id):
    started = time.monotonic(); torch.set_num_threads(1)
    lock = rt.load_json(root/'lock.json'); plan = rt.load_json(root/'plan.json')
    assert sha256(root/'plan.json') == lock['plan_sha256']
    validate_multiref_plan(plan)
    output = root/'runs'/run_id
    report = rt.load_json(output/'report.json')
    assert report['complete'] and rt.load_json(root/f'execution_{run_id}.json')['complete']
    run = report['run']
    assert report['counts']['updates'] == run['updates'] and report['counts']['c4'] == report['counts']['input_embedder'] == 0
    assert sha256(output/'history.jsonl') == report['history_sha256']
    expected_steps = set(run['checkpoints'])
    if run['additional_equal_update_checkpoint'] is not None:
        expected_steps.add(run['additional_equal_update_checkpoint'])
    assert {e['step'] for e in report['evaluations']} == expected_steps
    arms = ['exact', 'reference_only', *[str(x) for x in sorted(expected_steps)]]
    for e in report['evaluations']:
        assert sha256(output/e['checkpoint']) == e['sha256']
        record = rt.load_json(output/f"evaluation_{e['step']}.json")
        assert len(record['predictions']) == 912
        for p in record['predictions']:
            assert sha256(output/p['path']) == p['sha256']
    preflight = rt.load_json(root/'preflight.json'); assert preflight['complete']
    for p in preflight['baseline']:
        assert sha256(root/p['path']) == p['sha256']
    store = FactorTeacherStore(lock['teachers'])
    records, all_outputs, chemistry = [], [], {}
    role_key = 'role_n3' if run_id.startswith('n3_') else 'role_n15'
    for site in plan['sites']:
        pi, pos = site['parent_index'], site['position_zero_based']
        choices = site['candidates']; sequence = store.rows[pi]['sequence']
        gt_info = store.lock['gt'][str(pi)]
        assert sha256(Path(gt_info['path'])) == gt_info['sha256']
        gt = dict(np.load(gt_info['path'])); gca = gt['atom_names'] == 'CA'
        y, observed = gt['coordinates'][gca], gt['mask'][gca]
        assert len(y) == len(sequence)
        task_pairs, task_distances = backbone_target_pairs(y, observed)
        local = np.linalg.norm(y-y[pos], axis=-1) <= 8; local[pos] = True
        ii, jj = np.triu_indices(len(sequence), 3)
        wt = store.load(pi); wt_ca = np.flatnonzero(wt['inventory']['atom_names'] == 'CA')
        reference_distances = np.linalg.norm(wt['coordinates'][:, wt_ca[ii]]-wt['coordinates'][:, wt_ca[jj]], axis=-1)
        tasks = {arm: np.zeros((2, 19)) for arm in arms}
        distances = {arm: np.zeros((2, 19, len(ii))) for arm in arms}
        site_outputs = []
        for ai, aa in enumerate(choices):
            label = f'p{pi}_s{pos+1}_{aa}'
            inv = dict(np.load(store.path(pi, label, 'inventory.npz')))
            exact = np.load(store.path(pi, label, 'coordinates.npz'))['coordinates'][0]
            target_sequence = sequence[:pos]+aa+sequence[pos+1:]
            labels = build_adapter_supervision(dict(inv, coordinates=exact[0], mask=np.ones(len(inv['atom_names']), bool)), inv['bonds'], target_sequence)
            ca = np.flatnonzero(inv['atom_names'] == 'CA'); residues = inv['residue_ids']
            assert len(ca) == len(sequence)
            assert np.array_equal(residues[ca], wt['inventory']['residue_ids'][wt_ca])
            centres = np.asarray(labels['centres']); reference_volumes = np.asarray(labels['volumes'])
            chemistry[label] = dict(centres=centres.tolist(), reference_volumes=reference_volumes.tolist(),
                                     centre_atom_names=inv['atom_names'][centres].tolist(),
                                     centre_residues=residues[centres].tolist())
            xyz = {'exact': exact, 'reference_only': np.load(root/'baseline'/f'{label}.npz')['coordinates']}
            for arm in arms[2:]:
                xyz[arm] = np.load(output/'coordinates'/f'{arm}_{label}.npz')['coordinates']
            for ni, noise in enumerate(store.lock['seeds']):
                caches = (prepare_fidelity_pairs(exact[ni], residues), prepare_fidelity_pairs(exact[ni, ca], residues[ca]))
                eg = response_geometry(exact[ni], labels)['zero_severe_strict_checked_chirality']
                bg = response_geometry(xyz['reference_only'][ni], labels)['zero_severe_strict_checked_chirality']
                for arm in arms:
                    x = xyz[arm][ni]
                    assert x.shape == exact[ni].shape and np.isfinite(x).all()
                    task = float(backbone_target_loss(torch.tensor(x, dtype=torch.float64), ca, task_pairs, task_distances))
                    tasks[arm][ni, ai] = task
                    distances[arm][ni, ai] = np.linalg.norm(x[ca[ii]]-x[ca[jj]], axis=-1)
                    geometry = response_geometry(x, labels)
                    good = geometry['zero_severe_strict_checked_chirality']
                    fidelity = response_structure_metrics(x, exact[ni], ca, local, caches)
                    a, b, c, d = centres.T
                    volumes = (np.cross(x[b]-x[a], x[c]-x[a])*(x[d]-x[a])).sum(1)
                    edges = np.asarray(inv['bonds'])[:, :2]
                    lengths = np.linalg.norm(x[edges[:, 0]]-x[edges[:, 1]], axis=-1)
                    peptide = residues[edges[:, 0]] != residues[edges[:, 1]]
                    row = dict(site_key=site['site_key'], label=label, parent=pi, position=pos,
                               role=site[role_key], aa=aa, noise=int(noise), arm=arm, task=task,
                               geometry=geometry, fidelity=fidelity,
                               exact_pass_to_fail=bool(eg and not good), exact_fail_to_pass=bool(not eg and good),
                               reference_pass_to_fail=bool(bg and not good), reference_fail_to_pass=bool(not bg and good),
                               signed_volumes=volumes.tolist(),
                               reference_oriented_volume_ratio=(volumes*np.sign(reference_volumes)/np.maximum(abs(reference_volumes), 1e-12)).tolist(),
                               bond_length_min=float(lengths.min()), bond_length_max=float(lengths.max()),
                               peptide_cn_rmse_from_1p33=float(np.sqrt(np.mean((lengths[peptide]-1.33)**2))))
                    site_outputs.append(row)
        for arm in arms:
            ranks = [ranking_fidelity(tasks['exact'][ni], tasks[arm][ni]) for ni in range(2)]
            selected = int(np.argmin(tasks[arm][0]))
            rows = [r for r in site_outputs if r['arm'] == arm]
            locals_ = np.array([r['fidelity']['local_ca_rmsd_global_frame'] for r in rows])
            records.append(dict(site_key=site['site_key'], parent=pi, position=pos, pdb=site['pdb_id'],
                                role=site[role_key], original_aa=site['original_aa'], arm=arm, ranking=ranks,
                                tasks=tasks[arm].tolist(),
                                aggregate_ranking=ranking_fidelity(tasks['exact'].mean(0), tasks[arm].mean(0)),
                                old_selected=choices[selected], old_select_new_regret=float(tasks['exact'][1, selected]-tasks['exact'][1].min()),
                                local_mean=float(locals_.mean()), local_max=float(locals_.max()),
                                aa_lddt=float(np.mean([r['fidelity']['all_atom_lddt'] for r in rows])),
                                ca_lddt=float(np.mean([r['fidelity']['ca_lddt'] for r in rows])),
                                response=[distance_response_summary(distances['exact'][ni], distances[arm][ni], reference_distances[ni]) for ni in range(2)]))
        all_outputs.extend(site_outputs)
        print('SCORED_SITE', run_id, site['site_key'], flush=True)
    summary = {}
    for role in sorted({r['role'] for r in records}):
        summary[role] = {}
        for arm in arms:
            rows = [r for r in records if r['role'] == role and r['arm'] == arm]
            outputs = [r for r in all_outputs if r['role'] == role and r['arm'] == arm]
            summary[role][arm] = summarize_editor_sites(rows, outputs)
    terminal = str(run['updates'])
    held = summary['dev_unseen_protein']
    contrasts = {field: paired_parent_interval(held[terminal]['parent_summaries'], held['reference_only']['parent_summaries'], field) for field in ['spearman', 'regret']}
    result = dict(complete=True, run=run, summary=summary, sites=records, outputs=all_outputs,
                  chemistry=chemistry, held_terminal_vs_reference_only=contrasts,
                  report_sha256=sha256(output/'report.json'), audit_source_sha256=sha256(Path(__file__)),
                  metrics_source_sha256=sha256(Path(__import__('fastglycan.reference_editor_metrics', fromlist=['x']).__file__)),
                  seconds=time.monotonic()-started, independent_confirmation=False)
    with gzip.open(output/'scores.json.gz', 'wt') as f:
        json.dump(result, f, allow_nan=False)
    write_json(output/'summary.json', {k: v for k, v in result.items() if k not in ['sites', 'outputs', 'chemistry']})
    print('SCORING_COMPLETE', run_id, result['seconds'], flush=True)


def replay_multiref_run(root, run_id):
    from fastglycan.reference_editor_runtime import MiniEditorRuntime
    from fastglycan.reference_editor_multiref import paired_reference_editor
    runtime = MiniEditorRuntime(root, f'replay_{run_id}')
    output = root/'runs'/run_id
    report = rt.load_json(output/'report.json'); assert report['complete']
    site = runtime.sites['p3_s37']; aa = site['candidates'][0]
    item = runtime.item(3, 36, aa); records = []
    with torch.no_grad():
        for e in report['evaluations']:
            path = output/e['checkpoint']; assert sha256(path) == e['sha256']
            checkpoint = torch.load(path, map_location='cpu', weights_only=False)
            net = paired_reference_editor(checkpoint['architecture'], report['run']['seed'], checkpoint['config']).cuda().eval()
            net.load_state_dict(checkpoint['state_dict'], strict=True)
            reference = net.prepare_reference(runtime.references[3], runtime.sequences[3])
            conditioning = net(reference, runtime.edits(site, [aa]))
            old = np.load(output/'coordinates'/f"{e['step']}_{item['label']}.npz")['coordinates']
            for ni in range(2):
                new = runtime.decode(item, tuple(t[0] for t in conditioning), ni).cpu().numpy()
                assert np.array_equal(new, old[ni]), (run_id, e['step'], ni, float(np.max(np.abs(new-old[ni]))))
            records.append(dict(step=e['step'], coordinate_bitwise=True, checkpoint_sha256=e['sha256']))
            del net, reference, conditioning, checkpoint
    runtime.finish_checks()
    write_json(output/'checkpoint_replay.json', dict(complete=True, records=records, counts=runtime.counts,
               runtime=runtime.runtime, audit_source_sha256=sha256(Path(__file__))))
    print('REPLAY_COMPLETE', run_id, len(records), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True)
    p.add_argument('--run-id', required=True); p.add_argument('--mode', choices=['score', 'replay'], required=True)
    a = p.parse_args()
    (score_multiref_run if a.mode == 'score' else replay_multiref_run)(a.root, a.run_id)
