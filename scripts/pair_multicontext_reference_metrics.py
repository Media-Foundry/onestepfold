"""CPU reference matrix diagnostics; no training, ESM, C4, or decoder calls."""
import argparse
from pathlib import Path
import torch
import numpy as np
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.deep_response_student import response_diagnostics
from fastglycan.multicontext_response import context_role
from fastglycan.paired_teacher_protocol import write_json,sha256


def pair_reference_metrics(root,index):
    torch.set_num_threads(1)
    lock=rt.load_json(root/'lock.json');store=FactorTeacherStore(Path(lock['teachers']));rows=[]
    for pi in lock['assignments'][index]:
        wt=store.load(pi)['conditioning'][2]
        for pos in store.rows[pi]['positions']:
            target=[];oracle=[]
            for aa in lock['aa']:
                if aa==store.rows[pi]['sequence'][pos]:continue
                z=store.load(pi,pos,aa)['conditioning'][2]
                delta=z.numpy().astype(np.float64)-wt.numpy().astype(np.float64)
                u,s,v=np.linalg.svd(delta.transpose(2,0,1),full_matrices=False)
                reconstructed=torch.from_numpy((wt.numpy().astype(np.float64)+((u[:,:,:32]*s[:,None,:32])@v[:,:32]).transpose(1,2,0)).astype(np.float32))
                target.append(z-wt);oracle.append(reconstructed-wt)
            target=torch.stack(target);oracle=torch.stack(oracle)
            for arm,pred in [('exact',target),('baseline',target),('wt_z',torch.zeros_like(target)),('oracle_r32',oracle)]:
                rows.append(dict(parent_index=pi,position=pos,role=context_role(pi,pos),arm=arm,**response_diagnostics(pred,target)))
    write_json(root/f'reference_metrics_{index}.json',dict(complete=True,records=rows,device='cpu',source_sha256=sha256(Path(__file__)),note='NumPy CPU FP64 SVD reference matrix diagnostics (this Torch build has no CPU LAPACK); functional oracle independently decoded with GPU FP64 SVD.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--index',type=int,required=True);a=p.parse_args();pair_reference_metrics(a.root,a.index)
