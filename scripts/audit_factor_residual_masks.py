"""Independent CPU reconstruction of fixed oracle mask rules and storage."""
import argparse,json
from pathlib import Path
import numpy as np
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.paired_teacher_protocol import sha256,write_json


def audit_residual_masks(root):
    lock=json.loads((root/'sparse/lock.json').read_text());store=FactorTeacherStore(Path(lock['teachers']));checks=[];contact_checks=0
    for wi,parents in enumerate(lock['assignments']):
        report=json.loads((root/f'sparse/worker_{wi}/report.json').read_text())
        for parent in report['parents']:
            pi=parent['parent_index'];wt=store.load(pi);inv=wt['inventory'];ca=wt['coordinates'][0,inv['atom_names']=='CA'];length=len(ca)
            for site in parent['sites']:
                pos=site['position'];near=(np.linalg.norm(ca-ca[pos],axis=-1)<=lock['contact_radius'])|(np.abs(np.arange(length)-pos)<=2);contact=near[:,None]&near[None,:]
                for mutant in site['mutants']:
                    p=root/f'sparse/worker_{wi}/{mutant["label"]}_masks.npz';assert sha256(p)==mutant['evidence']['mask_sha256'];masks=dict(np.load(p))
                    assert np.array_equal(masks['contact'],contact);contact_checks+=1
                    for name,mask in masks.items():
                        assert mutant['evidence']['pairs'][name]==int(mask.sum())
                        expected=(2*length*128*32*4+int(mask.sum())*(128*4+8))/(length*length*128*4)
                        assert abs(expected-mutant['evidence']['representation_fraction'][name])<1e-12
                if site is not parent['sites'][0]:continue
                mutant=site['mutants'][0];target=store.load(pi,pos,mutant['aa']);delta=target['conditioning'][2].numpy().astype(np.float64)-wt['conditioning'][2].numpy().astype(np.float64)
                left,sigma,right=np.linalg.svd(np.moveaxis(delta,-1,0),full_matrices=False)
                bulk=np.moveaxis((left[:,:,:32]*sigma[:,None,:32])@right[:,:32],0,-1);residual=delta-bulk;energy=(residual**2).sum(-1).ravel();order=np.argsort(-energy,kind='stable')
                masks=dict(np.load(root/f'sparse/worker_{wi}/{mutant["label"]}_masks.npz'));z0=(wt['conditioning'][2].numpy().astype(np.float64)+bulk).astype(np.float32)
                maximum=0.
                for name,mask in masks.items():
                    if name.startswith('top_'):
                        expected=np.zeros(length*length,bool);expected[order[:int(mask.sum())]]=True;assert np.array_equal(expected.reshape(length,length),mask)
                    z=np.where(mask[:,:,None],target['conditioning'][2].numpy(),z0)
                    nmse=float(np.mean((z.astype(np.float64)-target['conditioning'][2].numpy())**2)/max(np.mean(delta**2),1e-6))
                    maximum=max(maximum,abs(nmse-mutant['evidence']['latent_nmse'][name]))
                assert maximum<1e-6
                checks.append(dict(parent_index=pi,position=pos,aa=mutant['aa'],max_nmse_error=maximum))
    assert contact_checks==304 and len(checks)==8
    write_json(root/'residual_mask_audit.json',dict(complete=True,contact_and_storage_checks=contact_checks,independent_numpy_svd_cases=checks))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();audit_residual_masks(a.root)
