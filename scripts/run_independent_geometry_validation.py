#!/usr/bin/env python3
"""Frozen32-protein raw/mean/tail experiment; no selection or tuning from outputs."""
import argparse,concurrent.futures,copy,json,os,signal,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json

SEEDS=(300007,300017,300023)


def raw(a):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import full_recycle_pairformer,diffusion_from_conditioning,prepare_atom_pairs
    from fastglycan.hybrid_proposals import identity_noise
    lock=json.loads((a.root/'runtime_lock.json').read_text());row=json.loads((a.root/'panel32.json').read_text())[a.index];g=row['group_id']
    folder=a.root/'proteins'/g/'raw';folder.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    report=dict(complete=False,group_id=g,pdb_id=row['pdb_id'],results={},failures={},runtime_lock_sha256=sha256(a.root/'runtime_lock.json'))
    def save():write_json(folder/'report.json',report)
    def expired(signum,frame):raise TimeoutError('1800s raw prediction budget including shared conditioning for first seed')
    signal.signal(signal.SIGALRM,expired);torch.set_num_threads(1);torch.cuda.reset_peak_memory_stats();save()
    try:
        for f,h in lock['source_hashes'].items():assert sha256(Path(f))==h
        runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
        assert all(p.dtype==torch.float32 for p in model.parameters() if p.is_floating_point())
        torch.serialization.add_safe_globals([argparse.Namespace])
        from protenix.data.esm.compute_esm import load_esm_model
        esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
        packet=Path(row['chemistry']['packet_dir'])/'native.pt';assert sha256(packet)==row['chemistry']['files']['native.pt']
        native=torch.load(packet,map_location='cpu',weights_only=False);atoms=native['atoms'];base=device_tree(native['features'],'cuda')
        assert len(set(atoms.chain_id))==1
        report.update(resolved_config=runner.configs.to_dict(),model=rt.MODEL,device=torch.cuda.get_device_name(0),load_seconds=time.monotonic()-start,conditioning_cycles=4,conditioning_shared_across_three_noises=True)
        save();first_start=time.monotonic();signal.alarm(1800)
        with torch.no_grad():
            tokens=alphabet.get_batch_converter()([('sequence',row['sequence'])])[2].cuda()
            base['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
            del esm,tokens;torch.cuda.empty_cache()
            features=prepare_atom_pairs(model.relative_position_encoding.generate_relp(copy.deepcopy(base)))
            counts={'pairformer':0,'diffusion':0}
            def counted(name):
                def hook(module,args,output):counts[name]+=1
                return hook
            ph=model.pairformer_stack.register_forward_hook(counted('pairformer'));dh=model.diffusion_module.register_forward_hook(counted('diffusion'))
            point=full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False)
            shapes=[x.shape for x in point];sizes=[x.numel() for x in point]
            conditioning=tuple(x.reshape(s) for x,s in zip(torch.cat([x.flatten() for x in point]).split(sizes),shapes));del point
            assert counts['pairformer']==4
            torch.cuda.synchronize();report['conditioning_seconds']=time.monotonic()-first_start;save()
            for j,seed in enumerate(SEEDS):
                if j:signal.alarm(1800)
                t=time.monotonic();before=counts['diffusion'];noise=identity_noise(atoms,seed,device='cuda')
                x=diffusion_from_conditioning(model,features,noise,conditioning,steps=1)
                torch.cuda.synchronize();signal.alarm(0);assert counts['diffusion']-before==1 and torch.isfinite(x).all()
                file=folder/f'{seed}.npz';np.savez_compressed(file,coordinates=x.detach().cpu().numpy().reshape(-1,3),atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id,sequence=row['sequence'])
                report['results'][str(seed)]=dict(file=str(file),sha256=sha256(file),seconds=time.monotonic()-t,diffusion_nfe=1,schedule=model.inference_noise_scheduler(N_step=1,device='cpu',dtype=torch.float32).tolist(),initial_noise='identity-key',augmentation='identity',mc_dropout=False,gamma0=0,noise_scale_lambda=1,step_scale_eta=1,stable_euler=True)
                save()
            ph.remove();dh.remove()
        report['complete']=True
    except Exception:
        signal.alarm(0);report['error']=traceback.format_exc()
        for s in SEEDS:
            if str(s) not in report['results']:report['failures'][str(s)]='raw process failed; no altered-setting retry'
    report.update(seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved());save()
    if not report['complete']:raise RuntimeError(report['error'])


def repair(a):
    from run_anchored_geometry import case
    torch.cuda.reset_peak_memory_stats()
    try:case(argparse.Namespace(root=a.root,case=a.index))
    finally:
        p=a.root/'cases'/f'{a.index:02d}'/'report.json'
        if p.exists():
            x=json.loads(p.read_text());x.update(peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved());write_json(p,x)


def batch(a):
    root=a.root;lock=json.loads((root/'runtime_lock.json').read_text());rows=json.loads((root/'panel32.json').read_text());assert len(rows)==32
    assert not (root/'controller.json').exists();write_json(root/'controller.json',dict(pid=os.getpid(),phase='running',proteins=32,devices=list(range(8))))
    def execute(cmd,env,path,timeout):
        with path.open('x') as log:
            t=time.monotonic()
            try:p=subprocess.run(cmd,env=env,stdout=log,stderr=log,timeout=timeout);return dict(returncode=p.returncode,seconds=time.monotonic()-t)
            except subprocess.TimeoutExpired:return dict(returncode=124,seconds=time.monotonic()-t,reason='fixed external timeout')
    def worker(device):
        env=dict(os.environ,ROCR_VISIBLE_DEVICES=str(device),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1');results=[]
        for index in range(device,32,8):
            row=rows[index];g=row['group_id'];folder=root/'proteins'/g;folder.mkdir(parents=True,exist_ok=True)
            raw_exit=execute([sys.executable,str(Path(__file__).resolve()),'--root',str(root),'--mode','raw','--index',str(index)],env,folder/'raw.log',5400)
            p=folder/'raw/report.json';raw_report=json.loads(p.read_text()) if p.exists() else dict(results={})
            output=dict(index=index,group_id=g,raw=raw_exit,repairs=[])
            for objective in ['mean','tail']:
                repair_root=folder/objective;repair_root.mkdir()
                available=[dict(arm='controlled_s1',seed=s,**raw_report['results'][str(s)]) for s in SEEDS if str(s) in raw_report['results']]
                entry=dict(objective=objective,sequence=row['sequence'],cases=available,reference=str(folder/'chemical_reference.npz'),reference_sha256=sha256(folder/'chemical_reference.npz'),variants=str(folder/'variants.json'),variants_sha256=sha256(folder/'variants.json'),topology=str(folder/'topology.pt'),topology_sha256=sha256(folder/'topology.pt'),source_hashes=lock['source_hashes'],scope='locked independent32, fixed source subgroups; iterative repair only')
                write_json(repair_root/'lock.json',entry)
                for i,item in enumerate(available):
                    result=execute([sys.executable,str(Path(__file__).resolve()),'--root',str(repair_root),'--mode','repair','--index',str(i)],env,folder/f'{objective}_{item["seed"]}.log',900)
                    output['repairs'].append(dict(objective=objective,seed=item['seed'],**result));write_json(folder/'execution.json',output)
                from run_anchored_geometry import collect
                collect(repair_root)
            write_json(folder/'execution.json',output);results.append(output)
        return results
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:results=[x for part in ex.map(worker,range(8)) for x in part]
    write_json(root/'execution.json',dict(complete=True,proteins=results,runtime_lock_sha256=sha256(root/'runtime_lock.json')))
    write_json(root/'controller.json',dict(pid=os.getpid(),phase='finished',proteins=32))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['raw','repair','batch'],required=True);p.add_argument('--index',type=int);a=p.parse_args();a.root=a.root.resolve()
    globals()[a.mode](a)
