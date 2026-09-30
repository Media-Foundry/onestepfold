#!/usr/bin/env python3
"""Post-hoc saved-coordinate audit: independent metrics and fixed loss values."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.spatial.distance import cdist
from scipy.spatial.transform import Rotation
import torch
from fastglycan.adapter_supervision import adapter_loss_parts
from fastglycan.paired_teacher_protocol import sha256, write_json
from onestepfold.data.gt_materializer import ATOM37_INDEX


def audit_folding_tail_objective(training_root, output):
    assert not output.exists(), 'preserve a prior diagnostic'
    torch.set_num_threads(1);start=time.monotonic()
    lock=json.loads((training_root/'lock.json').read_text())
    case=json.loads((training_root/'probe1024_worst_case.json').read_text());g=case['group_id']
    assert g in lock['original_train_ids'] and case['pdb_id'].lower()=='1mv8'
    source=Path(lock['source']);cache=Path(lock['cache']);folder=cache/'examples'/g
    inputs={str(training_root/'lock.json'):sha256(training_root/'lock.json'),
        str(training_root/'probe1024_worst_case.json'):sha256(training_root/'probe1024_worst_case.json')}
    for name in ['adapter_supervision.py','experimental_training.py','smooth_lddt_supervision.py']:
        p=training_root/'code/src/fastglycan'/name
        assert sha256(p)==lock['hashes'][str(p)];inputs[str(p)]=sha256(p)
    for name in ['gt_supervision.pt','s2_seed600001.npy','s2_seed600011.npy']:
        p=folder/name;assert sha256(p)==lock['cache_files'][str(p)];inputs[str(p)]=sha256(p)
    cl=json.loads((cache/'lock.json').read_text())
    for p in [source/'chemistry'/g/'mapping.npz',source/'data/examples'/g/'gt.npz']:
        assert sha256(p)==cl['input_hashes'][str(p)];inputs[str(p)]=sha256(p)
    labels=torch.load(folder/'gt_supervision.pt',map_location='cpu',weights_only=False)
    mapping=dict(np.load(source/'chemistry'/g/'mapping.npz'));original=dict(np.load(source/'data/examples'/g/'gt.npz'))
    names=mapping['atom_names'];residues=mapping['residue_ids'];indices=np.array([ATOM37_INDEX[n] for n in names])
    mask=original['atom37_mask'][residues-1,indices]&original['residue_mask'][residues-1]
    assert np.array_equal(mask,mapping['mask']) and np.array_equal(mask,labels['coordinate_mask'].numpy())
    target=np.asarray(mapping['coordinates'],dtype=float)
    assert np.array_equal(target[mask],original['atom37_positions'][residues[mask]-1,indices[mask]])
    assert np.array_equal(target[mask],labels['coordinate'].numpy()[mask])
    results=[];maximum_lddt_error=maximum_rmsd_error=maximum_mse_error=0.
    with torch.no_grad():
        for arm in ['train128','expanded']:
            for update in [0,512,1024]:
                probe=training_root/arm/f'probe_{update:04d}'
                rp=probe/'report.json';report=json.loads(rp.read_text());inputs[str(rp)]=sha256(rp)
                for seed in lock['training_seeds']:
                    record=next(x for x in report['records'] if x['group_id']==g and x['seed']==seed)
                    p=probe/f'{g}_{seed}.npy';assert sha256(p)==record['sha256'];inputs[str(p)]=sha256(p)
                    x=np.load(p);assert x.dtype==np.float32 and np.isfinite(x).all()
                    teacher=np.load(folder/f's2_seed{seed}.npy')
                    parts=adapter_loss_parts(torch.from_numpy(x),labels,torch.from_numpy(teacher),smooth_temperature=lock['smooth_temperature'])
                    parts={k:float(v) for k,v in parts.items()};weighted={k:lock['weights'][k]*v for k,v in parts.items()}
                    independent={}
                    for selection,key in [(mask,'all_atom_lddt'),((names=='CA')&mask,'ca_lddt')]:
                        pred=x[selection].astype(float);ref=target[selection];ids=residues[selection]
                        pc=pred-pred.mean(0);rc=ref-ref.mean(0)
                        rotation,_=Rotation.align_vectors(rc,pc)
                        aligned_mse=float(np.mean(np.sum((rotation.apply(pc)-rc)**2,axis=1)))
                        if key=='ca_lddt':
                            independent['ca_aligned_rmsd']=float(np.sqrt(aligned_mse))
                            maximum_rmsd_error=max(maximum_rmsd_error,abs(np.sqrt(aligned_mse)-record['ca_aligned_rmsd']))
                        else:
                            independent['aa_aligned_mse']=aligned_mse
                            maximum_mse_error=max(maximum_mse_error,abs(aligned_mse-parts['coordinate']))
                        total=0.;count=0
                        for first in range(0,len(pred),128):
                            native=cdist(ref[first:first+128],ref);measured=cdist(pred[first:first+128],pred)
                            keep=(native<15)&(ids[first:first+128,None]!=ids[None,:])
                            neighbors=keep.sum(1);valid=neighbors>0;error=np.abs(measured-native)
                            agreement=sum(((error<t)&keep).astype(float) for t in [.5,1.,2.,4.])*.25
                            total+=float((agreement.sum(1)[valid]/neighbors[valid]).sum());count+=int(valid.sum())
                        independent[key]=total/count
                        maximum_lddt_error=max(maximum_lddt_error,abs(independent[key]-record[key]))
                    results.append(dict(arm=arm,update=update,seed=seed,parts=parts,weighted=weighted,
                        total=sum(weighted.values()),independent=independent,
                        severe_pairs=record['geometry']['severe_pairs'],strict_stereo=record['geometry']['strict_checked_chirality']))
    assert maximum_lddt_error<1e-10 and maximum_rmsd_error<1e-8 and maximum_mse_error<1e-6
    changes=[]
    for arm in ['train128','expanded']:
        for seed in lock['training_seeds']:
            initial=next(x for x in results if x['arm']==arm and x['seed']==seed and x['update']==0)
            for update in [512,1024]:
                final=next(x for x in results if x['arm']==arm and x['seed']==seed and x['update']==update)
                changes.append(dict(arm=arm,seed=seed,update=update,total_delta=final['total']-initial['total'],
                    weighted_delta={k:final['weighted'][k]-initial['weighted'][k] for k in initial['weighted']},
                    delta_aa=final['independent']['all_atom_lddt']-initial['independent']['all_atom_lddt'],
                    delta_ca=final['independent']['ca_lddt']-initial['independent']['ca_lddt']))
    write_json(output,dict(complete=True,group_id=g,pdb_id=case['pdb_id'],weights=lock['weights'],
        smooth_temperature=lock['smooth_temperature'],results=results,changes=changes,
        max_lddt_abs_error=maximum_lddt_error,max_ca_rmsd_abs_error=maximum_rmsd_error,max_coordinate_mse_abs_error=maximum_mse_error,
        inputs=inputs,script_sha256=sha256(Path(__file__)),seconds=time.monotonic()-start,
        scope='post-hoc single TRAIN protein; saved-coordinate CPU values, no model inference/gradient/optimizer or weight change; not causal attribution',
        teacher_role='native S2 synthetic auxiliary, experimental coordinates used for GT terms',
        numerical_scope='CPU recomputation of frozen objective values; not a bitwise GPU-loss replay or validation-set result'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--training-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();audit_folding_tail_objective(a.training_root.resolve(),a.output.resolve())
