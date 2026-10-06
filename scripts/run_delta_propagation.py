"""Bounded Base-C4 model-only invariance audit; no ESM or MSA search."""
import argparse
import inspect
import json
import os
import sys
import time
from pathlib import Path
import numpy as np
import torch
from fastglycan.delta_propagation import DeltaObserver,delta_statistics,tensor_digest
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.models.prefix_recycle import capture_rng_state,restore_rng_state


def run_delta_propagation(root):
    runtime=guarded_hip_runtime()
    from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
    from fastglycan.models.differentiable_mini import prepare_atom_pairs
    from protenix.utils.seed import seed_everything
    from runner.batch_inference import get_default_runner
    from run_prefix_reuse import rng_fingerprint
    lock=json.loads((root/'lock.json').read_text())
    for p,h in lock['assets'].items(): assert sha256(Path(p))==h,p
    for p,h in lock['code'].items(): assert sha256(root/'code'/p)==h,p
    seed_everything(101,deterministic=True)
    work=root/'work';work.mkdir();os.chdir(work)
    argv=sys.argv;sys.argv=sys.argv[:1]
    start=time.perf_counter()
    try:
        runner=get_default_runner(seeds=[101],n_cycle=4,n_step=200,n_sample=1,
            dtype='fp32',model_name='protenix_base_default_v0.5.0',use_msa=False,
            use_template=False,trimul_kernel='torch',triatt_kernel='torch',enable_tf32=False)
    finally: sys.argv=argv
    runner.configs.deterministic=True
    model=runner.model.eval().requires_grad_(False)
    assert not model.input_embedder.esm_configs['enable']
    assert model.template_embedder.n_blocks==0
    assert all(p.dtype==torch.float32 for p in model.parameters())
    torch.cuda.synchronize()
    report=dict(complete=False,runtime=runtime,model_load_seconds=time.perf_counter()-start,
                configuration=runner.configs.to_dict(),records=[],operator_timing=[],
                scope='Base C4 model-only/query-only MSA diagnostic; no ESM, MSA search, S1 or speedup claim',
                source_hashes={},counts=dict(c4=0,cycles=0,s1=0,updates=0))
    for module in (type(model),type(model.input_embedder),type(model.pairformer_stack.blocks[0]),type(model.pairformer_stack.blocks[0].tri_mul_out)):
        p=Path(inspect.getfile(module));report['source_hashes'][str(p)]=sha256(p)
    root.joinpath('inputs').mkdir();root.joinpath('snapshots').mkdir()
    # Prepare/freeze all inputs before model audit. This work is outside all model timers.
    inputs=[];preparation=time.perf_counter()
    for site in lock['sites']:
        wt=site['sequence'];pos=site['position']
        for aa in wt[pos]+''.join(a for a in lock['alphabet'] if a!=wt[pos]):
            seq=wt[:pos]+aa+wt[pos+1:];label=f"{site['pdb']}_{pos+1}_{aa}"
            raw,atoms=native_sequence_features(seq)
            file=root/'inputs'/f'{label}.pt';torch.save(raw,file)
            inputs.append(dict(site=site,label=label,aa=aa,sequence=seq,path=str(file),sha256=sha256(file),
                               atom_count=len(atoms),msa_shape=list(raw['msa'].shape)))
    assert all(i['msa_shape'][0]==1 for i in inputs)
    report['excluded_input_preparation_seconds']=time.perf_counter()-preparation
    write_json(root/'prepared_inputs.json',inputs)
    report['prepared_inputs_sha256']=sha256(root/'prepared_inputs.json')
    first=True;wt_values=None;wt_feature=None;begun=time.perf_counter()
    counter=model.pairformer_stack.register_forward_hook(lambda *args:report['counts'].__setitem__('cycles',report['counts']['cycles']+1))
    def forward(f):
        out=model.get_pairformer_output(f,N_cycle=4,inplace_safe=False,mc_dropout=False)
        report['counts']['c4']+=1
        return out
    with torch.no_grad():
        for item in inputs:
            site=item['site'];pos=site['position'];is_wt=item['aa']==site['sequence'][pos]
            raw=torch.load(item['path'],weights_only=True,map_location='cpu')
            f=prepare_atom_pairs(model.relative_position_encoding.generate_relp(device_tree(raw,'cuda')))
            # Host/device preparation is outside model timing; native embedding remains inside.
            seed_everything(101,deterministic=True);rng=capture_rng_state()
            if first:
                forward(f);torch.cuda.synchronize();restore_rng_state(rng);first=False
            timings=[]
            for repeat in range(2):
                restore_rng_state(rng);torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
                baseline=forward(f);torch.cuda.synchronize();timings.append(time.perf_counter()-t)
                end_rng=rng_fingerprint();peak=torch.cuda.max_memory_allocated()
                current=[tensor_digest(x.cpu().numpy()) for x in baseline]
                if repeat==0: initial_hash=current;initial_end_rng=end_rng
                else: assert current==initial_hash and end_rng==initial_end_rng
            restore_rng_state(rng)
            with DeltaObserver(model) as observer:
                observed=forward(f)
            assert all(torch.equal(a,b) for a,b in zip(baseline,observed)),item['label']
            assert rng_fingerprint()==end_rng,(item['label'],'RNG')
            values=observer.values
            values['final_s']=observed[1].cpu().numpy().copy()
            values['final_z']=observed[2].cpu().numpy().copy()
            # Actual native initialization, reconstructed from observed native projection outputs.
            # CPU arithmetic here is only a diagnostic; original forward remains untouched.
            values['z_init_formula']=values['z_left'][:,None,:]+values['z_right'][None,:,:]+values['relpos_embedded']+values['bond_embedded']
            feature={k:v.cpu().numpy() for k,v in raw.items() if isinstance(v,torch.Tensor)}
            if is_wt:
                wt_values=values;wt_feature=feature
                # Repeat all observation points on WT to establish the instrumentation noise floor.
                restore_rng_state(rng)
                with DeltaObserver(model) as repeat_observer: repeated=forward(f)
                assert all(np.array_equal(v,repeat_observer.values[k]) for k,v in observer.values.items() if k not in ('final_s','final_z','z_init_formula'))
                assert rng_fingerprint()==end_rng
                del repeated,repeat_observer
            assert set(wt_values)==set(values)
            stats={k:delta_statistics(wt_values[k],v,pos,spectral=not is_wt) for k,v in values.items()}
            leaves={k:dict(same_shape=v.shape==wt_feature[k].shape,
                           exact_equal=np.array_equal(v,wt_feature[k])) for k,v in feature.items() if k in wt_feature}
            sample={}
            for k,v in values.items():
                sample[k]=v[:,:,::max(1,v.shape[-1]//8)][:,:,:8] if v.ndim==3 and v.shape[0]==v.shape[1] else v
            snapshot=root/'snapshots'/f"{item['label']}.npz";np.savez(snapshot,**sample)
            record=dict(label=item['label'],pdb=site['pdb'],position=pos,aa=item['aa'],is_wt=is_wt,
                        atom_count=item['atom_count'],length=len(item['sequence']),features=leaves,
                        c4_seconds=timings,peak_allocated_bytes=peak,conditioning_sha256=current,
                        plain_repeated_bitwise=True,hook_replay_bitwise=True,hook_rng_equal=True,
                        observed_points=len(values),statistics=stats,snapshot_sha256=sha256(snapshot))
            report['records'].append(record)
            # Separate non-copying CUDA-event instrumentation on each WT. Inclusive ranges; do not sum nested ranges.
            if is_wt:
                events=[];handles=[];pending={}
                modules={n:m for n,m in model.named_modules() if n in ('input_embedder','msa_module','pairformer_stack') or n.endswith(('tri_mul_out','tri_mul_in','tri_att_start','tri_att_end','pair_transition'))}
                for name,module in modules.items():
                    def pre(m,a,n=name):
                        ev=torch.cuda.Event(enable_timing=True);ev.record();pending[n]=ev
                    def post(m,a,o,n=name):
                        ev=torch.cuda.Event(enable_timing=True);ev.record();events.append((n,pending.pop(n),ev))
                    handles.extend([module.register_forward_pre_hook(pre),module.register_forward_hook(post)])
                restore_rng_state(rng)
                try: timed=forward(f);torch.cuda.synchronize()
                finally:
                    for h in handles:h.remove()
                assert all(torch.equal(a,b) for a,b in zip(baseline,timed)) and rng_fingerprint()==end_rng
                rows=[dict(module=n,ms=a.elapsed_time(b)) for n,a,b in events]
                report['operator_timing'].append(dict(pdb=site['pdb'],events=rows,bitwise=True))
                del timed
            report['active']=item['label'];report['audit_seconds']=time.perf_counter()-begun
            write_json(root/'report.json',report)
            print(item['label'],len(report['records']),timings,flush=True)
            del observer,values,observed,baseline,f,raw,sample
    counter.remove()
    assert len(report['records'])==60 and report['counts']['c4']==187,report['counts']
    assert report['counts']['cycles']==748,report['counts']
    for p,h in lock['assets'].items(): assert sha256(Path(p))==h
    for p,h in lock['code'].items(): assert sha256(root/'code'/p)==h
    report['complete']=True;write_json(root/'report.json',report)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    root=parser.parse_args().root;started=time.perf_counter()
    try:
        run_delta_propagation(root)
        write_json(root/'execution.json',dict(complete=True,seconds=time.perf_counter()-started))
    except BaseException as e:
        write_json(root/'execution.json',dict(complete=False,error=repr(e),seconds=time.perf_counter()-started));raise
