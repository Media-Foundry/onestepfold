"""Independent NumPy/FP64 reconstruction of saved parameter-space diagnostics."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json


def verify_stage_update_audit(root):
    begin=time.monotonic();checks=dict(nodes=0,derivatives=0,site_objectives=0)
    lock=json.loads((root/'audit_lock.json').read_text())
    def close(a,b):
        assert np.allclose(a,b,rtol=2e-9,atol=1e-10),(a,b)
    def comparison(record,g,d,groups):
        close(record['dot'],np.dot(g,d));close(record['gradient_norm'],np.linalg.norm(g))
        close(record['displacement_norm'],np.linalg.norm(d))
        denominator=np.linalg.norm(g)*np.linalg.norm(d)
        if denominator:close(record['cosine'],np.dot(g,d)/denominator)
        for name,slices in groups.items():
            close(record['groups'][name],sum(np.dot(g[a:b],d[a:b]) for a,b in slices))
        checks['derivatives']+=1
    for arm in ('final','hint'):
        for seed in (272001,272003):
            folder=root/'runs'/arm/str(seed)
            report=json.loads((folder/'report.json').read_text());assert report['complete']
            assert report['counts']==dict(forwards=14013,backwards=1701,virtual_adam_steps=165)
            assert all(v==0 for v in report['native_counts'].values())
            for node_meta in report['nodes']:
                path=folder/node_meta['path'];assert sha256(path)==node_meta['sha256']
                node=json.loads(path.read_text());assert node['complete'] and node['state_restored']
                vp=folder/node['vectors']['path'];assert sha256(vp)==node['vectors']['sha256']
                vectors=torch.load(vp,map_location='cpu',weights_only=False)
                array=lambda key:vectors[key].numpy().astype(np.float64,copy=False)
                gradients=array('site_gradients');g=array('full_gradient')
                close(g,gradients.mean(0));close(node['gradient_gram'],gradients@gradients.T)
                norms=np.linalg.norm(gradients,axis=1)
                close(node['gradient_cosines'],(gradients@gradients.T)/np.maximum(norms[:,None]*norms[None,:],1e-300))
                groups=vectors['groups']
                for record,gi in zip(node['site_gradients'],gradients):comparison(record,g,gi,groups)
                bg,cg,cd,ud=(array(x) for x in ('batch_gradients','clipped_gradients','clipped_deltas','unclipped_deltas'))
                for i,record in enumerate(node['scheduled_batches']):
                    for key,d in (('raw_gradient',bg[i]),('clipped_gradient',cg[i]),('clipped_update',cd[i]),('unclipped_update',ud[i])):
                        comparison(record[key],g,d,groups)
                    comparison(record['batch_own_clipped_update'],bg[i],cd[i],groups)
                comparison(node['mean_raw_gradient'],g,bg.mean(0),groups)
                comparison(node['mean_clipped_gradient'],g,cg.mean(0),groups)
                close(vectors['directions']['mean_clipped_adam'].numpy(),cd.mean(0))
                close(vectors['directions']['mean_unclipped_adam'].numpy(),ud.mean(0))
                origin=array('origin')
                evaluations=[node['baseline']]
                for name,record in node['probes'].items():
                    direction=vectors['directions'][name].numpy()
                    comparison(record['direction'],g,direction,groups)
                    for fraction in record['fractions']:
                        applied=(origin+fraction['fraction']*direction).astype(np.float32).astype(np.float64)-origin
                        comparison(fraction['actual_direction'],g,applied,groups)
                        evaluations.append(fraction['evaluation'])
                        close(fraction['loss_change'],fraction['evaluation']['objective']-node['baseline']['objective'])
                for ev in evaluations:
                    close(ev['objective'],np.mean([r['objective'] for r in ev['sites']]))
                    for row in ev['sites']:
                        assert row['site'] in lock['train_sites']
                        for stage in ('final','hint'):
                            close(row[stage]['raw'],row[stage]['common']+row[stage]['centered'])
                        expected=row['final']['raw'] if arm=='final' else (row['final']['raw']+row['hint']['raw'])/2
                        close(row['objective'],expected);checks['site_objectives']+=1
                    for stage in ('final','hint'):
                        for mode in ('raw','common','centered'):
                            close(ev[stage][mode],np.mean([r[stage][mode] for r in ev['sites']]))
                checks['nodes']+=1
                print('VERIFIED_UPDATE_NODE',arm,seed,node['step'],flush=True)
                del vectors,gradients,bg,cg,cd,ud
    assert checks['nodes']==12 and checks['site_objectives']==2916
    write_json(root/'verification.json',dict(complete=True,checks=checks,
        method='independent NumPy FP64 from saved parameter vectors and full per-site objective moments',
        native_calls=0,additional_optimizer_steps=0,seconds=time.monotonic()-begin))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    verify_stage_update_audit(p.parse_args().root)
