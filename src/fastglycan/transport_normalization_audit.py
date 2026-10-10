"""Frozen native evaluation of a single input-only normalized transport rule."""
import json
from pathlib import Path
import time

import numpy as np
import torch

from fastglycan.models.compensated_recycle import initialize_cached_recycle, native_recycle_step
from fastglycan.models.normalized_trajectory import normalized_trajectory_transport, channel_error_decomposition
from fastglycan.models.recycle_trajectory import transfer_reference_progress
from fastglycan.models.prefix_recycle import capture_rng_state, restore_rng_state
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.response_moments import ResponseMoments


def read_transport_normalization_lock(root):
    root=Path(root);lock=json.loads((root/'normalization_lock.json').read_text())
    assert lock['updates']==0 and lock['shards']==6
    assert lock['arms']==['exact','cold_c2','wt_progress','normalized']
    assert sha256(root/'protocol.md')==lock['protocol_sha256']
    for path,digest in lock['code'].items():assert sha256(root/'code'/path)==digest,path
    source=Path(lock['trajectory_root'])
    assert sha256(source/'trajectory_lock.json')==lock['trajectory_lock_sha256']
    assert json.loads((source/'controller.json').read_text())['complete']
    assert json.loads((source/'summary.json').read_text())['complete']
    return lock


def _checked_load(root, record):
    path=root/record['path'];assert sha256(path)==record['sha256'],str(path)
    return torch.load(path,map_location='cpu',weights_only=False)


def run_transport_normalization_audit(root, shard, runtime_factory):
    root=Path(root);lock=read_transport_normalization_lock(root);start=time.monotonic()
    assert 0<=shard<6
    source=Path(lock['trajectory_root']);old=json.loads((source/'trajectory_lock.json').read_text())
    evidence=[json.loads((source/f'shard_{i}.json').read_text()) for i in range(2)]
    assert all(r['complete'] for r in evidence)
    refs={r['parent']:r for d in evidence for r in d['references']}
    labels={r['label']:r for d in evidence for r in d['labels']}
    old_xyz={(r['arm'],r['label']):r for d in evidence for r in d['rows']}
    runtime=runtime_factory(Path(old['source']),str(root/f'work_{shard}'))
    base=runtime.base;model=runtime.model
    norms=(model.layernorm_s,model.layernorm_z_cycle)
    projections=(model.linear_no_bias_s,model.linear_no_bias_z_cycle)
    epsilons=tuple(float(n.eps) for n in norms)
    report=dict(complete=False,shard=shard,epsilons=epsilons,rows=[],sites=[],latent=[],
                candidate_errors=[],reference_scales=[],noedit=[],raw_replay=[],isolation=[])
    coordinates=root/'coordinates';coordinates.mkdir(exist_ok=True)
    with torch.no_grad():
        for parent in base.plan['parents']:
            pi=parent['parent_index']
            if pi%6!=shard:continue
            saved=_checked_load(source,refs[pi])
            w1=tuple(x.cuda() for x in saved['reference1']);w3=tuple(x.cuda() for x in saved['reference3'])
            guards=tuple(x.clone() for x in (*w1,*w3))
            rng=saved['rng3'];wt=base.item(pi)
            init=initialize_cached_recycle(model,wt['features'],base.references[pi][0])
            predicted=normalized_trajectory_transport(w1,w1,w3,epsilons)
            assert all(torch.equal(a,b) for a,b in zip(predicted,w3))
            final=native_recycle_step(model,wt['features'],init,predicted,rng=rng)
            assert all(torch.equal(a,b) for a,b in zip(final,base.references[pi][1:]))
            for ni in (0,1):assert torch.equal(base.decode(wt,(init.inputs,*final),ni),wt['teacher'][ni])
            report['noedit'].append(pi)
            bridge_w3=tuple(p(n(x)) for p,n,x in zip(projections,norms,w3))
            scales={}
            for field,first,third,eps in zip(('s','z'),w1,w3,epsilons):
                s1=((first-first.mean(-1,keepdim=True)).square().mean(-1)+eps).sqrt()
                s3=((third-third.mean(-1,keepdim=True)).square().mean(-1)+eps).sqrt()
                ratio=s3/s1
                scales[field]=dict(mean=float(ratio.mean()),minimum=float(ratio.min()),maximum=float(ratio.max()),
                                   quantiles=torch.quantile(ratio.flatten(),torch.tensor([.01,.5,.99],device='cuda')).tolist())
            report['reference_scales'].append(dict(parent=pi,fields=scales))
            first_candidate=None
            for site in base.plan['sites']:
                if site['parent_index']!=pi:continue
                moments={space:{arm:{f:ResponseMoments() for f in ('s','z')}
                                for arm in ('wt_progress','normalized')} for space in ('state','bridge')}
                for aa in site['candidates']:
                    item=base.item(pi,site['position_zero_based'],aa);label=item['label']
                    input_data=_checked_load(source,labels[label]['input'])
                    assert input_data['label']==label and input_data['role']==site['role_n15']
                    m1=tuple(x.cuda() for x in input_data['candidate1'])
                    inputs=runtime.candidate_input(item)
                    init=initialize_cached_recycle(model,item['features'],inputs)
                    raw=transfer_reference_progress(m1,w1,w3)
                    predicted=normalized_trajectory_transport(m1,w1,w3,epsilons)
                    final=native_recycle_step(model,item['features'],init,predicted,rng=rng)
                    xyz=np.stack([base.decode(item,(inputs,*final),ni).cpu().numpy() for ni in (0,1)])
                    assert np.isfinite(xyz).all()
                    path=coordinates/f'normalized_{label}.npz';assert not path.exists()
                    np.savez_compressed(path,coordinates=xyz)
                    report['rows'].append(dict(arm='normalized',label=label,path=str(path.relative_to(root)),sha256=sha256(path)))
                    if first_candidate is None:
                        baseline=native_recycle_step(model,item['features'],init,raw,rng=rng)
                        r=old_xyz['wt_progress',label];assert sha256(source/r['path'])==r['sha256']
                        expected=np.load(source/r['path'])['coordinates']
                        for ni in (0,1):assert np.array_equal(base.decode(item,(inputs,*baseline),ni).cpu().numpy(),expected[ni])
                        report['raw_replay'].append(label)
                        first_candidate=(item,init,m1,tuple(t.clone() for t in predicted),tuple(t.clone() for t in final),xyz)
                    # Target labels are opened only after prediction and coordinate output.
                    target_data=_checked_load(source,labels[label]['target'])
                    assert target_data['label']==label and target_data['role']==site['role_n15']
                    m3=tuple(x.cuda() for x in target_data['target3'])
                    target_path=base.store.path(pi,label,'conditioning.pt')
                    assert sha256(target_path)==target_data['verified_target4_sha256']
                    target4=torch.load(target_path,map_location='cpu',weights_only=False)['conditioning'][1:]
                    diagnostics={}
                    for index,field in enumerate(('s','z')):
                        bridge_target=projections[index](norms[index](m3[index]))
                        for arm,state in [('wt_progress',raw),('normalized',predicted)]:
                            moments['state'][arm][field].add(state[index]-w3[index],m3[index]-w3[index])
                            bridge=projections[index](norms[index](state[index]))
                            moments['bridge'][arm][field].add(bridge-bridge_w3[index],bridge_target-bridge_w3[index])
                        before=channel_error_decomposition(predicted[index],m3[index])
                        after=float((final[index].double()-target4[index].cuda().double()).square().mean())
                        diagnostics[field]=dict(elements=predicted[index].numel(),raw=channel_error_decomposition(raw[index],m3[index]),
                            normalized=before,after_mse=after,
                            finite_error_norm_gain=(after/before['mse'])**.5 if before['mse']>1e-24 else None)
                    report['candidate_errors'].append(dict(label=label,parent=pi,site=site['site_key'],role=site['role_n15'],states=diagnostics))
                    del target_data,target4,m3,final,predicted,raw,m1,input_data
                report['sites'].append(site['site_key'])
                report['latent'].append(dict(site=site['site_key'],parent=pi,pdb=site['pdb_id'],role=site['role_n15'],
                    spaces={space:{a:{f:m.result() for f,m in fields.items()} for a,fields in arms.items()}
                            for space,arms in moments.items()}))
                report['seconds']=time.monotonic()-start;write_json(root/f'shard_{shard}.json',report)
                print('NORMALIZATION_SITE',shard,site['site_key'],base.counts,flush=True)
            item,init,m1,expected3,expected4,expected_xyz=first_candidate
            again=normalized_trajectory_transport(m1,w1,w3,epsilons)
            final=native_recycle_step(model,item['features'],init,again,rng=rng)
            assert all(torch.equal(a,b) for a,b in zip(again,expected3))
            assert all(torch.equal(a,b) for a,b in zip(final,expected4))
            for ni in (0,1):assert np.array_equal(base.decode(item,(init.inputs,*final),ni).cpu().numpy(),expected_xyz[ni])
            assert all(torch.equal(a,b) for a,b in zip(guards,(*w1,*w3)))
            assert sha256(source/refs[pi]['path'])==refs[pi]['sha256']
            report['isolation'].append(item['label'])
        assert len(report['rows'])==152 and len(report['sites'])==8
        assert len(report['noedit'])==len(report['raw_replay'])==len(report['isolation'])==4
        assert base.counts['recycle']==164 and base.counts['s1']==328
        assert base.counts['updates']==base.counts['input_embedder']==0
    runtime.finish();read_transport_normalization_lock(root)
    report.update(complete=True,counts=base.counts,runtime=base.runtime,seconds=time.monotonic()-start,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),lock_sha256=sha256(root/'normalization_lock.json'))
    write_json(root/f'shard_{shard}.json',report)
    print('NORMALIZATION_COMPLETE',shard,report['seconds'],flush=True)
