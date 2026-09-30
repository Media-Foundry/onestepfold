#!/usr/bin/env python3
"""Two fixed smooth-lDDT widths at archived TRAIN initial states; no optimization."""
import argparse
import json
from pathlib import Path
import time
import traceback
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_temperature_probe(root):
    assert not (root/'lock.json').exists()
    previous=root.parent/'diffusion_gradient_budget_v1_20260930'
    old=json.loads((previous/'lock.json').read_text());audit=json.loads((previous/'audit.json').read_text())
    assert audit['complete'] and audit['lock_sha256']==sha256(previous/'lock.json')
    inputs=dict(old['input_hashes'])
    # Keep only initial diagnostic inputs: terminal/student outputs are not read.
    inputs={p:h for p,h in inputs.items() if '/diffusion_learning_evaluation_' not in p and not p.endswith('.pt') or p.endswith(('conditioning.pt','gt_supervision.pt','native.pt'))}
    for row in old['rows']:
        for seed in old['seeds']:
            path=previous/'points'/row['group_id']/f'initial_{seed}'/'gradients.pt'
            report=json.loads((path.parent/'report.json').read_text());assert sha256(path)==report['gradient_sha256']
            inputs[str(path)]=report['gradient_sha256']
    assignments=[[] for _ in range(4)];loads=[0]*4
    for row in sorted(old['rows'],key=lambda r:(-len(r['sequence']),r['group_id'])):
        i=min(range(4),key=lambda j:(loads[j],j));assignments[i].append(row);loads[i]+=len(row['sequence'])**2
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']}
    write_json(root/'lock.json',dict(previous=str(previous),cache=old['cache'],source=old['source'],
        rows=old['rows'],seeds=old['seeds'],assignments=assignments,temperatures=[.1,1.],
        hashes=hashes,input_hashes=inputs,weight_stats=old['weight_stats'],
        initial_only=True,no_optimizer=True,planned_points=32,planned_vjps=64))


def run_temperature_probe(root,index):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.models.diffusion_adapter import attach_diffusion_adapter
    from fastglycan.hybrid_proposals import identity_noise
    from fastglycan.smooth_lddt_supervision import smooth_lddt_loss
    lock=json.loads((root/'lock.json').read_text());cache=Path(lock['cache']);source=Path(lock['source'])
    folder=root/f'worker_{index}';folder.mkdir(exist_ok=False);begin=time.monotonic()
    report=dict(complete=False,index=index,points=[],lock_sha256=sha256(root/'lock.json'))
    try:
        for path,h in lock['hashes'].items():assert sha256(Path(path))==h
        torch.set_num_threads(1);runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32'
        model=runner.model.eval().requires_grad_(False)
        original=[(p,p.detach().cpu().clone()) for p in model.parameters()]
        assert all(p.dtype==torch.float32 for p,_ in original)
        adapters=attach_diffusion_adapter(model);params=[];names=[]
        for name,a in adapters.items():
            for kind,p in a.named_parameters():params.append(p);names.append(name+'.'+kind)
        counts=dict(diffusion=0,pairformer=0)
        dh=model.diffusion_module.register_forward_hook(lambda *args:counts.__setitem__('diffusion',counts['diffusion']+1))
        ph=model.pairformer_stack.register_forward_hook(lambda *args:counts.__setitem__('pairformer',counts['pairformer']+1))
        for row in lock['assignments'][index]:
            g=row['group_id'];data=cache/'examples'/g;assert row['role']=='train'
            for path in [data/'conditioning.pt',data/'gt_supervision.pt',source/'chemistry'/g/'native.pt']:
                assert sha256(path)==lock['input_hashes'][str(path)]
            saved=torch.load(data/'conditioning.pt',map_location='cpu',weights_only=False);assert saved['role']=='train'
            flat=saved['conditioning_flat'].cuda();features=device_tree(saved['features'],'cuda')
            conditioning=tuple(x.reshape(s) for x,s in zip(flat.split(saved['sizes']),saved['shapes']))
            atoms=torch.load(source/'chemistry'/g/'native.pt',map_location='cpu',weights_only=False)['atoms']
            labels=torch.load(data/'gt_supervision.pt',map_location='cpu',weights_only=False)['smooth']
            for seed in lock['seeds']:
                noise=identity_noise(atoms,seed,device='cuda');cpu=torch.get_rng_state();gpu=torch.cuda.get_rng_state()
                x=diffusion_from_conditioning(model,features,noise,conditioning,steps=1).reshape(-1,3)
                assert np.array_equal(x.detach().cpu().numpy(),np.load(data/f's1_seed{seed}.npy'))
                losses=[];vectors=[]
                for t in lock['temperatures']:
                    loss=smooth_lddt_loss(x,labels,temperature=t);losses.append(float(loss.detach()))
                    gradient=torch.autograd.grad(loss,params,retain_graph=t==.1)
                    vectors.append(torch.cat([v.detach().flatten() for v in gradient]).cpu());del gradient,loss
                matrix=torch.stack(vectors);assert torch.isfinite(matrix).all()
                previous=Path(lock['previous'])/'points'/g/f'initial_{seed}'/'gradients.pt'
                assert sha256(previous)==lock['input_hashes'][str(previous)]
                old=torch.load(previous,map_location='cpu',weights_only=False)
                assert old['parameter_names']==names and torch.equal(matrix[0],old['raw_gradients'][old['names'].index('smooth_lddt')])
                norms=matrix.double().norm(dim=1);cos=float(torch.dot(matrix[0].double(),matrix[1].double())/norms.prod())
                assert torch.equal(cpu,torch.get_rng_state()) and torch.equal(gpu,torch.cuda.get_rng_state())
                target=root/'points'/g/f'{seed}';target.mkdir(parents=True,exist_ok=False)
                torch.save(dict(gradients=matrix,parameter_names=names,temperatures=lock['temperatures']),target/'gradients.pt')
                point=dict(group_id=g,pdb_id=row['pdb_id'],length=len(row['sequence']),seed=seed,
                    losses=losses,norms=norms.tolist(),cosine=cos,coordinate_replay=True,old_gradient_exact=True,
                    path=str(target/'gradients.pt'),sha256=sha256(target/'gradients.pt'))
                write_json(target/'report.json',point);report['points'].append(point);write_json(folder/'report.json',report)
                del x,matrix,vectors,old,noise
            del saved,features,flat,conditioning,atoms,labels
            torch.cuda.empty_cache()
        assert counts==dict(diffusion=2*len(lock['assignments'][index]),pairformer=0)
        assert all(torch.equal(p.detach().cpu(),old) for p,old in original)
        assert all(p.grad is None for p in model.parameters())
        dh.remove();ph.remove();report.update(complete=True,counts=counts,base_unchanged=len(original),optimizer_updates=0)
    except Exception:report['error']=traceback.format_exc()
    report['seconds']=time.monotonic()-begin;write_json(folder/'report.json',report)
    if not report['complete']:raise RuntimeError(report.get('error'))


def finish_temperature_probe(root):
    lock=json.loads((root/'lock.json').read_text());execution=json.loads((root/'execution.json').read_text())
    assert execution['complete'] and all(w['exit_code']==0 for w in execution['workers'])
    points=[];largest=0.
    for i,rows in enumerate(lock['assignments']):
        report=json.loads((root/f'worker_{i}/report.json').read_text());assert report['complete']
        assert report['lock_sha256']==sha256(root/'lock.json') and report['base_unchanged']==1613
        assert report['counts']==dict(diffusion=2*len(rows),pairformer=0)
        for point in report['points']:
            path=Path(point['path']);assert sha256(path)==point['sha256']
            a=torch.load(path,map_location='cpu',weights_only=False)['gradients'].double().numpy()
            norms=np.sqrt(np.einsum('ij,ij->i',a,a));cos=float(np.dot(a[0],a[1])/np.prod(norms))
            largest=max(largest,float(np.max(np.abs(norms/point['norms']-1))),abs(cos-point['cosine']))
            assert largest<1e-10
            points.append(dict(point,numpy_norms=norms.tolist(),numpy_cosine=cos))
    assert len(points)==32 and len({(p['group_id'],p['seed']) for p in points})==32
    groups=sorted({p['group_id'] for p in points});assert len(groups)==16
    medians=[]
    for t in range(2):
        medians.append(float(np.median([np.mean([p['numpy_norms'][t] for p in points if p['group_id']==g]) for g in groups])))
    assert min(medians)>0
    write_json(root/'calibration.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),
        points=points,median_protein_mean_norms=medians,weight_D=medians[0]/medians[1],
        numpy_max_relative_or_cosine_error=largest,initial_only=True,optimizer_updates=0,
        formula='median_protein(mean_noise(norm(g_D_T0.1))) / median_protein(mean_noise(norm(g_D_T1)))'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['prepare','worker','finish'],required=True);p.add_argument('--index',type=int);a=p.parse_args()
    torch.set_num_threads(1)
    if a.mode=='prepare':prepare_temperature_probe(a.root)
    elif a.mode=='worker':run_temperature_probe(a.root,a.index)
    else:finish_temperature_probe(a.root)
