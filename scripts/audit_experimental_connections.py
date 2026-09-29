#!/usr/bin/env python3
"""Read-only GT and archived prediction connection diagnostics; no solver call."""
import argparse
import csv
import json
from pathlib import Path

import gemmi
import numpy as np
import torch

from fastglycan.anchored_geometry import JointObjective
from fastglycan.connection_audit import measure_connections,summarize_residuals,TOLERANCES
from fastglycan.paired_teacher_protocol import sha256,write_json


def raw_cif_check(cif,meta,inventory,target):
    table=gemmi.cif.read(str(cif)).sole_block().get_mmcif_category('_atom_site.')
    chain=meta['chains'][0];lookup={}
    def clean(x):return '' if x in [False,None,'.','?'] else str(x)
    for i,label in enumerate(table['label_asym_id']):
        if label!=chain['source_label_asym_id'] or str(table['pdbx_PDB_model_num'][i])!='1':continue
        seq=clean(table['label_seq_id'][i])
        if not seq.isdigit():continue
        key=(int(seq),table['label_atom_id'][i],clean(table['label_alt_id'][i]))
        assert key not in lookup
        lookup[key]=(np.array([float(table[k][i]) for k in ['Cartn_x','Cartn_y','Cartn_z']]),
                     table['type_symbol'][i],table['label_comp_id'][i])
    points=[]
    for residue,name,element in zip(inventory['residue_id'],inventory['atom_name'],inventory['element'],strict=True):
        r=chain['residues'][int(residue)-1];alt=clean(r['selected_altloc'])
        key=(int(r['label_seq_id']),str(name),alt)
        if key not in lookup:key=(int(r['label_seq_id']),str(name),'')
        point,atom_element,comp=lookup[key]
        assert atom_element==element and comp==r['comp_id']
        points.append(point)
    points=np.array(points);x=points-points.mean(0);y=target-target.mean(0)
    u,_,vt=np.linalg.svd(x.T@y);rotation=u@np.diag([1.,1.,np.linalg.det(u@vt)])@vt
    aligned=x@rotation+target.mean(0)
    error=float(np.linalg.norm(aligned-target,axis=-1).max())
    assert error<1e-3
    return dict(source_mmcif_sha256=sha256(cif),atoms=len(points),proper_rotation_det=float(np.linalg.det(rotation)),
                rigid_aligned_max_atom_difference=error,recorded_operator_path=chain['operator_path'])


def main():
    p=argparse.ArgumentParser()
    for key in ['root','source','joint','base']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();root=a.root;assert not (root/'lock.json').exists();torch.set_num_threads(1)
    selection=json.loads((a.source/'selection.json').read_text())
    joint=json.loads((a.joint/'report.json').read_text());jointaudit=json.loads((a.joint/'audit.json').read_text())
    assert jointaudit['verified']==28 and jointaudit['paired']==14
    assert jointaudit['report_sha256']==sha256(a.joint/'report.json')
    previous=json.loads((a.joint/'lock.json').read_text())
    for path,value in previous['hashes'].items():assert sha256(Path(path))==value
    references=json.loads((root/'external_reference.json').read_text());af=references['values']
    assert af['between_res_bond_length_c_n']==[1.329,1.341]
    assert af['between_res_cos_angles_ca_c_n'][0]==-.4473 and af['between_res_cos_angles_c_n_ca'][0]==-.5203
    inputs={str(a.source/'selection.json'):sha256(a.source/'selection.json'),
            str(a.joint/'report.json'):sha256(a.joint/'report.json'),
            str(a.joint/'audit.json'):sha256(a.joint/'audit.json'),
            str(root/'external_reference.json'):sha256(root/'external_reference.json')}
    for folder in [a.source/'data',a.source/'chemistry',a.joint/'cases',root/'code']:
        for file in folder.rglob('*'):
            if file.is_file() and file.suffix in ['.json','.npz','.py','.md']:inputs[str(file)]=sha256(file)
    for item in selection:
        file=a.source/'data'/item['group_id']/'gt.json';meta=json.loads(file.read_text());pdb=item['pdb_id']
        cif=a.base/'Dataset/raw/pdb_mmcif'/pdb[1:3]/(pdb+'.cif.gz')
        assert sha256(cif)==meta['provenance']['source_mmcif_sha256'];inputs[str(cif)]=sha256(cif)
    write_json(root/'lock.json',dict(hashes=inputs,source=str(a.source),joint=str(a.joint),
        protocol='mini_connection_gt_audit_v1',optimization=False,model_forward=False,threshold_changes=False))
    rows=[];edges=[];mapping=[];branches=[];skipped=[];vectors={}
    for slot,item in enumerate(selection):
        g=item['group_id'];packet=a.source/'chemistry'/g;folder=a.source/'data'/g
        chemistry=json.loads((packet/'report.json').read_text())
        if not chemistry['passed']:
            skipped.append(dict(pdb_id=item['pdb_id'],reason=chemistry['error']));continue
        inv=dict(np.load(folder/'inventory.npz'));meta=json.loads((folder/'gt.json').read_text())
        gt=dict(np.load(packet/'mapping.npz'));assert gt['mask'].all()
        target=gt['coordinates'].astype(np.float64);names=inv['atom_name'];residues=inv['residue_id'];seq=item['sequence']
        assert np.array_equal(names,gt['atom_names']) and np.array_equal(residues,gt['residue_ids'])
        anchors=np.array([[int(np.flatnonzero((residues==i)&(names==n))[0]) for n in ['N','CA','C','O']]
                          for i in range(1,len(seq)+1)])
        pdb=item['pdb_id'];cif=a.base/'Dataset/raw/pdb_mmcif'/pdb[1:3]/(pdb+'.cif.gz')
        mapping.append(dict(pdb_id=pdb,**raw_cif_check(cif,meta,inv,target)))
        ground=measure_connections(target,anchors,seq)
        structures=[dict(stage='gt_self',seed=None,coordinates=target,anchor=target)]
        for noise,seed in enumerate([12345,54321]):
            raw=np.load(folder/f'native_{seed}.npy').astype(np.float64)
            native=measure_connections(raw,anchors,seq)
            disagree=native['nearest_omega_sign']!=ground['nearest_omega_sign']
            branches.append(dict(pdb_id=pdb,seed=seed,edges=len(seq)-1,disagreements=int(disagree.sum()),
                gt_cis_like=int((ground['nearest_omega_sign']>0).sum()),
                raw_cis_like=int((native['nearest_omega_sign']>0).sum()),sites=[dict(
                    left_label=int(i)+1,right_label=int(i)+2,
                    gt_degrees=float(ground['omega_degrees'][i]),raw_degrees=float(native['omega_degrees'][i]),
                    next_residue=seq[i+1]) for i in np.flatnonzero(disagree)]))
            structures.append(dict(stage='model_raw',seed=seed,coordinates=raw,anchor=raw))
            for arm_i,arm in enumerate(['zero','fitted']):
                case=a.joint/'cases'/f'{slot*4+noise*2+arm_i:02d}'
                report=json.loads((case/'report.json').read_text());assert report['success']
                assert sha256(case/'coordinates.npz')==report['coordinates_sha256']
                data=dict(np.load(case/'coordinates.npz'));assert np.array_equal(data['target'],target)
                structures.append(dict(stage=arm+'_final',seed=seed,coordinates=data['final'],anchor=raw))
        for structure in structures:
            x=structure['coordinates'];anchor=structure['anchor'];stage=structure['stage']
            base=dict(pdb_id=pdb,group_id=g,stage=stage,seed=structure['seed'],edges=len(seq)-1,
                      resolution=meta['experimental']['resolution_high_angstrom'])
            try:
                objective=JointObjective(torch.tensor(anchor),anchors,seq,torch.empty((0,2),dtype=torch.long),torch.ones(len(x)))
                m=measure_connections(x,anchors,seq,objective.omega_target[:,0].numpy())
                measured=objective.residuals(torch.tensor(x))
                error=max(float(np.max(np.abs(value.numpy()-m['residuals'][key]))) for key,value in measured.items())
                assert error<1e-8
                phase_error=0.
                for ids,which in [(np.stack([anchors[:-1,1],anchors[:-1,2],anchors[1:,0],anchors[1:,1]],axis=1),'omega'),
                                  (np.stack([anchors[1:,0],anchors[:-1,1],anchors[:-1,2],anchors[:-1,3]],axis=1),'carbonyl')]:
                    angles=np.array([gemmi.calculate_dihedral(*[gemmi.Position(*p) for p in x[ix]]) for ix in ids])
                    expected=np.radians(m[which+'_degrees'])
                    phase_error=max(phase_error,float(np.max(np.abs(np.exp(1j*angles)-np.exp(1j*expected)))))
                assert phase_error<1e-8
                stats=summarize_residuals(m['residuals'])
                with torch.no_grad():
                    _,terms=objective(torch.tensor(x),[torch.zeros((len(seq),6),dtype=torch.float64)],1.)
                energy=sum(v['mean_penalty'] for v in stats.values())
                assert abs(energy-float(terms['connection']))<1e-6
                union_active=np.logical_or.reduce([np.abs(v)>.5*TOLERANCES[k] for k,v in m['residuals'].items()])
                union_fail=np.logical_or.reduce([np.abs(v)>TOLERANCES[k]+1e-6 for k,v in m['residuals'].items()])
                sigmas=dict(cn=np.array([af['between_res_bond_length_stddev_c_n'][aa=='P'] for aa in seq[1:]]),
                            angle_c=af['between_res_cos_angles_ca_c_n'][1],angle_n=af['between_res_cos_angles_c_n_ca'][1])
                overlay={k:int((np.sqrt(m['residuals'][k]**2+1e-6)>12*sigmas[k]).sum()) for k in sigmas}
                result=dict(**base,verified=True,stats=stats,connection_energy=energy,
                    active_edges=int(union_active.sum()),rejected_edges=int(union_fail.sum()),
                    residual_max_abs_vs_production=error,phase_max_abs_vs_gemmi=phase_error,
                    reference_12sigma_overlay_three_terms=overlay)
                structure_edges=[]
                for i in range(len(seq)-1):
                    r1,r2=meta['chains'][0]['residues'][i:i+2]
                    structure_edges.append(dict(**base,left_label=i+1,right_label=i+2,left_auth=r1['auth_seq_id'],right_auth=r2['auth_seq_id'],
                        next_residue=seq[i+1],**{k+'_residual':float(v[i]) for k,v in m['residuals'].items()},
                        **{k:float(m[k][i]) for k in ['cn','angle_c_degrees','angle_n_degrees','omega_degrees','carbonyl_degrees']},
                        fixed_cis_like=bool(m['omega_sign'][i]>0),gt_cis_like=bool(ground['nearest_omega_sign'][i]>0)))
                rows.append(result);edges.extend(structure_edges)
                for k,v in m['residuals'].items():vectors.setdefault((stage,k),[]).append(v)
            except Exception as exc:
                rows.append(dict(**base,verified=False,error=repr(exc)))
    pooled={}
    for stage in ['gt_self','model_raw','zero_final','fitted_final']:
        matching=[r for r in rows if r['stage']==stage];good=[r for r in matching if r['verified']]
        pooled[stage]=dict(planned_structures=len(matching),verified_structures=len(good),
            active_edges=sum(r['active_edges'] for r in good),rejected_edges=sum(r['rejected_edges'] for r in good),
            measured_edges=sum(r['edges'] for r in good),
            stats=summarize_residuals({k:np.concatenate(vectors[stage,k]) for k in TOLERANCES}) if good else {},
            protein_or_instance_mean_energy=float(np.mean([r['connection_energy'] for r in good])) if good else None)
    write_json(root/'report.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),mapping_checks=mapping,
        source_failures=skipped,rows=rows,pooled=pooled,raw_branch_comparisons=branches,
        scope='read-only development audit; unchanged thresholds; no causal quality attribution'))
    with (root/'edges.csv').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(edges[0]),lineterminator='\n');writer.writeheader();writer.writerows(edges)
    print(json.dumps({k:{n:v[n] for n in ['planned_structures','verified_structures','measured_edges','active_edges','rejected_edges']} for k,v in pooled.items()}))


if __name__=='__main__':main()
