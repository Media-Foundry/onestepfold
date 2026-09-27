#!/usr/bin/env python3
"""Four gate experiment, with explicit rejection of unvalidated global smoothness."""
import argparse, copy, json, time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import write_json, sha256
from fastglycan.models.soft_esm import AMINO_ACIDS, soft_esm2, sequence_probabilities, hard_sequence
from fastglycan.models.soft_sequence_chart import SequenceChart, native_sequence_features
from fastglycan.models.differentiable_mini import fixed_graph_coordinates
from fastglycan.sequence_gate_metrics import directional_finite_differences, contact_objective
from run_c4_s1_precision import ReplayNoise


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--group');p.add_argument('--opt-s',type=int,choices=(1,2),required=True)
    p.add_argument('--updates',type=int,default=50);p.add_argument('--directions',type=int,default=3)
    a=p.parse_args();root=a.root.resolve();out=a.out.resolve();out.mkdir(exist_ok=False)
    info=rt.load_json(root/'packets.json');manifest=rt.load_json(root/'manifest.json')
    g=a.group or min(info,key=lambda g:(info[g]['length'],g));seq=manifest[g]['sequence']
    report=dict(group=g,sequence=seq,length=len(seq),opt_s=a.opt_s,complete=False,
                contract='piecewise native-inventory relaxation; not globally smooth',
                objective='monomer nonlocal contacts with CA chain/clash penalties; NOT binding affinity',
                stage='load',gates={},trajectory=[])
    def save(): write_json(out/'report.json',report)
    save();runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32'
    model=runner.model.eval().requires_grad_(False)
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir)
    esm.eval().requires_grad_(False)
    report['environment']=dict(torch=torch.__version__,hip=torch.version.hip,gpu=torch.cuda.get_device_name(),
        checkpoint_sha256=sha256(Path(runner.configs.load_checkpoint_dir)/'protenix_mini_esm_v0.5.0.pt'),
        source_sha256={str(f.relative_to(Path(__file__).resolve().parents[1])):sha256(f)
                       for f in [Path(__file__).resolve(),*Path(__file__).resolve().parents[1].glob('src/fastglycan/models/soft_*.py')]})
    report['stage']='templates';save()
    templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS}
    base_chart=SequenceChart(seq,model,esm,alphabet,templates)
    chart=base_chart
    def select_chart(probability):
        nonlocal chart
        sequence=hard_sequence(probability)
        if chart.sequence!=sequence:
            chart=SequenceChart(sequence,model,esm,alphabet,templates)
        return chart
    def coordinates(probability,steps,seed=103):
        c=select_chart(probability)
        x=fixed_graph_coordinates(model,c.features(probability),c.initial_noise(seed),steps=steps,stable_euler=True)
        return x,c
    def objective(logits,steps):
        x,c=coordinates(logits.softmax(-1),steps)
        return contact_objective(x,c.ca_indices)[0]
    def native_replay(sequence,seed=103):
        c=SequenceChart(sequence,model,esm,alphabet,templates)
        onehot=sequence_probabilities(sequence,device='cuda')
        with torch.no_grad():
            soft_features=c.features(onehot)
            _,_,tokens=alphabet.get_batch_converter()([('hard',sequence)])
            native_esm=esm(tokens.cuda(),repr_layers=[esm.num_layers])['representations'][esm.num_layers][0,1:-1]
            embedding_error=float((soft_features['esm_token_embedding']-native_esm).abs().max())
            feature_error=max(float((soft_features[k]-c.native[k]).abs().max()) for k in ('restype','profile','ref_pos','ref_mask','ref_element','ref_charge','ref_atom_name_chars'))
            native_features=copy.deepcopy(c.native);native_features['esm_token_embedding']=native_esm
            initial=c.initial_noise(seed);centered=initial-initial.mean(-2,keepdim=True)
            arrays=dict(initial_coordinate=initial.cpu().numpy(),first_noisy=centered.cpu().numpy())
            with ReplayNoise(runner,g,seed,arrays):
                prediction,ref,_=rt.predict(runner,dict(input_feature_dict=native_features),'c4_s1',seed,None)
            del prediction
            x=fixed_graph_coordinates(model,soft_features,initial,stable_euler=True)
        return dict(embedding_max_abs=embedding_error,feature_max_abs=feature_error,
                    coordinate_max_abs=float((x-torch.as_tensor(ref,device='cuda')).abs().max()),
                    sequence=sequence,atom_count=len(c.atoms))
    report['stage']='gate1';save();replay=native_replay(seq)
    replay['passed']=replay['embedding_max_abs']<=1e-5 and replay['feature_max_abs']<=1e-5 and replay['coordinate_max_abs']<=.002
    report['gates']['1_hard_replay']=replay;save()
    if not replay['passed']:raise RuntimeError('native hard-input replay failed')
    onehot=sequence_probabilities(seq,device='cuda');initial_logits=onehot*4
    report['stage']='gate2';save();gradients={}
    for steps in (1,2):
        gradient,numerics=directional_finite_differences(lambda q:objective(q,steps),initial_logits,directions=a.directions)
        gradients[steps]=gradient.detach()
        report['gates'][f'2_s{steps}_local_derivative']=numerics;save()
    report['gradient_cosine']=float(torch.nn.functional.cosine_similarity(gradients[1].flatten(),gradients[2].flatten(),dim=0))
    report['stage']='gate3';save()
    q=initial_logits.detach().clone().requires_grad_(True);optimizer=torch.optim.Adam([q],lr=.2)
    previous_hard=seq
    for update in range(a.updates+1):
        optimizer.zero_grad(set_to_none=True)
        previous_chart=chart
        x,c=coordinates(q.softmax(-1),a.opt_s)
        loss,metrics=contact_objective(x,c.ca_indices)
        current=hard_sequence(q.softmax(-1))
        row=dict(update=update,loss=float(loss.detach()),**metrics,
                 sequence=current,hard_mutations=sum(x!=y for x,y in zip(seq,current)),
                 topology_changed=current!=previous_hard)
        if current!=previous_hard:
            with torch.no_grad():
                old_x=fixed_graph_coordinates(model,previous_chart.features(q.softmax(-1),check_chart=False),
                    previous_chart.initial_noise(103),steps=a.opt_s,stable_euler=True)
                old_ca=old_x[0,previous_chart.ca_indices].double()
                new_ca=x.detach()[0,c.ca_indices].double()
                old_ca=old_ca-old_ca.mean(0);new_ca=new_ca-new_ca.mean(0)
                u,_,vh=torch.linalg.svd(old_ca.T@new_ca)
                correction=torch.eye(3,device=old_ca.device,dtype=old_ca.dtype)
                correction[-1,-1]=torch.linalg.det(u@vh)
                aligned=old_ca@(u@correction@vh)
                row['chart_jump_rmsd']=float((aligned-new_ca).square().sum(-1).mean().sqrt())
                row['chart_loss_jump']=float(loss.detach()-contact_objective(old_x,previous_chart.ca_indices)[0])
                row['atom_counts']=[len(previous_chart.atoms),len(c.atoms)]
        # Cross-evaluate the same logits under both S at endpoints and every10steps.
        if update%10==0 or update==a.updates:
            with torch.no_grad(): row['cross_losses']={str(s):float(objective(q,s)) for s in (1,2)}
        report['trajectory'].append(row);save();print('update',update,row['loss'],flush=True)
        previous_hard=current
        if update==a.updates:break
        loss.backward()
        if not torch.isfinite(q.grad).all():raise RuntimeError('nonfinite logit gradient')
        torch.nn.utils.clip_grad_norm_([q],1.)
        optimizer.step()
        del x,loss
    report['gates']['3_optimization']=dict(soft_loss_decreased=report['trajectory'][-1]['loss']<report['trajectory'][0]['loss'],
        topology_changes=sum(r['topology_changed'] for r in report['trajectory']),updates=a.updates)
    report['stage']='gate4';save();final_sequence=hard_sequence(q.softmax(-1));hard_replay=native_replay(final_sequence)
    report['gates']['4_hard_rebuild_replay']=hard_replay
    robustness=[]
    for seed in (103,107):
        for label,sequence in [('initial',seq),('optimized',final_sequence)]:
            probability=sequence_probabilities(sequence,device='cuda')
            for steps in (1,2):
                with torch.no_grad():
                    x,c=coordinates(probability,steps,seed)
                    value,metrics=contact_objective(x,c.ca_indices)
                robustness.append(dict(seed=seed,label=label,steps=steps,loss=float(value),**metrics))
                np.savez_compressed(out/f'{label}_seed{seed}_s{steps}.npz',coordinates=x.cpu().numpy(),atom_names=c.atoms.atom_name,residue_ids=c.atoms.res_id,sequence=sequence)
    report['gates']['4_independent_noise']=robustness
    report['final_sequence']=final_sequence
    report['complete']=True;report['stage']='complete'
    # Completing an experiment is distinct from validating a design oracle.
    report['deployment_accepted']=False
    report['remaining_gate']='global chart-boundary continuity, broader targets and actual interface objective unvalidated'
    report['peak_memory_gib']=torch.cuda.max_memory_allocated()/2**30
    save();torch.save(dict(initial_logits=initial_logits.cpu(),final_logits=q.detach().cpu()),out/'logits.pt')

if __name__=='__main__':main()
