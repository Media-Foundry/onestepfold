#!/usr/bin/env python3
"""Bounded fixed2048 full-input audit, followed conditionally by hard utility."""
import argparse
import gc
import hashlib
import json
import time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.models.soft_esm import AMINO_ACIDS, sequence_probabilities, soft_esm2
from fastglycan.models.soft_sequence_chart import SequenceChart, native_sequence_features, device_tree
from fastglycan.models.differentiable_mini import full_recycle_pairformer, diffusion_from_conditioning, prepare_atom_pairs
from fastglycan.folding_scale import load_folding_scale_terminal
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.position_utility import position_mutation_proposals, mutation_chemistry, audit_probability_pullback
from fastglycan.backbone_sequence_task import backbone_target_pairs, backbone_target_loss, backbone_candidate_accept
from fastglycan.composite_derivatives import without_checkpoint_wrappers, consistency
from fastglycan.vjp_comparison import vector_metrics


def pack_conditioning(point):
    shapes = [x.shape for x in point]; sizes = [x.numel() for x in point]
    return tuple(x.reshape(s) for x, s in zip(torch.cat([x.flatten() for x in point]).split(sizes), shapes))


def prepare_backbone_sequence_pilot(root):
    prior_path = root.parent/'noise_diversity_assessment_v1_20261001_retry1/original/lock.json'
    prior = rt.load_json(prior_path)
    bands = root/'code/docs/connection_reference_bands.json'
    expected_bands = [h for p,h in prior['hashes'].items() if p.endswith('/connection_reference_bands.json')]
    assert expected_bands and all(sha256(bands)==h for h in expected_bands), 'missing or changed calibration'
    for path,digest in prior['weights_sha256'].items(): assert sha256(Path(path))==digest,path
    excluded = {'2fip', '1bft', '1qsm', '5cpg', '8bzn', '9qr4'}
    eligible = [r for r in prior['rows'] if r['role']=='train' and 80<=len(r['sequence'])<=160 and r['pdb_id'].lower() not in excluded]
    rows = sorted(eligible, key=lambda r: hashlib.sha256(('backbone-sequence-v1:20261001:'+r['group_id']).encode()).hexdigest())[:4]
    assert len(rows)==4 and not (root/'lock.json').exists()
    source = Path(prior['source']); inputs = {str(prior_path): sha256(prior_path)}
    for row in rows:
        folder = source/'chemistry'/row['group_id']
        for p in [folder/'native.pt', folder/'mapping.npz', source/'data/examples'/row['group_id']/'gt.npz']:
            inputs[str(p)] = sha256(p)
            if str(p) in prior['input_hashes']: assert inputs[str(p)]==prior['input_hashes'][str(p)]
    cp = prior['checkpoints']['fixed']
    assert sha256(Path(cp['path']))==cp['sha256']=='3bee481ca3124b829eea476d1f2c9db18dd29965170524e4f4d5390dbb8cb509'
    write_json(root/'lock.json', dict(rows=rows, eligible=len(eligible), source=str(source), checkpoint=cp,
        checkpoint_lock=prior['checkpoint_training_locks']['fixed'], selected_names=prior['selected_names']['fixed'],
        weights_sha256=prior['weights_sha256'], input_hashes=inputs,
        code_hashes={str(p): sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']},
        alpha=.001, proposal_seed=211001, confirmation_seeds=[211013,211021],
        evaluation_seeds=[211001,211013,211021], direction_seed=212001, random_seed=213001,
        cycles=4, steps=1, workers=8, max_predictions=468, training=False))


def target_for_parent(lock, row):
    folder = Path(lock['source'])/'chemistry'/row['group_id']
    mapping = dict(np.load(folder/'mapping.npz'))
    original = dict(np.load(Path(lock['source'])/'data/examples'/row['group_id']/'gt.npz'))
    from onestepfold.data.gt_materializer import ATOM37_INDEX
    ca = mapping['atom_names']=='CA'; ids = mapping['residue_ids'][ca]-1
    assert np.array_equal(ids, np.arange(len(row['sequence'])))
    observed = mapping['mask'][ca].astype(bool)
    assert np.array_equal(observed, original['atom37_mask'][ids,ATOM37_INDEX['CA']] & original['residue_mask'][ids])
    xyz = mapping['coordinates'][ca]
    assert np.array_equal(xyz[observed], original['atom37_positions'][ids[observed],ATOM37_INDEX['CA']])
    return backbone_target_pairs(xyz, observed)


def run_backbone_sequence_pilot(root, mode, index):
    lock = rt.load_json(root/'lock.json'); torch.set_num_threads(1)
    for p,h in {**lock['code_hashes'],**lock['input_hashes']}.items(): assert sha256(Path(p))==h,p
    out = root/f'{mode}_{index}'; out.mkdir(exist_ok=False)
    started = time.monotonic(); report = dict(complete=False, stage='load', mode=mode, index=index, records=[], lock_sha256=sha256(root/'lock.json'))
    def save(): write_json(out/'report.json',report)
    save(); runner = rt.runner_setup(out/'work'); runner.configs.dtype='fp32'
    model = runner.model.eval().requires_grad_(False)
    cp = lock['checkpoint']; assert sha256(Path(cp['path']))==cp['sha256']
    state = torch.load(cp['path'],map_location='cpu',weights_only=False)
    load_folding_scale_terminal(model,state,arm='expanded',expected_names=lock['selected_names'],lock_sha256=lock['checkpoint_lock']); del state
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet = load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir)
    esm.eval().requires_grad_(False)
    calibration = rt.load_json(root/'code/docs/connection_reference_bands.json')
    report['load_seconds']=time.monotonic()-started
    def hard_features(sequence):
        native,atoms=native_sequence_features(sequence)
        f=model.relative_position_encoding.generate_relp(device_tree(native,'cuda'))
        tokens=alphabet.get_batch_converter()([('hard',sequence)])[2].cuda()
        f['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
        return prepare_atom_pairs(f),atoms
    def coordinates(f,atoms,seed):
        c=pack_conditioning(full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False))
        return diffusion_from_conditioning(model,f,identity_noise(atoms,seed,device='cuda'),c,steps=1)
    def measure(x,atoms,reference,sequence,pairs,distances):
        ca=torch.tensor(np.flatnonzero(atoms.atom_name=='CA'),device='cuda')
        return dict(task=float(backbone_target_loss(x,ca,pairs,distances).detach()),
            chemistry=mutation_chemistry(atoms,reference,sequence,x.detach().cpu().numpy(),calibration))
    if mode=='audit':
        row=lock['rows'][index]; seq=row['sequence']; pairs,distances=target_for_parent(lock,row)
        report['parent']=dict(pdb_id=row['pdb_id'],group_id=row['group_id'],length=len(seq));report['target_pairs']=len(pairs)
        setup=time.monotonic(); templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS}
        chart=SequenceChart(seq,model,esm,alphabet,templates)
        hard=sequence_probabilities(seq,device='cuda'); p0=(1-lock['alpha'])*hard+lock['alpha']/19*(1-hard); q0=p0.log()
        reference=chart.native['ref_pos'].cpu().numpy()
        def full(q): return coordinates(chart.features(q.softmax(-1),check_chart=False),chart.atoms,lock['proposal_seed'])
        def task(x): return backbone_target_loss(x,chart.ca_indices,pairs,distances)
        with torch.no_grad():
            native,atoms=hard_features(seq); soft=chart.features(hard)
            for key in ['esm_token_embedding','restype','profile','ref_pos','ref_charge','ref_mask','ref_element','ref_atom_name_chars']:
                assert torch.equal(native[key],soft[key]),key+' hard endpoint parity'
            hard_x=coordinates(native,atoms,lock['proposal_seed']); onehot_x=coordinates(soft,chart.atoms,lock['proposal_seed'])
            assert torch.equal(hard_x,onehot_x),'full hard endpoint parity'
            hard_measure=measure(hard_x,atoms,reference,seq,pairs,distances)
        del native,soft,onehot_x
        report.update(setup_seconds=time.monotonic()-setup, hard_parity_exact=True, hard=hard_measure, stage='native_reverse');save()
        counts=dict(pairformer=0,denoiser=0)
        hooks=[model.pairformer_stack.register_forward_hook(lambda *a:counts.__setitem__('pairformer',counts['pairformer']+1)),
               model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('denoiser',counts['denoiser']+1))]
        runs=[]; buffers=[]
        for repeat in range(2):
            gc.collect();torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();begin=time.monotonic()
            q=q0.detach().clone().requires_grad_(True); p=q.softmax(-1)
            counts.update(pairformer=0,denoiser=0)
            x=coordinates(chart.features(p),chart.atoms,lock['proposal_seed']);loss=task(x)
            forward_counts=dict(counts)
            gp,gq=torch.autograd.grad(loss,(p,q));torch.cuda.synchronize()
            runs.append(dict(seconds=time.monotonic()-begin,allocated_bytes=torch.cuda.max_memory_allocated(),reserved_bytes=torch.cuda.max_memory_reserved(),forward_calls=forward_counts,backward_recomputations={k:counts[k]-forward_counts[k] for k in counts}))
            assert forward_counts==dict(pairformer=4,denoiser=1)
            assert torch.isfinite(gp).all() and torch.isfinite(gq).all()
            buffers.append(dict(x=x.detach().cpu(),gp=gp.cpu(),gq=gq.cpu()))
            if repeat==0: chain=audit_probability_pullback(q,p,gp,gq)
            del q,p,x,loss,gp,gq
        for h in hooks:h.remove()
        repeat_exact={k:torch.equal(buffers[0][k],buffers[1][k]) for k in buffers[0]}
        assert all(repeat_exact.values()) and chain['local_softmax_vjp_exact']
        baseline=buffers[0]; del buffers
        near=measure(baseline['x'].cuda(),chart.atoms,reference,seq,pairs,distances)
        hg=hard_measure['chemistry'];ng=near['chemistry'];h=hg['legacy_geometry'];n=ng['legacy_geometry']
        nonregression=(n['severe_pairs']<=h['severe_pairs'] and ng['ca_wrong']<=hg['ca_wrong'] and ng['side_wrong']<=hg['side_wrong']
            and n['bond_rmse']<=h['bond_rmse']+.01 and n['peptide_mae']<=h['peptide_mae']+.01 and n['max_penetration']<=h['max_penetration']+.05)
        report.update(native_runs=runs,repeat_exact=repeat_exact,chain_audit=chain,near=near,near_nonregression=nonregression,stage='reference');save()
        gc.collect();torch.cuda.empty_cache()
        # Reference changes attention backend only; production remains native.
        def math_context(): return torch.nn.attention.sdpa_kernel([torch.nn.attention.SDPBackend.MATH])
        with math_context():
            qr=q0.detach().clone().requires_grad_(True);xr=full(qr);gr,=torch.autograd.grad(task(xr),qr)
        xr=xr.detach();gr=gr.detach();del qr
        report['reference_primal']=vector_metrics(baseline['x'].cuda(),xr)
        report['full_logits_vjp']=vector_metrics(baseline['gq'].cuda(),gr)
        directions=[];checks=[];gen=torch.Generator().manual_seed(lock['direction_seed']+index)
        for di in range(3):
            v=torch.randn(q0.shape,generator=gen);v=(v/v.norm()).cuda();directions.append(v.cpu())
            with without_checkpoint_wrappers(model),math_context():
                primal,tangent=torch.func.jvp(lambda q:task(full(q)),(q0,),(v,))
            native_projection=float((baseline['gq'].double()*v.cpu().double()).sum())
            reference_projection=float((gr.double()*v.double()).sum());jvp=float(tangent)
            native_check=consistency(jvp,native_projection);ref_check=consistency(jvp,reference_projection)
            informative=min(abs(jvp),abs(native_projection))>1e-6 and native_check['relative_error']<=.05
            checks.append(dict(direction=di,native=native_check,reference=ref_check,informative=informative,
                primal_delta=float(primal-task(xr)),direction_norm=float(v.norm())))
            report['directions']=checks;save();del primal,tangent
        metrics=report['full_logits_vjp']
        passed=(nonregression and report['reference_primal']['max_absolute_error']<=.001
            and metrics['relative_l2_error'] is not None and metrics['relative_l2_error']<=.01
            and all(c['native']['passed'] and c['reference']['passed'] for c in checks) and any(c['informative'] for c in checks))
        torch.save(dict(q=q0.cpu(),**baseline,hard_x=hard_x.cpu(),reference_x=xr.cpu(),reference_gq=gr.cpu(),directions=directions,pairs=pairs,distances=distances),out/'audit.pt')
        proposal=position_mutation_proposals(seq,baseline['gp'],seed=lock['random_seed']+index)
        proposal.update(parent_index=index,parent=seq,group_id=row['group_id'],pdb_id=row['pdb_id'])
        write_json(out/'candidates.json',proposal)
        report.update(gate_passed=passed,artifact_sha256=sha256(out/'audit.pt'),candidate_sha256=sha256(out/'candidates.json'),
            parameter_gradients_absent=not any(p.grad is not None for p in list(model.parameters())+list(esm.parameters())))
        assert report['parameter_gradients_absent']
    elif mode=='evaluate':
        manifest=rt.load_json(root/'candidates_lock.json');assert manifest['lock_sha256']==sha256(root/'lock.json')
        for path,digest in manifest['proposal_hashes'].items():assert sha256(Path(path))==digest
        for item in manifest['assignments'][index]:
            begin=time.monotonic();pi=item['parent_index'];si=item['sequence_index'];seq=item['sequence'];row=lock['rows'][pi]
            pairs,distances=target_for_parent(lock,row);values={};report['stage']=f'p{pi}_s{si}';save()
            with torch.no_grad():
                f,atoms=hard_features(seq);reference=f['ref_pos'].cpu().numpy()
                cond=pack_conditioning(full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False))
                for seed in lock['evaluation_seeds']:
                    x=diffusion_from_conditioning(model,f,identity_noise(atoms,seed,device='cuda'),cond,steps=1)
                    assert torch.isfinite(x).all()
                    value=measure(x,atoms,reference,seq,pairs,distances)
                    file=out/f'p{pi}_s{si}_n{seed}.npz'
                    np.savez_compressed(file,coordinates=x.cpu().numpy(),reference=reference,atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id,sequence=seq)
                    value.update(coordinate_file=file.name,coordinate_sha256=sha256(file));values[str(seed)]=value
                torch.save(dict(atoms=atoms,reference=reference),out/f'p{pi}_s{si}_topology.pt')
            report['records'].append(dict(**item,values=values,seconds=time.monotonic()-begin));save()
    report.update(complete=True,stage='complete',seconds=time.monotonic()-started,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved());save()


def score_backbone_sequence_pilot(root):
    lock=rt.load_json(root/'lock.json');manifest=rt.load_json(root/'candidates_lock.json');records={}
    for i in range(lock['workers']):
        r=rt.load_json(root/f'evaluate_{i}/report.json');assert r['complete']
        for row in r['records']: records[(row['parent_index'],row['sequence'])]=row
    assert len(records)*3==manifest['expected_outputs']
    summaries=[]
    for pi,proposal in enumerate(manifest['proposals']):
        parent=records[(pi,proposal['parent'])];arms={}
        for arm,options in proposal['arms'].items():
            candidates=[]
            for option in options:
                row=records[(pi,option['sequence'])];evaluations={}
                for seed in lock['evaluation_seeds']:
                    key=str(seed);v=row['values'][key];pv=parent['values'][key]
                    evaluations[key]=dict(task_delta=v['task']-pv['task'],**backbone_candidate_accept(v,pv))
                candidates.append(dict(**option,evaluations=evaluations,proposal_task=row['values'][str(lock['proposal_seed'])]['task']))
            allowed=[c for c in candidates if c['evaluations'][str(lock['proposal_seed'])]['accepted']]
            selected=min(allowed,key=lambda c:(c['proposal_task'],c['sequence'])) if allowed else None
            confirmed=bool(selected and all(selected['evaluations'][str(s)]['accepted'] for s in lock['confirmation_seeds']))
            arms[arm]=dict(candidates=candidates,selected_sequence=selected['sequence'] if selected else None,selected_confirmed=confirmed,
                all_candidate_confirmation_success=sum(all(c['evaluations'][str(s)]['accepted'] for s in lock['confirmation_seeds']) for c in candidates),
                mean_confirmation_task_delta=float(np.mean([c['evaluations'][str(s)]['task_delta'] for c in candidates for s in lock['confirmation_seeds']])))
        summaries.append(dict(parent_index=pi,pdb_id=proposal['pdb_id'],arms=arms))
    write_json(root/'report.json',dict(complete=True,parents=summaries,predictions=manifest['expected_outputs'],
        selected_confirmation_success={a:sum(r['arms'][a]['selected_confirmed'] for r in summaries) for a in ['gradient','random']},
        scope='four development proteins; target backbone, not mutant GT or binding',deployment_accepted=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','audit','evaluate','score'],required=True);p.add_argument('--index',type=int,default=0);a=p.parse_args()
    if a.mode=='prepare':prepare_backbone_sequence_pilot(a.root)
    elif a.mode=='score':score_backbone_sequence_pilot(a.root)
    else:run_backbone_sequence_pilot(a.root,a.mode,a.index)
