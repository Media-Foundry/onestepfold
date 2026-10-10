"""Native Mini reference replay and paired-suffix gradient audit; no optimization."""
import argparse
import importlib.util
import json
from pathlib import Path
import time

import torch

from fastglycan.anchor_gradients import (flat_gradients, gradient_description,
                                         initial_site_gradients)
from fastglycan.models.anchored_pair_recovery import (ReferenceAnchoredPairRecovery,
    reference_gradient_proxy, backward_reference_proxy)
from fastglycan.models.compensated_recycle import initialize_cached_recycle, native_recycle_step
from fastglycan.models.prefix_recycle import capture_rng_state, restore_rng_state
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_multiref import editor_state_digest
from fastglycan.stage_pair_data import PairStageCapture, StagePairData
from run_recycle_lora import LoRARuntime
from run_reference_editor import state_hash


def audit_reference_anchor(root):
    start = time.monotonic()
    lock = json.loads((root/'audit_lock.json').read_text())
    assert sha256(root/'protocol.md') == lock['protocol_sha256']
    for name, digest in lock['code'].items():
        assert sha256(root/'code'/name) == digest, name
    full = Path(lock['fullbatch_root'])
    assert sha256(full/'training_lock.json') == lock['fullbatch_lock_sha256']
    source = json.loads((full/'training_lock.json').read_text())
    legacy_path = full/'code/src/fastglycan/models/stage_pair_recovery.py'
    assert sha256(legacy_path) == source['code']['src/fastglycan/models/stage_pair_recovery.py']
    spec = importlib.util.spec_from_file_location('legacy_native_suffix',legacy_path)
    legacy = importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    rt = LoRARuntime(Path(source['source']), str(root/'work'));b=rt.base
    data = PairRecoveryData(source['build_root'],source['cache_manifest_sha256'])
    stages = StagePairData(source['stage_root'],source['stage_manifest_sha256'])
    reference_guard={pi:state_hash(x[0]) for pi,x in rt.prefixes.items()}
    (root/'reference_cache').mkdir(exist_ok=False)
    cache={}; records=[]
    report=dict(complete=False,phase='reference_cache',seeds=[],reference_records=records,
                counts=dict(identity_candidate_forwards=0,legacy_candidate_forwards=0,
                    identity_reference_forwards=0,gradient_candidate_forwards=0,
                    gradient_candidate_backwards=0,gradient_reference_forwards=0,
                    gradient_reference_backwards=0,joint_candidate_forwards=0,
                    proxy_candidate_forwards=0,comparison_reference_forwards=0,
                    comparison_candidate_backward_branches=0,comparison_reference_backward_branches=0,
                    joint_autograd_calls=0,proxy_backward_calls=0,trained_state_forwards=0),
                audit_lock_sha256=sha256(root/'audit_lock.json'),parameter_updates=0)

    def save():
        report.update(seconds=time.monotonic()-start,native_counts=b.counts)
        write_json(root/'report.json',report)

    save()
    with torch.no_grad():
        for pi in sorted(b.references):
            wt=b.references[pi];item=b.item(pi)
            init=initialize_cached_recycle(rt.model,item['features'],wt[0])
            state,rng=rt.prefixes[pi];ambient=capture_rng_state()
            try:
                with PairStageCapture(rt.model.pairformer_stack) as capture:
                    final=native_recycle_step(rt.model,item['features'],init,state,rng=rng)
            finally:restore_rng_state(ambient)
            assert torch.equal(init.inputs,wt[0])
            assert all(torch.equal(x,y) for x,y in zip(final,wt[1:])),pi
            path=root/'reference_cache'/f'{pi}.pt'
            payload=dict(boundary=capture.values[13].cpu(),warm_hint=capture.values[14].cpu())
            torch.save(payload,path);cache[pi]=payload
            records.append(dict(parent=pi,path=str(path.relative_to(root)),sha256=sha256(path),bytes=path.stat().st_size))
            save()
    assert len(cache)==24 and b.counts['recycle']==24

    def forbid(*args):raise AssertionError('native folding/input/decoding forbidden after WT cache')
    handles=[rt.model.pairformer_stack.register_forward_pre_hook(forbid),
             rt.model.input_embedder.register_forward_pre_hook(forbid),
             rt.model.diffusion_module.register_forward_pre_hook(forbid)]
    def fetch(site):
        out=[];pi,pos=site['parent_index'],site['position_zero_based']
        assert site['role_n15']=='train'
        for aa in site['candidates']:
            label=b.label(pi,pos,aa)
            out.append((b.aa.index(aa),data.base(label),stages.load(label,training=False)[0],data.target(label)))
        return out
    vectors_all={}
    for seed in lock['seeds']:
        model=ReferenceAnchoredPairRecovery(list(rt.model.pairformer_stack.blocks[-2:]),seed).cuda().eval()
        original=legacy.StagePairRecovery(list(rt.model.pairformer_stack.blocks[-2:]),seed).cuda().eval()
        initial=editor_state_digest(model)
        assert initial==editor_state_digest(original)==source['initial_hashes'][str(seed)]
        report['phase']=f'identity_{seed}';save()
        with torch.no_grad():
            for key in source['eval_sites']:
                site=b.sites[key];pi,pos=site['parent_index'],site['position_zero_based'];old=b.aa.index(site['original_aa'])
                wt=b.references[pi];ref=rt.prefixes[pi][0][1]
                anchor=model.prepare_reference(wt,cache[pi]['boundary'].cuda(),ref,pos,old)
                report['counts']['identity_reference_forwards']+=1
                assert torch.count_nonzero(anchor.drift)==0
                assert model(wt,cache[pi]['boundary'].cuda(),ref,pos,old,old,anchor=anchor) is wt
                for aa in site['candidates']:
                    label=b.label(pi,pos,aa);base=data.base(label);boundary=stages.load(label,training=False)[0]
                    c=model(base,boundary,ref,pos,old,b.aa.index(aa),anchor=anchor)
                    previous,_=original(base,boundary,ref,pos,old,b.aa.index(aa))
                    assert all(torch.equal(x,y) for x,y in zip(c,previous))
                    assert torch.equal(c[2],base[2]) and c[0] is base[0] and c[1] is base[1]
                    report['counts']['identity_candidate_forwards']+=1
                    report['counts']['legacy_candidate_forwards']+=1
            save()
        del original
        report['phase']=f'gradients_{seed}';save();rows=[];sums=None
        for key in source['train_sites']:
            site=b.sites[key];pi,pos=site['parent_index'],site['position_zero_based'];old=b.aa.index(site['original_aa'])
            candidates=fetch(site)
            vectors,row=initial_site_gradients(model,candidates,b.references[pi],cache[pi]['boundary'].cuda(),
                rt.prefixes[pi][0][1],pos,old,source['site_scale_squared'][key])
            sums={k:v.clone() for k,v in vectors.items()} if sums is None else {k:sums[k]+v for k,v in vectors.items()}
            rows.append(dict(site=key,**row))
            report['counts']['gradient_candidate_forwards']+=len(candidates)
            report['counts']['gradient_candidate_backwards']+=2*len(candidates)
            report['counts']['gradient_reference_forwards']+=1
            report['counts']['gradient_reference_backwards']+=1
            print('ANCHOR_GRADIENT_SITE',seed,key,flush=True);save();del candidates,vectors
        means={k:v/len(rows) for k,v in sums.items()};refrec=source['gradient_references'][str(seed)]
        assert sha256(Path(refrec['path']))==refrec['sha256']
        saved=torch.load(refrec['path'],map_location='cpu',weights_only=False)['full_gradient']
        relative=float((means['raw']-saved).norm()/saved.norm());assert relative<=5e-6,relative
        vector_path=root/f'vectors_{seed}.pt';torch.save(means,vector_path)
        vectors_all[seed]=means
        seed_record=dict(seed=seed,initial_sha256=initial,sites=rows,gradient_reference_relative_error=relative,
            full_objective=sum(r['raw'] for r in rows)/len(rows),full=gradient_description(means),
            vector_path=vector_path.name,vector_sha256=sha256(vector_path))
        report['seeds'].append(seed_record);save()

        # Independent actual-model joint graph versus one reference pullback.
        report['phase']=f'pullback_{seed}';save()
        site=b.sites[source['train_sites'][0]];pi,pos=site['parent_index'],site['position_zero_based'];old=b.aa.index(site['original_aa'])
        candidates=fetch(site);wt=b.references[pi];boundary=cache[pi]['boundary'].cuda();ref=rt.prefixes[pi][0][1]
        scale=source['site_scale_squared'][site['site_key']]
        anchor=model.prepare_reference(wt,boundary,ref,pos,old)
        loss=sum((model(base,z,ref,pos,old,aa,anchor=anchor)[2]-target).square().mean()/scale/len(candidates)
                 for aa,base,z,target in candidates)
        joint=flat_gradients(loss,list(model.parameters())).cpu().double()
        del loss,anchor
        model.zero_grad(set_to_none=True)
        anchor=model.prepare_reference(wt,boundary,ref,pos,old);proxy=reference_gradient_proxy(anchor)
        for aa,base,z,target in candidates:
            loss=(model(base,z,ref,pos,old,aa,anchor=proxy)[2]-target).square().mean()/scale/len(candidates)
            loss.backward()
        backward_reference_proxy(anchor,proxy)
        streamed=torch.cat([p.grad.detach().cpu().double().flatten() for p in model.parameters()])
        rel=float((joint-streamed).norm()/joint.norm());assert rel<=5e-5,rel
        seed_record['pullback']=dict(site=site['site_key'],relative=rel,max_abs=float((joint-streamed).abs().max()),
            joint_norm=float(joint.norm()),proxy_norm=float(streamed.norm()))
        report['counts']['joint_candidate_forwards']+=len(candidates)
        report['counts']['proxy_candidate_forwards']+=len(candidates)
        report['counts']['comparison_reference_forwards']+=2
        report['counts']['comparison_candidate_backward_branches']+=2*len(candidates)
        report['counts']['comparison_reference_backward_branches']+=2
        report['counts']['joint_autograd_calls']+=1
        report['counts']['proxy_backward_calls']+=len(candidates)+1
        assert editor_state_digest(model)==initial
        del model,anchor,proxy,loss,candidates,means,sums,joint,streamed
        torch.cuda.empty_cache();save()

    # Already fixed historical parameters: functional invariants only.
    model=ReferenceAnchoredPairRecovery(list(rt.model.pairformer_stack.blocks[-2:]),272001).cuda().eval()
    checkpoint=Path(lock['functional_checkpoint']);assert sha256(checkpoint)==lock['functional_checkpoint_sha256']
    model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=False)['state_dict'])
    site=b.sites[source['train_sites'][0]];pi,pos=site['parent_index'],site['position_zero_based'];old=b.aa.index(site['original_aa'])
    ref=rt.prefixes[pi][0][1];wt=b.references[pi];boundary=cache[pi]['boundary'].cuda()
    with torch.no_grad():
        anchor=model.prepare_reference(wt,boundary,ref,pos,old);correct=[];raw=[]
        report['counts']['trained_state_forwards']+=1
        for aa in site['candidates']:
            label=b.label(pi,pos,aa);base=data.base(label);z=stages.load(label,training=False)[0]
            correct.append(model(base,z,ref,pos,old,b.aa.index(aa),anchor=anchor)[2])
            raw.append(model.run_pair_suffix(base,z,ref,pos,old,b.aa.index(aa))[0][2])
            report['counts']['trained_state_forwards']+=2
        a,u=torch.stack(correct).double(),torch.stack(raw).double()
        maximum=float(((a-a.mean(0))-(u-u.mean(0))).abs().max())
        bound=2*torch.finfo(torch.float32).eps*float((u.abs()+anchor.drift.double().abs()).max())
        assert maximum<=bound,(maximum,bound)
        aa=site['candidates'][0];label=b.label(pi,pos,aa);base=data.base(label);z=stages.load(label,training=False)[0]
        assert torch.equal(correct[0],model(base,z,ref,pos,old,b.aa.index(aa),anchor=anchor)[2])
        report['counts']['trained_state_forwards']+=1
        assert model(wt,boundary,ref,pos,old,old,anchor=anchor) is wt
        report['trained_state_check']=dict(site=site['site_key'],centered_max_abs=maximum,
            fp32_rounding_bound=bound,anchor_norm=float(anchor.drift.norm()),no_edit_exact=True,order_independent=True)
    for handle in handles:handle.remove()
    rt.finish()
    assert reference_guard=={pi:state_hash(x[0]) for pi,x in rt.prefixes.items()}
    assert b.counts==dict(c4=0,input_embedder=0,recycle=24,s1=0,updates=0)
    assert report['counts']['identity_candidate_forwards']==1824
    assert report['counts']['gradient_candidate_forwards']==1026
    assert report['counts']['gradient_candidate_backwards']==2052
    report.update(complete=True,phase='closed',reference_cache_bytes=sum(r['bytes'] for r in records),
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),promoted=False,new_training_started=False)
    save()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    audit_reference_anchor(parser.parse_args().root)
