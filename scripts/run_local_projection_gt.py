#!/usr/bin/env python3
"""Frozen GT self-projection and cached native-prediction development comparison."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

import numpy as np
import torch

from fastglycan.articulated_output import ArticulatedOutput, AA
from fastglycan.articulated_reference import geometry_invariants
from fastglycan.anchored_geometry import PoseVariables, JointObjective
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.local_projection_fit import fit_local_projection
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.scaling_metrics import lddt_observed
from audit_anchored_geometry import replay


def dense_scores(x, target, residues, bone):
    """Independent dense score and additive atom-centred BB/SC contributions."""
    d = np.linalg.norm(target[:, None] - target[None, :], axis=-1)
    keep = (d < 15) & (residues[:, None] != residues[None, :])
    counts = keep.sum(-1)
    valid = counts > 0
    err = np.abs(np.linalg.norm(x[:, None] - x[None, :], axis=-1) - d)
    score = sum((err < t).astype(float) for t in [.5, 1., 2., 4.]) / 4
    per = np.zeros(len(x))
    per[valid] = (score * keep).sum(-1)[valid] / counts[valid]
    return dict(all_atom=float(per[valid].mean()),
        backbone_contribution=float(per[valid & bone].sum() / valid.sum()),
        sidechain_contribution=float(per[valid & ~bone].sum() / valid.sum()))


def run_case(root, index):
    lock = json.loads((root / 'execution_lock.json').read_text())
    for path, value in lock['hashes'].items():
        assert sha256(Path(path)) == value
    rows = json.loads((root / 'selection.json').read_text())
    row, arm = rows[index // 3], ['gt_self', 'native_12345', 'native_54321'][index % 3]
    g = row['group_id']; packet = root / 'chemistry' / g
    folder = root / 'fits' / f'{index:02d}'; folder.mkdir(parents=True, exist_ok=False)
    result = dict(index=index, group_id=g, pdb_id=row['pdb_id'], arm=arm, success=False)
    start = time.monotonic()
    try:
        chemistry = json.loads((packet / 'report.json').read_text())
        if not chemistry['passed']:
            result['source_failure'] = chemistry['error']
            result['not_run'] = True
            return result
        torch.set_num_threads(1)
        mapping = dict(np.load(packet / 'mapping.npz'))
        inv = dict(np.load(root / 'data' / g / 'inventory.npz'))
        names, residues = mapping['atom_names'], mapping['residue_ids']
        assert np.array_equal(names, inv['atom_name']) and np.array_equal(residues, inv['residue_id'])
        assert mapping['mask'].all()
        target = mapping['coordinates'].astype(np.float64)
        raw = target.copy() if arm == 'gt_self' else np.load(root / 'data' / g / (arm + '.npy')).astype(np.float64)
        variants = json.loads((packet / 'variants.json').read_text())
        adapter = ArticulatedOutput(mapping['reference'], names, residues, row['sequence'], variants).double()
        # GT input is an explicitly separate self-projection diagnostic, never a model prediction.
        fit = fit_local_projection(adapter, torch.tensor(raw), max_iter=60, max_eval=90)
        result['fit_seconds'] = time.monotonic() - start
        variables = PoseVariables(adapter, torch.tensor(raw))
        with torch.no_grad():
            for p, value in zip(variables.variables, fit.values, strict=True):
                p.copy_(value)
        result['independent_pose_max_abs'] = float(np.abs(replay(variables) - fit.coordinates.numpy()).max())
        assert result['independent_pose_max_abs'] < 1e-8
        atoms = torch.load(packet / 'native.pt', map_location='cpu', weights_only=False)['atoms']
        top = GeometryTopology(atoms, mapping['reference'])
        anchors = [[int(np.flatnonzero((residues == i) & (names == n))[0]) for n in ['N','CA','C','O']]
                   for i in range(1, len(row['sequence']) + 1)]
        objective = JointObjective(torch.tensor(raw), anchors, row['sequence'], top.pairs, top.radii)
        bone = np.isin(names, ['N','CA','C','O']); ca = names == 'CA'
        side = np.array([[int(np.flatnonzero((residues == i) & (names == n))[0])
            for n in ['CB','CA','CG1' if aa == 'I' else 'OG1','CG2']]
            for i, aa in enumerate(row['sequence'], 1) if aa in 'IT'], dtype=int).reshape(-1,4)
        def volumes(x):
            c,a,b,d = side.T
            return (np.cross(x[a]-x[c], x[b]-x[c]) * (x[d]-x[c])).sum(-1)
        refvol = volumes(mapping['reference'])
        arrays = dict(raw=raw, initial=fit.initial.numpy(), final=fit.coordinates.numpy(), target=target)
        result['metrics'] = {}
        for label in ['raw','initial','final']:
            x = arrays[label]
            score = lddt_observed(x, target, residues)['score']
            dense = dense_scores(x, target, residues, bone)
            assert abs(score - dense['all_atom']) < 1e-12
            _, geometry = top.terms(torch.tensor(x))
            residuals = {k:float(v.abs().max()) for k,v in objective.residuals(torch.tensor(x)).items()}
            squared = ((x-raw)**2).sum(-1)
            result['metrics'][label] = dict(all_atom_lddt=score,
                ca_lddt=lddt_observed(x[ca], target[ca], residues[ca])['score'],
                atom_centred=dense, geometry=geometry, connection_max=residuals,
                connection_pass=all(residuals[k] <= tol + 1e-6 for k,tol in
                    dict(cn=.03,angle_c=.04,angle_n=.04,omega=.1,carbonyl=.1).items()),
                all_checked_chirality_pass=geometry['chirality_fraction']==1 and bool((volumes(x)*refvol>0).all()),
                raw_mse=float(squared.mean()), backbone_raw_mse=float(squared[bone].mean()),
                sidechain_raw_mse=float(squared[~bone].mean()), ca_raw_rms=float(np.sqrt(squared[ca].mean())),
                max_atom_displacement=float(np.sqrt(squared.max())))
        invariants = []
        for i, aa in enumerate(row['sequence'],1):
            mask = residues == i
            bonds = variants[AA[aa]+':'+','.join(names[mask])]['bonds']
            a,b = geometry_invariants(mapping['reference'][mask], bonds)
            c,d = geometry_invariants(arrays['final'][mask], bonds)
            invariants.append(dict(residue=i, bond_error=float(np.abs(a-c).max()),
                                    angle_cosine_error=float(np.abs(b-d).max())))
        np.savez_compressed(folder / 'coordinates.npz', **arrays, atom_names=names, residue_ids=residues)
        torch.save(fit.values, folder / 'values.pt')
        result.update(success=True, local_invariants=invariants, iterations=fit.iterations,
            closure_calls=fit.closure_calls, final_gradient_norm=fit.final_gradient_norm,
            coordinates_sha256=sha256(folder/'coordinates.npz'), values_sha256=sha256(folder/'values.pt'))
    except Exception:
        result['error'] = traceback.format_exc()
    finally:
        result['seconds'] = time.monotonic()-start
        write_json(folder / 'report.json', result)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['lock','batch','case'],required=True);p.add_argument('--index',type=int)
    a=p.parse_args();root=a.root
    if a.mode=='lock':
        assert not (root/'execution_lock.json').exists()
        files=[root/'selection.json',root/'preparation_lock.json',root/'summary.json']
        files += [f for d in ['data','chemistry'] for f in (root/d).rglob('*') if f.is_file()]
        code=Path(__file__).parent
        files += [f for f in code.rglob('*') if f.is_file() and f.suffix in ['.py','.md']]
        write_json(root/'execution_lock.json',dict(hashes={str(f):sha256(f) for f in files},
            cases=24,workers=2,timeout=900,max_iter=60,max_eval=90,reference_code_commit='74d75c47',
            scope='7 eligible proteins plus1 source failure; retained8-source/24-arm denominator',
            no_training=True,no_new_model_inference=True))
    elif a.mode=='case':
        run_case(root,a.index)
    else:
        assert not (root/'report.json').exists()
        def worker(i):
            with (root/f'fit_{i:02d}.log').open('x') as log:
                try:
                    x=subprocess.run([sys.executable,__file__,'--root',str(root),'--mode','case','--index',str(i)],
                        stdout=log,stderr=log,timeout=900,env=dict(os.environ,OMP_NUM_THREADS='1',
                        OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',ROCR_VISIBLE_DEVICES=''))
                    return dict(index=i,returncode=x.returncode)
                except subprocess.TimeoutExpired:
                    return dict(index=i,returncode=124)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            execution=list(pool.map(worker,range(24)))
        rows=[]
        for i in range(24):
            f=root/'fits'/f'{i:02d}'/'report.json'
            rows.append(json.loads(f.read_text()) if f.exists() else dict(index=i,success=False,error='missing report'))
        write_json(root/'report.json',dict(complete=True,expected=24,successful=sum(r['success'] for r in rows),
            rows=rows,execution=execution,lock_sha256=sha256(root/'execution_lock.json'),
            scope='development results; source failures retained; no C4 or generalization claim'))
        write_json(root/'execution_exit.json',dict(process_failures=sum(r['returncode']!=0 for r in execution),
            successful_fits=sum(r['success'] for r in rows),expected=24))


if __name__=='__main__':main()
