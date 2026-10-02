"""Independent saved-endpoint checks and compact Gram evidence for the rank pilot."""
import argparse
from pathlib import Path
import json
import numpy as np
from fastglycan.paired_teacher_protocol import sha256,write_json


def audit_hard_response_rank(root):
    lock=json.loads((root/'lock.json').read_text());report=json.loads((root/'report.json').read_text())
    assert report['complete'] and report['lock_sha256']==sha256(root/'lock.json')
    grams={};sources=[];errors=[];svd_errors=[];n=0
    for worker in report['workers']:
        for row in worker['records']:
            path=root/f'worker_{worker["worker"]}'/row['endpoint_file'];assert sha256(path)==row['endpoint_sha256']
            e=np.load(path);wt=row['amino_acids'].index(row['wt']);keep=np.arange(20)!=wt
            assert all(e[k].dtype==np.float32 and len(e[k])==20 and np.isfinite(e[k]).all() for k in e.files)
            b=[e[k].astype(float)[keep]-e[k].astype(float)[wt] for k in ['s_site','z_row','z_col']]
            x=[v.reshape(19,-1) for v in b];prefix=f'p{row["parent_index"]}_s{row["position_1based"]}'
            for key,v in zip(['s','row','col'],x):grams[prefix+'_'+key]=v@v.T
            diag=b[2][:,row['position_0based']];grams[prefix+'_diagonal']=diag@diag.T
            norms=[float((v*v).sum()) for v in x]
            matrices=dict(s_site=x[0],z_row=x[1],z_col=x[2],raw_concat=np.concatenate(x,axis=1),
                per_feature=np.concatenate([v/np.sqrt(v.shape[1]) for v in x],axis=1),
                equal_block_energy=np.concatenate([v/np.sqrt(norm) if norm else v for v,norm in zip(x,norms)],axis=1),
                deduplicated_diagonal=np.concatenate([x[0],x[1],np.delete(b[2],row['position_0based'],axis=1).reshape(19,-1)],axis=1))
            for variant,matrix in matrices.items():
                for centered in [False,True]:
                    m=matrix-matrix.mean(0) if centered else matrix
                    expected=row['analysis']['spectra'][variant]['mutant_centered' if centered else 'wt_anchored']
                    # General SVD of the 19x19 Gram rather than eigvalsh; direct rectangular SVD for primary.
                    vals=np.linalg.svd(m@m.T,compute_uv=False);energy=vals.cumsum()/vals.sum()
                    errors.append(float(np.max(np.abs(energy-np.array(expected['cumulative_energy'])))))
                    assert int(np.searchsorted(energy,.95)+1)==expected['rank95']
                    assert int(np.searchsorted(energy,.99)+1)==expected['rank99']
                    if variant=='raw_concat':
                        sv=np.linalg.svd(m,compute_uv=False,full_matrices=False);ref=(sv*sv).cumsum()/(sv*sv).sum()
                        svd_errors.append(float(np.max(np.abs(ref-np.array(expected['cumulative_energy'])))))
            assert row['wt_replay_exact'];n+=1
            sources.append(dict(parent=row['parent_index'],site=row['position_1based'],file=str(path),sha256=sha256(path),dimensions=row['analysis']['dimensions']))
    assert n==50 and max(errors)<1e-10 and max(svd_errors)<1e-10
    np.savez_compressed(root/'gram_evidence.npz',**grams)
    write_json(root/'endpoint_manifest.json',dict(files=sources,storage='FP32 endpoints retained on DiamondHill and local runtime mirror; compact Gram evidence committed'))
    write_json(root/'independent_audit.json',dict(complete=True,sites=n,gram_comparisons=len(errors),direct_rectangular_svd_comparisons=len(svd_errors),
        max_gram_cumulative_error=max(errors),max_direct_svd_cumulative_error=max(svd_errors),gram_sha256=sha256(root/'gram_evidence.npz'),
        scope='all saved local spectra and rank95/99 independently checked; no additional GPU inference'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();audit_hard_response_rank(a.root)
