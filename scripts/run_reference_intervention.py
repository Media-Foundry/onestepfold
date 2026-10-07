"""Frozen student-only conditioning intervention; no training or candidate trunk."""
import argparse
import gzip
import json
import time
from pathlib import Path

import numpy as np
import torch

from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_intervention import (
    ARMS, fixed_candidate_derangement, mean_candidate_conditioning, intervention_conditioning,
)


def intervention_lock(root):
    lock = rt.load_json(root/'intervention_lock.json')
    for path, digest in lock['code'].items():
        assert sha256(root/'audit_code'/path) == digest, path
    assert sha256(root/'protocol.md') == lock['protocol_sha256']
    source = Path(lock['source_root'])
    for path, digest in lock['source_files'].items():
        assert sha256(source/path) == digest, path
    plan = rt.load_json(source/'plan.json')
    expected = [s for s in plan['sites'] if s['role_n15'] == s['role_n3'] == 'dev_unseen_protein']
    assert lock['sites'] == expected and len(expected) == 18
    assert len({s['parent_index'] for s in expected}) == 9
    for s in expected:
        assert lock['donors'][s['site_key']] == fixed_candidate_derangement(s['site_key'], s['candidates'])
    assert len(lock['runs']) == 4 and all(r['architecture'] == 'workspace' for r in lock['runs'])
    return lock, source


def decode_intervention(root, run_id):
    from fastglycan.reference_editor_runtime import MiniEditorRuntime
    from fastglycan.reference_editor_multiref import paired_reference_editor, editor_state_digest
    started = time.monotonic()
    lock, source = intervention_lock(root)
    run = next(r for r in lock['runs'] if r['run_id'] == run_id)
    old = source/'runs'/run_id
    previous = rt.load_json(old/'report.json')
    terminal = next(e for e in previous['evaluations'] if e['step'] == run['updates'])
    cp_path = old/terminal['checkpoint']
    assert sha256(cp_path) == terminal['sha256']
    prior_files = rt.load_json(old/f"evaluation_{run['updates']}.json")['predictions']
    prior_files = {p['label']: p for p in prior_files}
    runtime = MiniEditorRuntime(root, f'work_{run_id}')
    cp = torch.load(cp_path, map_location='cpu', weights_only=False)
    assert cp['architecture'] == 'workspace' and cp['step'] == run['updates']
    net = paired_reference_editor('workspace', run['seed'], cp['config']).cuda().eval()
    net.load_state_dict(cp['state_dict'], strict=True)
    before = editor_state_digest(net)
    output = root/'runs'/run_id
    output.mkdir(parents=True, exist_ok=False)
    (output/'coordinates').mkdir()
    records, decompositions = [], []
    with torch.no_grad():
        for site in lock['sites']:
            pi, pos = site['parent_index'], site['position_zero_based']
            ref = net.prepare_reference(runtime.references[pi], runtime.sequences[pi])
            predictions = []
            for start in range(0, 19, 4):
                aas = site['candidates'][start:start+4]
                tensors = net(ref, runtime.edits(site, aas))
                predictions.extend(tuple(t[i].cpu() for t in tensors) for i in range(len(aas)))
                del tensors
            common, energy = mean_candidate_conditioning(tuple(t.cpu() for t in runtime.references[pi]), predictions)
            donors = lock['donors'][site['site_key']]
            decompositions.append(dict(site_key=site['site_key'], blocks=energy, donors=donors))
            for ai, aa in enumerate(site['candidates']):
                item = runtime.item(pi, pos, aa)
                previous_file = prior_files[item['label']]
                assert sha256(old/previous_file['path']) == previous_file['sha256']
                expected = np.load(old/previous_file['path'])['coordinates']
                for arm in ARMS:
                    cond = intervention_conditioning(predictions, common, donors, arm, ai)
                    cond = tuple(t.cuda() for t in cond)
                    xyz = np.stack([runtime.decode(item, cond, ni).cpu().numpy() for ni in range(2)])
                    assert np.isfinite(xyz).all()
                    if arm == 'correct':
                        assert np.array_equal(xyz, expected), (run_id, item['label'], float(np.max(abs(xyz-expected))))
                    path = output/'coordinates'/f'{arm}_{item["label"]}.npz'
                    np.savez_compressed(path, coordinates=xyz)
                    records.append(dict(label=item['label'], site_key=site['site_key'], arm=arm,
                                        actual_aa=aa, donor_aa=site['candidates'][donors[ai]] if arm == 'shuffled' else None,
                                        path=str(path.relative_to(output)), sha256=sha256(path),
                                        correct_replay_bitwise=True if arm == 'correct' else None))
                    del cond
            del ref, predictions, common
            write_json(output/'progress.json', dict(completed_sites=len(decompositions), total_sites=18,
                       counts=runtime.counts, seconds=time.monotonic()-started))
            print('SITE_COMPLETE', run_id, site['site_key'], runtime.counts, flush=True)
    runtime.finish_checks(); intervention_lock(root)
    assert editor_state_digest(net) == before and all(p.grad is None for p in net.parameters())
    assert runtime.counts == dict(c4=0, input_embedder=0, s1=2052, updates=0)
    assert len(records) == 1026
    result = dict(complete=True, run=run, counts=runtime.counts, predictions=records,
                  decomposition=decompositions, original_outputs_replayed_bitwise=684,
                  checkpoint_sha256=sha256(cp_path), intervention_lock_sha256=sha256(root/'intervention_lock.json'),
                  parameter_digest_unchanged=before, runtime=runtime.runtime, seconds=time.monotonic()-started)
    write_json(output/'report.json', result)
    print('DECODE_COMPLETE', run_id, result['seconds'], flush=True)


def score_intervention(root, run_id):
    from fastglycan.adapter_supervision import build_adapter_supervision
    from fastglycan.backbone_sequence_task import backbone_target_pairs, backbone_target_loss
    from fastglycan.factor_student_data import FactorTeacherStore
    from fastglycan.functional_response_rank import (
        ranking_fidelity, prepare_fidelity_pairs, response_structure_metrics, response_geometry,
    )
    from fastglycan.reference_editor_metrics import (
        distance_response_summary, summarize_editor_sites, paired_parent_interval,
    )
    started = time.monotonic(); torch.set_num_threads(1)
    lock, source = intervention_lock(root)
    output = root/'runs'/run_id
    report = rt.load_json(output/'report.json'); assert report['complete']
    for p in report['predictions']:
        assert sha256(output/p['path']) == p['sha256']
    store = FactorTeacherStore(rt.load_json(source/'lock.json')['teachers'])
    baseline_manifest = {p['label']: p for p in rt.load_json(source/'preflight.json')['baseline']}
    arms = ['exact', 'reference_only', *ARMS]
    records, all_outputs, chemistry = [], [], {}
    for site in lock['sites']:
        pi, pos = site['parent_index'], site['position_zero_based']
        choices = site['candidates']; sequence = store.rows[pi]['sequence']
        gt_info = store.lock['gt'][str(pi)]
        assert sha256(Path(gt_info['path'])) == gt_info['sha256']
        gt = dict(np.load(gt_info['path'])); gca = gt['atom_names'] == 'CA'
        y, observed = gt['coordinates'][gca], gt['mask'][gca]
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
            assert np.array_equal(residues[ca], wt['inventory']['residue_ids'][wt_ca])
            centres = np.asarray(labels['centres']); volumes0 = np.asarray(labels['volumes'])
            chemistry[label] = dict(centres=centres.tolist(), reference_volumes=volumes0.tolist(),
                                   centre_atom_names=inv['atom_names'][centres].tolist(), centre_residues=residues[centres].tolist())
            assert sha256(source/baseline_manifest[label]['path']) == baseline_manifest[label]['sha256']
            xyz = {'exact': exact, 'reference_only': np.load(source/'baseline'/f'{label}.npz')['coordinates']}
            for arm in ARMS:
                xyz[arm] = np.load(output/'coordinates'/f'{arm}_{label}.npz')['coordinates']
            for ni, noise in enumerate(store.lock['seeds']):
                caches = (prepare_fidelity_pairs(exact[ni], residues), prepare_fidelity_pairs(exact[ni, ca], residues[ca]))
                eg = response_geometry(exact[ni], labels)['zero_severe_strict_checked_chirality']
                bg = response_geometry(xyz['reference_only'][ni], labels)['zero_severe_strict_checked_chirality']
                for arm in arms:
                    x = xyz[arm][ni]
                    task = float(backbone_target_loss(torch.tensor(x, dtype=torch.float64), ca, task_pairs, task_distances))
                    tasks[arm][ni, ai] = task
                    distances[arm][ni, ai] = np.linalg.norm(x[ca[ii]]-x[ca[jj]], axis=-1)
                    geometry = response_geometry(x, labels); good = geometry['zero_severe_strict_checked_chirality']
                    fidelity = response_structure_metrics(x, exact[ni], ca, local, caches)
                    a, b, c, d = centres.T
                    volumes = (np.cross(x[b]-x[a], x[c]-x[a])*(x[d]-x[a])).sum(1)
                    site_outputs.append(dict(site_key=site['site_key'], label=label, parent=pi, position=pos,
                        role='dev_unseen_protein', aa=aa, noise=int(noise), arm=arm, task=task,
                        geometry=geometry, fidelity=fidelity,
                        exact_pass_to_fail=bool(eg and not good), exact_fail_to_pass=bool(not eg and good),
                        reference_pass_to_fail=bool(bg and not good), reference_fail_to_pass=bool(not bg and good),
                        signed_volumes=volumes.tolist(), reference_oriented_volume_ratio=(volumes*np.sign(volumes0)/np.maximum(abs(volumes0),1e-12)).tolist()))
        for arm in arms:
            rows = [r for r in site_outputs if r['arm'] == arm]
            local_rmsd = np.array([r['fidelity']['local_ca_rmsd_global_frame'] for r in rows])
            selected = int(np.argmin(tasks[arm][0]))
            records.append(dict(site_key=site['site_key'], parent=pi, position=pos, pdb=site['pdb_id'], role='dev_unseen_protein',
                original_aa=site['original_aa'], arm=arm, tasks=tasks[arm].tolist(),
                ranking=[ranking_fidelity(tasks['exact'][ni], tasks[arm][ni]) for ni in range(2)],
                aggregate_ranking=ranking_fidelity(tasks['exact'].mean(0), tasks[arm].mean(0)),
                old_selected=choices[selected], old_select_new_regret=float(tasks['exact'][1,selected]-tasks['exact'][1].min()),
                local_mean=float(local_rmsd.mean()), local_max=float(local_rmsd.max()),
                aa_lddt=float(np.mean([r['fidelity']['all_atom_lddt'] for r in rows])),
                ca_lddt=float(np.mean([r['fidelity']['ca_lddt'] for r in rows])),
                response=[distance_response_summary(distances['exact'][ni], distances[arm][ni], reference_distances[ni]) for ni in range(2)]))
        all_outputs.extend(site_outputs)
        print('SCORE_SITE', run_id, site['site_key'], flush=True)
    summary = {arm: summarize_editor_sites([r for r in records if r['arm']==arm], [r for r in all_outputs if r['arm']==arm]) for arm in arms}
    contrasts = {f'{a}-{b}': {field: paired_parent_interval(summary[a]['parent_summaries'],summary[b]['parent_summaries'],field)
                            for field in ['spearman','regret','centered_response_rmse']}
                 for a,b in [('correct','common'),('correct','shuffled'),('correct','reference_only'),('common','reference_only'),('shuffled','reference_only')]}
    # Every correct score must reproduce the prior independent coordinate audit.
    prior = rt.load_json(source/'runs'/run_id/'summary.json')['summary']['dev_unseen_protein'][str(report['run']['updates'])]
    assert summary['correct'] == prior, (run_id, 'prior summary changed')
    result = dict(complete=True, run=report['run'], summary=summary, contrasts=contrasts,
                  sites=records, outputs=all_outputs, chemistry=chemistry, correct_summary_matches_previous=True,
                  report_sha256=sha256(output/'report.json'), independent_confirmation=False, promoted=False,
                  seconds=time.monotonic()-started)
    with gzip.open(output/'scores.json.gz','wt') as f:
        json.dump(result,f,allow_nan=False)
    write_json(output/'summary.json',{k:v for k,v in result.items() if k not in ['sites','outputs','chemistry']})
    print('SCORE_COMPLETE',run_id,result['seconds'],flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--mode',choices=['decode','score'],required=True)
    args=parser.parse_args()
    (decode_intervention if args.mode=='decode' else score_intervention)(args.root,args.run_id)
