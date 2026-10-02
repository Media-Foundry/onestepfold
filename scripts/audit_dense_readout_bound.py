"""Post-hoc capacity audit of the row-wise affine dense diagnostic, not AA PCA.

Unrestricted hidden rows H have width128. Whitening by per-candidate loss weights
and projecting off the fixed affine-bias direction gives an exact least-squares
lower bound for H W + bias. The actual learned encoder is more constrained.
"""
import argparse,json
from pathlib import Path
import numpy as np
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.paired_teacher_protocol import write_json


def dense_readout_bound(root):
    lock=json.loads((root/'lock.json').read_text());store=FactorTeacherStore(Path(lock['teachers']),training_only=True);wt=store.load(3);position=36;aa=[a for a in store.lock['aa'] if a!=wt['sequence'][position]]
    # Match training: subtraction first in FP32, then FP64 metric analysis.
    delta=np.stack([(store.load(3,position,a)['conditioning'][2]-wt['conditioning'][2]).numpy() for a in aa]).astype(np.float64)
    count,length,_,channels=delta.shape;den=np.maximum((delta**2).mean((1,2,3)),1e-6);weights=1/np.sqrt(den)
    matrix=(delta*weights[:,None,None,None]).reshape(count*length,length*channels);bias=np.repeat(weights,length);bias=bias/np.linalg.norm(bias)
    mean=bias[:,None]*(bias@matrix)[None,:];centered=matrix-mean;gram=centered@centered.T;ev,vec=np.linalg.eigh(gram);ev=ev[::-1];vec=vec[:,::-1];tolerance=1e-9*max(ev[0],1.)
    assert ev.min()>-tolerance;ev=np.maximum(ev,0);normalizer=count*length*length*channels;width=128
    bound=float(ev[width:].sum()/normalizer);raw_rank_bound=float(np.linalg.eigvalsh(matrix@matrix.T)[:-129].clip(0).sum()/normalizer)
    reconstructed=mean+vec[:,:width]@(vec[:,:width].T@centered);measured=float(((reconstructed-matrix)**2).sum()/normalizer);assert abs(measured-bound)<1e-10
    rows=[]
    for p in sorted((root/'runs').glob('A_dense_*/report.json')):
        r=json.loads(p.read_text())
        if r['complete']:rows.append(dict(job=p.parent.name,nmse=r['history'][-1]['mean_nmse'],gap_above_affine_bound=r['history'][-1]['mean_nmse']-bound))
    write_json(root/'dense_readout_bound.json',dict(complete=True,post_hoc=True,training=False,shape=list(matrix.shape),hidden_width=width,affine_optimal_nmse=bound,explicit_reconstruction_nmse=measured,unconstrained_rank129_lower_bound=raw_rank_bound,teacher_weighted_mean_square=float((matrix**2).sum()/normalizer),runs=rows,interpretation='This bounds this shared row-wise readout only; not every dense head or every WT-only final-state regressor.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();dense_readout_bound(a.root)
