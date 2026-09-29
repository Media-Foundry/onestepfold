#!/usr/bin/env python3
"""Calibrate backbone scalars, freeze them, then measure held-out agreement."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile

import numpy as np

from fastglycan.backbone_reference_calibration import BACKBONE_METRICS, fit_backbone_reference, measure_backbone_local_geometry
from fastglycan.ca_span_feasibility import ca_span_bounds
from fastglycan.connection_audit import measure_connections, TOLERANCES
from onestepfold.data.gt_materializer import ATOM37_INDEX


def audit_backbone_reference_calibration(root, reference_file, provenance_file, output):
    assert not output.exists()
    output.mkdir(parents=True)
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    write = lambda n,d: (output/n).write_text(json.dumps(d,indent=2)+'\n')
    code = Path(__file__).resolve().parents[1]
    inputs = [Path(__file__), reference_file, provenance_file,
        code/'src/fastglycan/backbone_reference_calibration.py',
        code/'src/fastglycan/ca_span_feasibility.py', code/'src/fastglycan/connection_audit.py',
        code/'src/onestepfold/data/gt_materializer.py', code/'docs/mini_backbone_reference_calibration_v1.md',
        root/'measurement/source_evidence.tar.gz', root/'measurement/source_evidence_manifest.json',
        root/'extension/selection.json', root/'audit.json']
    write('input_lock.json',dict(hashes={str(p.resolve()):digest(p) for p in inputs},
        protocol='mini_backbone_reference_calibration_v1', no_model_or_solver=True))
    ref = json.loads(reference_file.read_text())
    previous = json.loads(provenance_file.read_text())
    for p,h in ref['hashes'].items(): assert previous['source_hashes'][p] == h
    reference = {aa:{k:float(v) for k,v in measure_backbone_local_geometry(r['coordinates']).items()}
                 for aa,r in ref['records'].items()}
    manifest = json.loads((root/'measurement/source_evidence_manifest.json').read_text())
    assert digest(root/'measurement/source_evidence.tar.gz') == manifest['archive_sha256']
    with tarfile.open(root/'measurement/source_evidence.tar.gz') as archive:
        blobs = {m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    assert set(blobs) == set(manifest['files'])
    for name,value in blobs.items():
        assert hashlib.sha256(value).hexdigest() == manifest['files'][name]['sha256']
        assert len(value) == manifest['files'][name]['bytes']
    assert blobs['extension/selection.json'] == (root/'extension/selection.json').read_bytes()
    panel = json.loads(blobs['extension/selection.json'])
    assert len(panel) == 64 and len({r['group_id'] for r in panel}) == 64
    assert sum(r['role']=='calibration' for r in panel) == 32
    rows, spans, failures, structures = [], [], [], []
    fitted = None; angle_check = 0.
    for role in ['calibration','held_out']:
        if role == 'held_out':
            assert fitted is not None
            fitted = json.loads((output/'fitted_backbone_reference.json').read_text())['parameters']
            frozen_fit_hash = digest(output/'fitted_backbone_reference.json')
        for item in [r for r in panel if r['role']==role]:
            try:
                prefix = 'selected_gt/'+item['group_id']+'/'
                for n,key in [('gt.npz','gt_sha256'),('gt.json','metadata_sha256')]:
                    assert hashlib.sha256(blobs[prefix+n]).hexdigest() == item[key]
                meta = json.loads(blobs[prefix+'gt.json'])
                seq = item['sequence']; assert meta['chains'][0]['sequence'] == seq
                data = np.load(io.BytesIO(blobs[prefix+'gt.npz']))
                indices = [ATOM37_INDEX[n] for n in ['N','CA','C','O']]
                assert data['residue_mask'].all() and data['atom37_mask'][:,indices].all()
                x = data['atom37_positions'][:,indices].astype(np.float64)
                measured = measure_backbone_local_geometry(x)
                # Independent triangle-law angles (different from dot product).
                for name,a,b,c in [('n_ca_c_degrees',0,1,2),('ca_c_o_degrees',1,2,3)]:
                    ab=np.linalg.norm(x[:,a]-x[:,b],axis=-1)
                    bc=np.linalg.norm(x[:,b]-x[:,c],axis=-1)
                    ac=np.linalg.norm(x[:,a]-x[:,c],axis=-1)
                    check=np.degrees(np.arccos(np.clip((ab*ab+bc*bc-ac*ac)/(2*ab*bc),-1,1)))
                    angle_check=max(angle_check,float(np.max(np.abs(check-measured[name]))))
                for i,aa in enumerate(seq):
                    rows.append(dict(group_id=item['group_id'],pdb_id=item['pdb_id'],role=role,
                        amino_acid=aa,residue=i+1,terminal=i in [0,len(seq)-1],
                        **{k:float(v[i]) for k,v in measured.items()}))
                structures.append(dict(group_id=item['group_id'],pdb_id=item['pdb_id'],role=role,
                    residues=len(seq), internal_residues=len(seq)-2))
                if role == 'held_out':
                    ids=np.arange(len(seq)*4).reshape(-1,4)
                    signs=measure_connections(x.reshape(-1,3),ids,seq)['nearest_omega_sign']
                    observed=np.linalg.norm(x[1:,1]-x[:-1,1],axis=-1)
                    supported=np.array([fitted[a]['supported'] and fitted[b]['supported'] for a,b in zip(seq[:-1],seq[1:])])
                    b0=np.array([1.341 if aa=='P' else 1.329 for aa in seq[1:]])
                    for label in ['native_reference','calibration_median']:
                        take=reference if label=='native_reference' else {
                            aa:{k:v['median'] for k,v in f['metrics'].items()} for aa,f in fitted.items() if f['supported']}
                        chosen=np.ones(len(seq)-1,dtype=bool) if label=='native_reference' else supported
                        edge_ids=np.flatnonzero(chosen)
                        if not len(edge_ids): continue
                        a=np.array([take[seq[i]]['ca_c'] for i in edge_ids])
                        c=np.array([take[seq[i+1]]['n_ca'] for i in edge_ids])
                        box=ca_span_bounds(a,c,b0[chosen],{k:v+1e-6 for k,v in TOLERANCES.items()},signs[chosen])
                        gap=np.maximum.reduce([box['lower']-observed[chosen],observed[chosen]-box['upper'],np.zeros(len(edge_ids))])
                        for j,i in enumerate(edge_ids):
                            spans.append(dict(group_id=item['group_id'],pdb_id=item['pdb_id'],variant=label,
                                left_residue=int(i+1),terminal_edge=bool(i in [0,len(seq)-2]),
                                paired_supported=bool(supported[i]),gap=float(gap[j]),outside=bool(gap[j]>1e-6)))
            except Exception as exc:
                failures.append(dict(group_id=item['group_id'],role=role,error=repr(exc)))
                raise
        if role=='calibration':
            fitted=fit_backbone_reference(rows)
            write('fitted_backbone_reference.json',dict(parameters=fitted,reference_values=reference,
                calibration_proteins=sum(r['role']=='calibration' for r in structures),
                selection_sha256=digest(root/'extension/selection.json'),not_acceptance_thresholds=True,
                no_complete_conformer=True))
    assert digest(output/'fitted_backbone_reference.json') == frozen_fit_hash
    assert angle_check<1e-9
    held=[r for r in rows if r['role']=='held_out' and not r['terminal']]
    summaries={}; per_protein=[]
    for metric in BACKBONE_METRICS:
        by_aa={}
        for aa in reference:
            select=[r for r in held if r['amino_acid']==aa]
            values=np.array([r[metric] for r in select])
            baseline=reference[aa][metric]
            candidate=fitted[aa]['metrics'][metric]
            by_aa[aa]=dict(residues=len(values),proteins=len({r['group_id'] for r in select}),
                reference_value=baseline,reference_bias=float(np.mean(baseline-values)),
                reference_mae=float(np.mean(abs(baseline-values))),supported=fitted[aa]['supported'],
                fitted_value=None if candidate is None else candidate['median'],
                fitted_bias=None if candidate is None else float(np.mean(candidate['median']-values)),
                fitted_mae=None if candidate is None else float(np.mean(abs(candidate['median']-values))))
        groups=[]
        for gid in sorted({r['group_id'] for r in held}):
            select=[r for r in held if r['group_id']==gid and fitted[r['amino_acid']]['supported']]
            if not select:continue
            ref_err=np.array([reference[r['amino_acid']][metric]-r[metric] for r in select])
            fit_err=np.array([fitted[r['amino_acid']]['metrics'][metric]['median']-r[metric] for r in select])
            value=dict(group_id=gid,pdb_id=select[0]['pdb_id'],metric=metric,residues=len(select),
                reference_mae=float(np.mean(abs(ref_err))),fitted_mae=float(np.mean(abs(fit_err))),
                reference_bias=float(ref_err.mean()),fitted_bias=float(fit_err.mean()))
            value['delta_mae']=value['fitted_mae']-value['reference_mae'];groups.append(value);per_protein.append(value)
        delta=np.array([r['delta_mae'] for r in groups]);rng=np.random.default_rng(9302030)
        draws=delta[rng.integers(0,len(delta),size=(2000,len(delta)))].mean(axis=1)
        summaries[metric]=dict(by_amino_acid=by_aa,proteins=len(groups),
            supported_residues=sum(r['residues'] for r in groups),held_internal_residues=len(held),
            equal_protein_reference_mae=float(np.mean([r['reference_mae'] for r in groups])),
            equal_protein_fitted_mae=float(np.mean([r['fitted_mae'] for r in groups])),
            equal_protein_reference_bias=float(np.mean([r['reference_bias'] for r in groups])),
            equal_protein_fitted_bias=float(np.mean([r['fitted_bias'] for r in groups])),
            paired_mae_change=float(delta.mean()),bootstrap95=np.quantile(draws,[.025,.975]).tolist(),
            improved_proteins=int((delta<0).sum()),
            pooled_reference_mae=float(np.average([r['reference_mae'] for r in groups],weights=[r['residues'] for r in groups])),
            pooled_fitted_mae=float(np.average([r['fitted_mae'] for r in groups],weights=[r['residues'] for r in groups])))
    span_summary={}
    for variant in ['native_reference','calibration_median']:
        selected=[r for r in spans if r['variant']==variant and r['paired_supported']]
        span_summary[variant]=dict(edges=len(selected),outside=sum(r['outside'] for r in selected),
            proteins_with_violation=len({r['group_id'] for r in selected if r['outside']}),
            maximum_gap=max(r['gap'] for r in selected),terminal_edges=sum(r['terminal_edge'] for r in selected),
            terminal_outside=sum(r['terminal_edge'] and r['outside'] for r in selected))
    for name,data in [('residues.csv',rows),('per_protein.csv',per_protein),('spans.csv',spans)]:
        with (output/name).open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(data[0]),lineterminator='\n');writer.writeheader();writer.writerows(data)
    report=dict(complete=True,selected=64,measured=len(structures),failures=failures,structures=structures,
        supported_amino_acids=[aa for aa,f in fitted.items() if f['supported']],
        metrics=summaries,span_necessary_conditions=span_summary,
        held_edges_denominator=sum(r['residues']-1 for r in structures if r['role']=='held_out'),
        angle_triangle_max_abs=angle_check,fitted_sha256=frozen_fit_hash,
        input_lock_sha256=digest(output/'input_lock.json'),
        output_sha256={n:digest(output/n) for n in ['residues.csv','per_protein.csv','spans.csv','fitted_backbone_reference.json']},
        limits='No output construction, correction, chemical gate, side-chain calibration or independent folding validation')
    write('report.json',report)
    print(json.dumps(dict(supported=report['supported_amino_acids'],span=span_summary,
        metrics={k:{n:v[n] for n in ['equal_protein_reference_mae','equal_protein_fitted_mae','paired_mae_change','bootstrap95']} for k,v in summaries.items()}),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['root','reference','provenance','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();audit_backbone_reference_calibration(a.root,a.reference,a.provenance,a.output)
