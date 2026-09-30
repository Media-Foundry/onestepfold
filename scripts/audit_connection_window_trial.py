#!/usr/bin/env python3
"""Independent saved-pose, geometry, quality, onset and objective audit."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from audit_anchored_geometry import replay
from audit_local_projection_gt import score
from fastglycan.anchored_geometry import PoseVariables
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.connection_audit import measure_connections, TOLERANCES
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.paired_teacher_protocol import sha256, write_json
from onestepfold.data.gt_materializer import ATOM37_INDEX


def audit_connection_window_trial(root):
    torch.set_num_threads(1)
    lock = json.loads((root / 'lock.json').read_text()); source = Path(lock['source'])
    fitted_trial = lock.get('initialization_contract') == 'calibrated_c4_fitted_start_v1'
    warm_trial = lock.get('initialization_contract') == 'calibrated_c4_sidechain_repulsion_start_v1'
    ideal_trial = warm_trial or lock.get('reference_contract') == 'calibrated_c4_ideal_reference_v1'
    reference_trial = ideal_trial or lock.get('reference_contract') == 'calibrated_c4_reference_lengths_v1'
    if 'reference_contract' in lock:
        assert reference_trial and not fitted_trial and lock['arms'] == ['native_ref', 'ideal_ref' if ideal_trial else 'length_ref']
    if 'initialization_contract' in lock:
        assert (fitted_trial and lock['arms'] == ['zero', 'fitted']) or (
            warm_trial and lock['arms'] == ['zero', 'sidechain'])
    selection = json.loads((source / 'selection.json').read_text())
    report = json.loads((root / 'report.json').read_text())
    calibration = json.loads(Path(lock['calibration']).read_text())['windows']
    assert report['complete'] and len(report['rows']) == report['expected'] == 32
    assert report['lock_sha256'] == sha256(root / 'lock.json')
    for path, digest in lock['hashes'].items():
        assert sha256(Path(path)) == digest
    outcomes = []
    for row in report['rows']:
        index = row['index']; item = selection[index // 4]; group = item['group_id']; packet = source / 'chemistry' / group
        if not row['success']:
            chemistry = json.loads((packet / 'report.json').read_text())
            outcomes.append(dict(index=index, verified=False, source_skipped=not chemistry['passed'],
                                 reason=row.get('source_failure', row.get('error', 'unknown'))))
            continue
        assert row['group_id'] == group and row['seed'] == [12345, 54321][(index // 2) % 2]
        assert row['arm'] == lock['arms'][index % 2]
        folder = root / 'cases' / f'{index:02d}'
        for file, key in [('coordinates.npz', 'coordinates_sha256'), ('values.pt', 'values_sha256')]:
            assert sha256(folder / file) == row[key]
        data = dict(np.load(folder / 'coordinates.npz')); mapping = dict(np.load(packet / 'mapping.npz'))
        gt = dict(np.load(source / 'data' / group / 'gt.npz')); inv = dict(np.load(source / 'data' / group / 'inventory.npz'))
        names, residues = data['atom_names'], data['residue_ids']; ca_mask = names == 'CA'
        assert np.array_equal(names, inv['atom_name']) and np.array_equal(residues, inv['residue_id'])
        ai = np.array([ATOM37_INDEX[n] for n in names]); ri = residues - 1
        assert (gt['atom37_mask'][ri, ai] & gt['residue_mask'][ri]).all()
        assert np.array_equal(data['target'], gt['atom37_positions'][ri, ai])
        assert np.array_equal(data['raw'], np.load(source / 'data' / group / f'native_{row["seed"]}.npy'))
        output_reference = mapping['reference'].copy()
        if reference_trial and row['arm'] == 'length_ref':
            parameters = json.loads(Path(lock['reference_parameters']).read_text())['parameters']
            for residue in range(2,len(item['sequence'])):
                ix = {n:int(np.flatnonzero((residues==residue)&(names==n))[0]) for n in ['CA','C','O']}
                p = parameters[item['sequence'][residue-1]]['metrics']; ca0,c0,o0 = mapping['reference'][[ix['CA'],ix['C'],ix['O']]]
                cnew = ca0+(c0-ca0)/np.sqrt(np.sum((c0-ca0)**2))*p['ca_c']['median']
                output_reference[ix['C']] = cnew
                output_reference[ix['O']] = cnew+(o0-c0)/np.sqrt(np.sum((o0-c0)**2))*p['c_o']['median']
            np.testing.assert_allclose(output_reference,data['output_reference'],rtol=0,atol=1e-12)
        if ideal_trial and (warm_trial or row['arm'] == 'ideal_ref'):
            templates = json.loads(Path(lock['reference_templates']).read_text())['records']
            for residue in range(2,len(item['sequence'])):
                ii = np.flatnonzero(residues == residue); nn = names[ii].tolist()
                template = templates[item['sequence'][residue-1]]
                xx = np.asarray(template['ideal'])[[template['atom_names'].index(n) for n in nn]]
                cc, ni, ci = [nn.index(n) for n in ['CA','N','C']]
                bases = []
                for points in [xx, mapping['reference'][ii]]:
                    a = points[ci]-points[cc]; a /= np.sqrt(a@a)
                    b = points[ni]-points[cc]; b -= a*(a@b); b /= np.sqrt(b@b)
                    bases.append(np.column_stack([a,b,np.cross(a,b)]))
                output_reference[ii] = (xx-xx[cc])@bases[0]@bases[1].T+mapping['reference'][ii[cc]]
            np.testing.assert_allclose(output_reference,data['output_reference'],rtol=0,atol=1e-12)
        adapter = ArticulatedOutput(output_reference, names, residues, item['sequence'],
            json.loads((packet / 'variants.json').read_text())).double()
        variables = PoseVariables(adapter, torch.tensor(data['raw']))
        values = torch.load(folder / 'values.pt', map_location='cpu', weights_only=True)
        if (not fitted_trial and not warm_trial) or row['arm'] == 'zero':
            assert all(torch.count_nonzero(v) == 0 for v in values['initial'])
        elif fitted_trial:
            fit = row['local_fit']
            assert fit['max_iter'] == 60 and fit['max_eval'] == 90 and fit['final_iterate']
            assert fit['iterations'] <= 60 and fit['seconds'] > 0
            for key, label in [('initial_mse', 'local'), ('final_mse', 'start')]:
                np.testing.assert_allclose(fit[key], ((data[label]-data['raw'])**2).sum(-1).mean(), rtol=1e-10, atol=1e-10)
        if warm_trial and row['arm'] == 'sidechain':
            warm_folder = Path(lock['warm_start_root']) / 'cases' / f'{index // 2:02d}'
            warm = json.loads((warm_folder / 'report.json').read_text())
            warm_values = torch.load(warm_folder / 'values.pt', weights_only=True, map_location='cpu')
            warm_data = dict(np.load(warm_folder / 'coordinates.npz'))
            assert warm['success'] and warm['group_id'] == group and warm['seed'] == row['seed']
            assert row['warm_start']['report_sha256'] == sha256(warm_folder / 'report.json')
            for file, key in [('coordinates.npz', 'coordinates_sha256'), ('values.pt', 'values_sha256')]:
                assert row['warm_start'][key] == warm[key] == sha256(warm_folder / file)
            for q, old_q, mask in zip(values['initial'], warm_values['values'], warm_values['masks'], strict=True):
                assert torch.equal(q, old_q) and torch.count_nonzero(q[:, :6]) == 0
                assert torch.count_nonzero(q * (~mask.bool())) == 0
            for key in ['raw', 'target', 'output_reference', 'atom_names', 'residue_ids']:
                assert np.array_equal(data[key], warm_data[key])
            assert np.array_equal(data['local'], warm_data['initial'])
            assert np.max(np.abs(data['start'] - warm_data['final'])) < 1e-8
            bone = np.isin(names, ['N','CA','C','O','OXT'])
            assert np.max(np.abs(data['start'][bone] - data['local'][bone])) < 1e-10
        error = 0.
        for label, key in [('start', 'initial'), ('final', 'final')]:
            with torch.no_grad():
                for parameter, value in zip(variables.variables, values[key], strict=True):
                    parameter.copy_(value)
            error = max(error, float(np.max(np.abs(replay(variables) - data[label]))))
        assert error < 1e-8
        reference_length_error = 0.
        if reference_trial and row['arm'] == 'length_ref':
            for residue in range(2,len(item['sequence'])):
                for a,b,key in [('CA','C','ca_c'),('C','O','c_o')]:
                    ia=int(np.flatnonzero((residues==residue)&(names==a))[0])
                    ib=int(np.flatnonzero((residues==residue)&(names==b))[0])
                    target=parameters[item['sequence'][residue-1]]['metrics'][key]['median']
                    for label in ['local','start','final']:
                        reference_length_error=max(reference_length_error,abs(np.linalg.norm(data[label][ia]-data[label][ib])-target))
            assert reference_length_error < 1e-8
        if ideal_trial and (warm_trial or row['arm'] == 'ideal_ref'):
            for residue in range(2,len(item['sequence'])):
                ii = np.flatnonzero(residues == residue); nn = names[ii].tolist()
                template = templates[item['sequence'][residue-1]]; tn = template['atom_names']
                for a,b,_ in template['bonds']:
                    ia,ib = ii[nn.index(tn[a])],ii[nn.index(tn[b])]
                    target = np.linalg.norm(output_reference[ia]-output_reference[ib])
                    for label in ['local','start','final']:
                        reference_length_error = max(reference_length_error,abs(np.linalg.norm(data[label][ia]-data[label][ib])-target))
            assert reference_length_error < 1e-8
        if lock['baseline'] is not None:
            previous = Path(lock['baseline']) / 'cases' / f'{index // 2 * 2 + int(fitted_trial or reference_trial):02d}'
            old = dict(np.load(previous / 'coordinates.npz'))
            if (not fitted_trial and not reference_trial) or row['arm'] in ['zero','native_ref']:
                assert np.max(np.abs(old['start'] - data['start'])) < 1e-8
            if not reference_trial or row['arm'] == 'native_ref':
                assert np.array_equal(old['local'], data['local'])
            else:
                unchanged = ~((residues>1)&(residues<len(item['sequence']))&np.isin(names,['C','O']))
                if ideal_trial:
                    unchanged = (residues==1) | (residues==len(item['sequence'])) | (names=='CA')
                assert np.max(np.abs(old['local'][unchanged]-data['local'][unchanged])) < 1e-8
                assert np.max(np.abs(data['local'][ca_mask]-data['raw'][ca_mask])) < 1e-8
            if row['arm'] in ['original', 'zero','native_ref']:
                assert np.max(np.abs(old['final'] - data['final'])) < 1e-8
            if ((fitted_trial or warm_trial) and row['arm'] == 'zero') or (reference_trial and row['arm'] == 'native_ref'):
                assert row['reused_control']['report_sha256'] == sha256(previous / 'report.json')
                assert row['coordinates_sha256'] == sha256(previous / 'coordinates.npz')
                assert row['values_sha256'] == sha256(previous / 'values.pt')
        else:
            assert lock.get('prediction_contract') == 'c4_s1_confirmation_v1'
            assert row['start_replay_max_abs'] is None
        atoms = torch.load(packet / 'native.pt', map_location='cpu', weights_only=False)['atoms']
        top = GeometryTopology(atoms, mapping['reference']); bonds = top.bonds.numpy(); pairs = top.pairs.numpy()
        ca, n, c, cb = top.centres.numpy().T
        anchors = np.array([[int(np.flatnonzero((residues == j) & (names == name))[0])
            for name in ['N', 'CA', 'C', 'O']] for j in range(1, len(item['sequence']) + 1)])
        side = np.array([[int(np.flatnonzero((residues == j) & (names == name))[0])
            for name in ['CB', 'CA', 'CG1' if aa == 'I' else 'OG1', 'CG2']]
            for j, aa in enumerate(item['sequence'], 1) if aa in 'IT'], dtype=int).reshape(-1, 4)
        sc, sa, sb, sd = side.T; ref = mapping['reference']
        side_ref = np.sum(np.cross(ref[sa]-ref[sc], ref[sb]-ref[sc])*(ref[sd]-ref[sc]), axis=1)
        raw_sign = measure_connections(data['raw'], anchors, item['sequence'])['nearest_omega_sign']
        gt_sign = measure_connections(data['target'], anchors, item['sequence'])['nearest_omega_sign']
        onsets = np.array([[calibration['Pro' if aa == 'P' else 'other']['windows'][term]['q95']['pooled']
                           if raw_sign[j] < 0 else .5 * t for j, aa in enumerate(item['sequence'][1:])]
                          for term, t in TOLERANCES.items()])
        if row['arm'] == 'calibrated' or fitted_trial or reference_trial:
            np.testing.assert_array_equal(onsets, row['connection_onsets'])
        assert row['raw_branch_mismatches'] == np.flatnonzero(raw_sign != gt_sign).tolist()
        metric_error = 0.; objective_error = 0.
        for label in ['raw', 'local', 'start', 'final']:
            x = data[label]; saved = row['metrics'][label]
            per, valid = score(x, data['target'], residues)
            perca, validca = score(x[ca_mask], data['target'][ca_mask], residues[ca_mask])
            checks = [(float(per[valid].mean()), saved['all_atom_lddt']), (float(perca[validca].mean()), saved['ca_lddt'])]
            bond = np.linalg.norm(x[bonds[:, 0]]-x[bonds[:, 1]], axis=1)-top.ideal.numpy()
            distances = np.linalg.norm(x[pairs[:, 0]]-x[pairs[:, 1]], axis=1)
            depths = top.radii.numpy()[pairs].sum(-1)-distances
            volume = np.sum(np.cross(x[n]-x[ca], x[c]-x[ca])*(x[cb]-x[ca]), axis=1)
            geometry = dict(bond_rmse=float(np.sqrt(np.mean(bond**2))),
                peptide_mae=float(np.abs(bond[top.peptide.numpy()]).mean()),
                chirality_fraction=float((volume*top.volumes.numpy() > 0).mean()),
                severe_pairs=int((distances < 1).sum()), severe_pairs_per_atom=float((distances < 1).sum()/len(x)),
                max_penetration=float(np.maximum(0, depths).max()))
            checks.extend((v, saved['geometry'][k]) for k, v in geometry.items())
            side_ok = bool((np.sum(np.cross(x[sa]-x[sc], x[sb]-x[sc])*(x[sd]-x[sc]), axis=1)*side_ref > 0).all())
            chirality = geometry['chirality_fraction'] == 1 and side_ok
            measured = measure_connections(x, anchors, item['sequence'], raw_sign)
            edges = measured['residuals']
            checks.extend((float(np.abs(v).max()), saved['connection_max'][k]) for k, v in edges.items())
            connected = all(np.abs(edges[k]).max() <= t+1e-6 for k, t in TOLERANCES.items())
            assert saved['branch_mismatches'] == np.flatnonzero(measured['nearest_omega_sign'] != gt_sign).tolist()
            squared = ((x-data['raw'])**2).sum(-1); hr = float(np.sqrt(squared.mean())); cr = float(np.sqrt(squared[ca_mask].mean()))
            checks += [(hr, saved['preservation']['heavy_rms']), (cr, saved['preservation']['ca_rms']),
                       (float(np.sqrt(squared.max())), saved['preservation']['max_displacement'])]
            budgets = hr <= 2 and cr <= 1
            accepted = geometry['bond_rmse'] <= .25 and geometry['peptide_mae'] <= .15 and geometry['max_penetration'] <= 2 and geometry['severe_pairs_per_atom'] <= .02 and chirality and connected and budgets
            assert bool(accepted) == saved['joint_pass'] and connected == saved['connection_pass']
            assert chirality == saved['all_checked_chirality_pass']
            assert (geometry['severe_pairs'] == 0 and chirality and budgets) == saved['zero_severe_chirality_budget']
            metric_error = max(metric_error, max(abs(a-b) for a, b in checks))
            if label == 'final':
                q = [v.numpy() for v in values['final']]
                rotations = np.concatenate([v[:, 3:6] for v in q]); torsions = np.concatenate([v[:, 6:].flatten() for v in q])
                regular = squared.mean()+.1*(rotations**2).sum(-1).mean()+(.01*(1-np.cos(torsions)).mean() if len(torsions) else 0.)
                repulsion = np.maximum(depths-1.5, 0).dot(np.maximum(depths-1.5, 0))/len(x)/.25
                tail = np.maximum(np.sort(depths)[-16:]-1.9, 0)**2/.01
                budget = max(cr**2-1, 0)**2+max(hr**2-4, 0)**2
                for name in ['original', 'calibrated']:
                    connection = sum(np.mean(np.maximum(np.abs(edges[k])/(.5*t)-
                        (1 if name == 'original' else onsets[i]/(.5*t)), 0)**2)
                        for i, (k, t) in enumerate(TOLERANCES.items()))
                    expected = regular+100*(connection+repulsion+budget+tail.mean())
                    found = row['final_cross_objectives'][name]
                    assert abs(expected-found) <= 1e-7+1e-10*abs(expected)
                    objective_error = max(objective_error, abs(expected-found))
        assert metric_error < 1e-8
        outcomes.append(dict(index=index, verified=True, pose_max_abs=error, metric_max_abs=metric_error,
                             objective_max_abs=objective_error, reference_length_max_abs=reference_length_error))
    paired = []
    for i in range(0, 32, 2):
        left, right = report['rows'][i:i+2]
        if not (left['success'] and right['success']):
            paired.append(dict(index=i//2, paired=False)); continue
        for key in (['shared_objective_sha256', 'raw_sha256'] if reference_trial and not warm_trial else ['chart_sha256', 'shared_objective_sha256', 'raw_sha256']):
            assert left[key] == right[key]
        x = dict(np.load(root / 'cases' / f'{i:02d}' / 'coordinates.npz'))
        y = dict(np.load(root / 'cases' / f'{i+1:02d}' / 'coordinates.npz'))
        shared = ['raw', 'target', 'atom_names', 'residue_ids']
        if not reference_trial or warm_trial:
            shared.append('local')
        if warm_trial:
            shared.append('output_reference')
        if fitted_trial or reference_trial:
            assert left['objective_sha256'] == right['objective_sha256']
        else:
            shared.append('start')
        assert all(np.array_equal(x[k], y[k]) for k in shared)
        paired.append(dict(index=i//2, paired=True))
    write_json(root / 'audit.json', dict(complete=True, report_sha256=sha256(root / 'report.json'),
        script_sha256=sha256(Path(__file__)), verified=sum(r['verified'] for r in outcomes),
        paired=sum(r['paired'] for r in paired), cases=outcomes, pairs=paired))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True)
    audit_connection_window_trial(p.parse_args().root)
