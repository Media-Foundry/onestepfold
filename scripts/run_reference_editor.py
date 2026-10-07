"""Bounded complete-conditioning Mini editor: structural learning, no target-state input."""
import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.reference_editor import ReferenceEditModel
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.models.soft_sequence_chart import native_sequence_features, device_tree
from fastglycan.models.differentiable_mini import prepare_atom_pairs, diffusion_from_conditioning
from fastglycan.functional_response_rank import pack_conditioning
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.adapter_supervision import build_adapter_supervision
from fastglycan.factor_student import factor_geometry_penalties


def state_hash(tensors):
    h = hashlib.sha256()
    for x in tensors:
        a = x.detach().cpu().contiguous().numpy()
        h.update(str((a.shape, a.dtype)).encode());h.update(a.tobytes())
    return h.hexdigest()


def coordinate_objective(x, y, ca, labels):
    xc, yc = x - x.mean(0), y - y.mean(0)
    with torch.no_grad():
        u, _, vt = torch.linalg.svd(xc.T @ yc)
        correction = torch.eye(3, device=x.device)
        correction[-1, -1] = torch.det(u @ vt)
        rotation = u @ correction @ vt
    coordinate = (xc @ rotation - yc).square().mean()
    ij = torch.triu_indices(len(ca), len(ca), offset=3, device=x.device)
    dx = torch.linalg.vector_norm(x[ca[ij[0]]] - x[ca[ij[1]]], dim=-1)
    dy = torch.linalg.vector_norm(y[ca[ij[0]]] - y[ca[ij[1]]], dim=-1)
    distance = (dx - dy).square().mean()
    clash, chirality = factor_geometry_penalties(x, labels)
    loss = coordinate + .25 * distance + .01 * clash + .01 * chirality
    return loss, {k:float(v.detach()) for k,v in dict(coordinate=coordinate, distance=distance, clash=clash, chirality=chirality).items()}


def run_reference_editor(root):
    runtime = guarded_hip_runtime();started = time.monotonic()
    lock = rt.load_json(root/'lock.json')
    for p,h in lock['code'].items(): assert sha256(root/'code'/p)==h,p
    teachers = Path(lock['teachers']);store = FactorTeacherStore(teachers)
    assert sha256(teachers/'teacher_lock.json')==lock['teacher_lock_sha256']
    assert sha256(teachers/'teacher_manifest.json')==lock['teacher_manifest_sha256']
    for p,h in store.lock['weights_sha256'].items(): assert sha256(Path(p))==h,p
    runner = rt.runner_setup(root/'work');runner.configs.dtype='fp32'
    decoder = runner.model.eval().requires_grad_(False)
    assert runner.configs.model_name == 'protenix_mini_esm_v0.5.0'
    counts = dict(c4=0, input_embedder=0, s1=0, updates=0)
    def forbid_trunk(*args):
        counts['c4'] += 1;raise AssertionError('candidate/reference C4 forbidden: frozen archive only')
    def forbid_inputs(*args):
        counts['input_embedder'] += 1;raise AssertionError('ESM/input encoder forbidden')
    def count_s1(*args): counts['s1'] += 1
    handles=[decoder.pairformer_stack.register_forward_pre_hook(forbid_trunk),
             decoder.input_embedder.register_forward_pre_hook(forbid_inputs),
             decoder.diffusion_module.register_forward_hook(count_s1)]
    aa=store.lock['aa'];noises=store.lock['seeds'];references={};raw_hashes={};items={};sites=lock['sites']
    for pi in sorted({s['parent'] for s in sites}):
        raw=store.load(pi);references[pi]=tuple(t.cuda() for t in raw['conditioning'])
        raw_hashes[pi]=state_hash(references[pi])
    def load_item(pi,pos=None,a=None):
        source=store.load(pi,pos,a);label=source['label']
        if label in items:return items[label]
        native,atoms=native_sequence_features(source['sequence']);inv=source['inventory']
        assert np.array_equal(atoms.atom_name,inv['atom_names']) and np.array_equal(atoms.bonds.as_array(),inv['bonds'])
        assert np.array_equal(native['ref_pos'].numpy(),inv['reference'])
        f=prepare_atom_pairs(decoder.relative_position_encoding.generate_relp(device_tree(native,'cuda')))
        co=source['coordinates'];exact=co if pos is None else co[0]
        labels=build_adapter_supervision(dict(inv,coordinates=exact[0],mask=np.ones(len(atoms),bool)),inv['bonds'],source['sequence'])
        data=dict(label=label,features=f,noises=[identity_noise(atoms,n,device='cuda') for n in noises],
                  teacher=torch.tensor(exact,device='cuda'),labels=labels,
                  ca=torch.tensor(np.flatnonzero(inv['atom_names']=='CA'),device='cuda'))
        # No target conditioning is retained in the student packet.
        items[label]=data;return data
    def decode(item,c,ni):
        return diffusion_from_conditioning(decoder,item['features'],item['noises'][ni],pack_conditioning(c),steps=1).squeeze(0)
    report=dict(complete=False,runtime=runtime,counts=counts,preflight=[],runs=[],lock_sha256=sha256(root/'lock.json'))
    (root/'coordinates').mkdir();(root/'checkpoints').mkdir()
    with torch.no_grad():
        for pi in references:
            item=load_item(pi)
            for ni in range(2):assert torch.equal(decode(item,references[pi],ni),item['teacher'][ni]),'WT replay'
        for site in sites:
            pi,pos=site['parent'],site['position'];sequence=store.rows[pi]['sequence']
            for a in aa:
                if a==sequence[pos]:continue
                item=load_item(pi,pos,a);teacher_state=tuple(t.cuda() for t in store.load(pi,pos,a)['conditioning'])
                for ni in range(2):assert torch.equal(decode(item,teacher_state,ni),item['teacher'][ni]),item['label']
                baseline=np.stack([decode(item,references[pi],ni).cpu().numpy() for ni in range(2)])
                np.savez_compressed(root/'coordinates'/f"baseline_{item['label']}.npz",coordinates=baseline)
                report['preflight'].append(item['label']);del teacher_state
    write_json(root/'report.json',report);print('PREFLIGHT complete',len(report['preflight']),counts,flush=True)
    dims=[x.shape[-1] for x in references[3]]
    for seed in lock['seeds']:
        torch.manual_seed(seed);np.random.seed(seed)
        net=ReferenceEditModel(*dims,**lock['architecture']).cuda()
        optimizer=torch.optim.AdamW(net.parameters(),lr=lock['lr'],weight_decay=1e-4,eps=1e-8)
        run=dict(seed=seed,complete=False,parameters=sum(p.numel() for p in net.parameters()),history=[],evaluations=[],invariants=[])
        report['runs'].append(run)
        def cache(pi):return net.prepare_reference(references[pi],[aa.index(a) for a in store.rows[pi]['sequence']])
        def edits(pi,pos,choices):
            old=aa.index(store.rows[pi]['sequence'][pos]);return [[(pos,old,aa.index(a))] for a in choices]
        def audit_cache():
            net.eval();errors=[]
            with torch.no_grad():
                pi=3;ref=cache(pi);seq=store.rows[pi]['sequence'];query=[[],[(36,aa.index(seq[36]),0)],[(83,aa.index(seq[83]),1)]]
                out=net(ref,query);fresh=net(cache(pi),query);reverse=net(ref,query[::-1])
                assert all(torch.equal(a,b) for a,b in zip(out,fresh))
                assert all(torch.equal(x[0],r) for x,r in zip(out,references[pi]))
                for i,q in enumerate(query):
                    alone=net(ref,[q]);error=max(float((x[i]-y[0]).abs().max()) for x,y in zip(out,alone));errors.append(error)
                    assert error<1e-4,error
                assert max(float((x-y.flip(0)).abs().max()) for x,y in zip(out,reverse))<1e-4
                wtitem=load_item(pi)
                assert torch.equal(decode(wtitem,tuple(x[0] for x in out),0),wtitem['teacher'][0])
            run['invariants'].append(dict(cache_fresh_bitwise=True,noedit_bitwise=True,order_subset_max=max(errors)))
        def evaluate(step):
            net.eval();audit_cache();begin=time.monotonic();predictions=[]
            with torch.no_grad():
                cached={pi:cache(pi) for pi in references}
                for site in sites:
                    pi,pos=site['parent'],site['position'];seq=store.rows[pi]['sequence'];choices=[a for a in aa if a!=seq[pos]]
                    # Small candidate batches bound dense writeout memory; no interaction across batch.
                    for start in range(0,19,4):
                        sub=choices[start:start+4];c=net(cached[pi],edits(pi,pos,sub))
                        for j,a in enumerate(sub):
                            item=load_item(pi,pos,a);xyz=np.stack([decode(item,tuple(x[j] for x in c),ni).cpu().numpy() for ni in range(2)])
                            path=root/'coordinates'/f'{seed}_{step}_{item["label"]}.npz';np.savez_compressed(path,coordinates=xyz)
                            predictions.append(dict(label=item['label'],path=str(path.relative_to(root)),sha256=sha256(path)))
                del cached
            ck=root/'checkpoints'/f'{seed}_{step}.pt';torch.save(dict(state_dict=net.state_dict(),architecture=net.config,seed=seed,step=step),ck)
            run['evaluations'].append(dict(step=step,predictions=predictions,seconds=time.monotonic()-begin,checkpoint=str(ck.relative_to(root)),sha256=sha256(ck)))
            write_json(root/'report.json',report);print('EVALUATE',seed,step,counts,flush=True)
        evaluate(0)
        for step in range(lock['updates']):
            net.train();optimizer.zero_grad(set_to_none=True)
            site=sites[step%2];pi,pos=site['parent'],site['position'];seq=store.rows[pi]['sequence'];choices=[a for a in aa if a!=seq[pos]]
            exposure=step//2;selected=[choices[(2*exposure+j)%19] for j in range(2)]
            ref=cache(pi);c=net(ref,edits(pi,pos,selected))
            parts=[];losses=[]
            for j,a in enumerate(selected):
                item=load_item(pi,pos,a);x=decode(item,tuple(t[j] for t in c),0)
                loss,values=coordinate_objective(x,item['teacher'][0],item['ca'],item['labels']);losses.append(loss);parts.append(values)
            loss=torch.stack(losses).mean();assert torch.isfinite(loss),step
            loss.backward()
            if step==0:
                branch={name:float(p.grad.norm()) if p.grad is not None else None for name,p in net.named_parameters() if name in ['inputs.1.weight','blocks.0.read.q.weight','aa.weight','pair_base.1.weight','input_out.weight','single_out.weight','pair_out.3.weight']}
                assert all(v is not None and v>0 and np.isfinite(v) for v in branch.values()),branch
                assert all(p.grad is None for p in decoder.parameters())
                run['gradient_audit']=branch
            norm=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True);optimizer.step();counts['updates']+=1
            stale=False
            try:net(ref,[[]])
            except RuntimeError:stale=True
            assert stale,'stale cache accepted'
            run['history'].append(dict(step=step+1,parent=pi,position=pos,aa=selected,loss=float(loss.detach()),gradient_norm=float(norm),components=parts))
            del ref,c,x,loss,losses
            if (step+1)%32==0:
                report['seconds']=time.monotonic()-started;write_json(root/'report.json',report);print('TRAIN',seed,step+1,run['history'][-1]['loss'],flush=True)
            if step+1 in (128,lock['updates']):evaluate(step+1)
        # Timings are model-only after raw reference/chemistry preparation, not C4-inclusive.
        net.eval();pi=3;pos=36;choices=[a for a in aa if a!=store.rows[pi]['sequence'][pos]];timings=[]
        with torch.no_grad():
            for repeat in range(6):
                torch.cuda.synchronize();t=time.perf_counter();r=cache(pi);torch.cuda.synchronize();build=time.perf_counter()-t
                t=time.perf_counter();c=net(r,edits(pi,pos,choices));torch.cuda.synchronize();edit=time.perf_counter()-t
                t=time.perf_counter()
                for j,a in enumerate(choices):decode(load_item(pi,pos,a),tuple(v[j] for v in c),0)
                torch.cuda.synchronize();denoise=time.perf_counter()-t
                timings.append(dict(projection_seconds=build,edit19_seconds=edit,s1_19_seconds=denoise))
            # Actual identical-workload comparison, not an extrapolation from one query.
            comparison=[]
            for repeat in range(4):
                t=time.perf_counter();shared=cache(pi)
                for a in choices:net(shared,edits(pi,pos,[a]))
                torch.cuda.synchronize();cached_time=time.perf_counter()-t
                t=time.perf_counter()
                for a in choices:net(cache(pi),edits(pi,pos,[a]))
                torch.cuda.synchronize();fresh_time=time.perf_counter()-t
                comparison.append(dict(cached=cached_time,reproject_each=fresh_time))
        run.update(complete=True,timing=timings,cache_comparison=comparison)
        del optimizer,net,c,r,shared
        for pi,raw in references.items():assert state_hash(raw)==raw_hashes[pi]
        write_json(root/'report.json',report)
    assert counts['c4']==counts['input_embedder']==0 and counts['updates']==2*lock['updates']
    for p,h in lock['code'].items(): assert sha256(root/'code'/p)==h,p
    for p,h in store.lock['weights_sha256'].items():assert sha256(Path(p))==h,p
    report.update(complete=True,seconds=time.monotonic()-started,reference_hashes=raw_hashes,
                  frozen_weights_unchanged=True,oracle_target_conditioning=False,peak_allocated_bytes=torch.cuda.max_memory_allocated())
    write_json(root/'report.json',report)
    for h in handles:h.remove()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root;t=time.monotonic()
    try:
        run_reference_editor(root);write_json(root/'execution.json',dict(complete=True,seconds=time.monotonic()-t))
    except BaseException as e:
        write_json(root/'execution.json',dict(complete=False,error=repr(e),seconds=time.monotonic()-t));raise
