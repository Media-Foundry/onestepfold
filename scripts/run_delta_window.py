"""All-channel mid-depth Base-C4 audit on twelve previously frozen inputs."""
import argparse,json,os,sys,time,inspect
from pathlib import Path
import numpy as np
import torch
from fastglycan.delta_window import DeltaWindowObserver,ContractionTimer,window_statistics
from fastglycan.delta_propagation import tensor_digest
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.models.prefix_recycle import capture_rng_state,restore_rng_state


def run_delta_window(root):
    runtime=guarded_hip_runtime()
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import prepare_atom_pairs
    from protenix.utils.seed import seed_everything
    from runner.batch_inference import get_default_runner
    from run_prefix_reuse import rng_fingerprint
    lock=json.loads((root/'lock.json').read_text())
    for p,h in lock['assets'].items():assert sha256(Path(p))==h,p
    for p,h in lock['code'].items():assert sha256(root/'code'/p)==h,p
    seed_everything(101,deterministic=True)
    work=root/'work';work.mkdir();os.chdir(work);argv=sys.argv;sys.argv=sys.argv[:1];t=time.perf_counter()
    try:
        runner=get_default_runner(seeds=[101],n_cycle=4,n_step=200,n_sample=1,dtype='fp32',
            model_name='protenix_base_default_v0.5.0',use_msa=False,use_template=False,
            trimul_kernel='torch',triatt_kernel='torch',enable_tf32=False)
    finally:sys.argv=argv
    runner.configs.deterministic=True;model=runner.model.eval().requires_grad_(False)
    assert not model.input_embedder.esm_configs['enable'] and model.template_embedder.n_blocks==0
    assert len(model.pairformer_stack.blocks)==48
    assert all(p.dtype==torch.float32 for p in model.parameters())
    torch.cuda.synchronize();load_time=time.perf_counter()-t
    report=dict(complete=False,runtime=runtime,model_load_seconds=load_time,records=[],counts=dict(c4=0,cycles=0,s1=0,updates=0),
                configuration=runner.configs.to_dict(),source_hashes={})
    for cls in (type(model),type(model.input_embedder),type(model.pairformer_stack.blocks[0]),type(model.pairformer_stack.blocks[0].tri_mul_out)):
        p=Path(inspect.getfile(cls));report['source_hashes'][str(p)]=sha256(p)
    previous=json.loads(Path(lock['previous_report']).read_text())
    references={r['label']:r['conditioning_sha256'] for r in previous['records']}
    root.joinpath('snapshots').mkdir();start=time.perf_counter();first=True;wt=None
    handle=model.pairformer_stack.register_forward_hook(lambda *a:report['counts'].__setitem__('cycles',report['counts']['cycles']+1))
    def forward(f):
        c=model.get_pairformer_output(f,N_cycle=4,inplace_safe=False,mc_dropout=False)
        report['counts']['c4']+=1
        return c
    def check(c,label):
        hashes=[tensor_digest(x.cpu().numpy()) for x in c]
        assert hashes==references[label],(label,'previous C4 mismatch')
        return hashes
    with torch.no_grad():
        for item in lock['inputs']:
            label=item['label'];site=item['site'];pos=site['position'];is_wt=item['aa']==site['sequence'][pos]
            raw=torch.load(item['path'],weights_only=True,map_location='cpu')
            assert list(raw['msa'].shape)==item['msa_shape']
            f=prepare_atom_pairs(model.relative_position_encoding.generate_relp(device_tree(raw,'cuda')))
            seed_everything(101,deterministic=True);rng=capture_rng_state()
            if first:forward(f);torch.cuda.synchronize();first=False
            times=[];final_rng=None
            for repeat in range(3):
                restore_rng_state(rng);torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
                c=forward(f);torch.cuda.synchronize();times.append(time.perf_counter()-t);peak=torch.cuda.max_memory_allocated()
                hashes=check(c,label);now=rng_fingerprint()
                if final_rng is None:final_rng=now
                else:assert final_rng==now
                del c
            restore_rng_state(rng)
            with DeltaWindowObserver(model) as observer:c=forward(f)
            check(c,label);assert rng_fingerprint()==final_rng
            values=observer.values
            assert len(values)==66,len(values)
            del c
            if is_wt:
                wt=values
                restore_rng_state(rng)
                with DeltaWindowObserver(model) as repeated:c=forward(f)
                check(c,label);assert rng_fingerprint()==final_rng
                assert all(tensor_digest(v)==tensor_digest(repeated.values[k]) for k,v in values.items())
                del repeated,c
            t=time.perf_counter()
            stats={k:window_statistics(wt[k],v,pos) for k,v in values.items()} if not is_wt else {}
            spectral_time=time.perf_counter()-t
            file=root/'snapshots'/f'{label}.npz';np.savez(file,**values)
            profile=[]
            for repeat in range(2):
                restore_rng_state(rng);torch.cuda.synchronize();t=time.perf_counter()
                with ContractionTimer(model) as timer:c=forward(f)
                torch.cuda.synchronize();wall=time.perf_counter()-t
                check(c,label);assert rng_fingerprint()==final_rng
                events=timer.rows()
                assert len(events)==768,len(events)
                profile.append(dict(wall_seconds=wall,events=events,bitwise_replay=True,rng_equal=True));del c,timer
            report['records'].append(dict(label=label,pdb=site['pdb'],position=pos,aa=item['aa'],is_wt=is_wt,
                length=len(item['sequence']),atom_count=item['atom_count'],plain_c4_seconds=times,
                peak_allocated_bytes=peak,conditioning_sha256=hashes,previous_archive_bitwise=True,all_rng_equal=True,
                observed_points=len(values),snapshot_sha256=sha256(file),statistics=stats,
                excluded_spectral_seconds=spectral_time,profiles=profile))
            report.update(active=label,seconds=time.perf_counter()-start)
            write_json(root/'report.json',report);print(label,len(report['records']),times,'spectra',spectral_time,flush=True)
            del observer,values,stats,raw,f
    handle.remove()
    assert report['counts']==dict(c4=76,cycles=304,s1=0,updates=0),report['counts']
    for p,h in lock['assets'].items():assert sha256(Path(p))==h,p
    for p,h in lock['code'].items():assert sha256(root/'code'/p)==h,p
    report['complete']=True;write_json(root/'report.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root;t=time.perf_counter()
    try:
        run_delta_window(root);write_json(root/'execution.json',dict(complete=True,seconds=time.perf_counter()-t))
    except BaseException as e:
        write_json(root/'execution.json',dict(complete=False,error=repr(e),seconds=time.perf_counter()-t));raise
