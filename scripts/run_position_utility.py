#!/usr/bin/env python3
"""Frozen learned S1: one local position proposal, native hard reconstruction."""
import argparse
import json
import time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.models.soft_esm import AMINO_ACIDS,sequence_probabilities,soft_esm2
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import full_recycle_pairformer,diffusion_from_conditioning,prepare_atom_pairs
from fastglycan.models.diffusion_scope import load_dense_diffusion_checkpoint
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.position_utility import position_mutation_proposals,mutation_chemistry,audit_probability_pullback
from run_hard_mutation_utility import packed,objective


def run_position_utility(root,mode,index):
    lock=json.loads((root/'lock.json').read_text());torch.set_num_threads(1)
    for path,digest in {**lock['hashes'],**lock['input_hashes']}.items():assert sha256(Path(path))==digest,path
    out=root/(f'proposal_{index}' if mode=='propose' else f'worker_{index}');out.mkdir(exist_ok=False)
    started=time.monotonic();report=dict(complete=False,mode=mode,worker=index,stage='load',lock_sha256=sha256(root/'lock.json'),records=[])
    write_json(out/'report.json',report)
    runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    cp=lock['checkpoint'];assert sha256(Path(cp['path']))==cp['sha256']
    state=torch.load(cp['path'],map_location='cpu',weights_only=False)
    load_dense_diffusion_checkpoint(model,state,arm='diffusion_dense',expected_names=lock['selected_names'])
    del state
    assert not any(p.requires_grad for p in model.parameters())
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
    calibration=json.loads((root/'code/docs/connection_reference_bands.json').read_text())
    if mode=='propose':
        row=lock['rows'][index];seq=row['sequence'];ts=time.monotonic()
        templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS}
        chart=SequenceChart(seq,model,esm,alphabet,templates);topology=GeometryTopology(chart.atoms,chart.native['ref_pos'].cpu().numpy())
        hard=sequence_probabilities(seq,device='cuda');p_initial=(1-lock['alpha'])*hard+lock['alpha']/19*(1-hard)
        q=p_initial.log().detach().requires_grad_(True);p=q.softmax(-1)
        report['stage']='gradient';write_json(out/'report.json',report)
        f=chart.features(p);cond=packed(full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False))
        x=diffusion_from_conditioning(model,f,identity_noise(chart.atoms,lock['proposal_seed'],device='cuda'),cond,steps=1)
        loss,parts=objective(x,topology,chart.ca_indices)
        gp,gq=torch.autograd.grad(loss,(p,q));expected=p*(gp-(gp*p).sum(-1,keepdim=True))
        assert torch.isfinite(gp).all() and torch.isfinite(gq).all() and float(gp.norm())>0
        chain_audit=audit_probability_pullback(q,p,gp,gq)
        torch.save(dict(q=q.detach().cpu(),p=p.detach().cpu(),gp=gp.cpu(),gq=gq.cpu(),coordinates=x.detach().cpu()),out/'gradient.pt')
        write_json(out/'chain_audit.json',chain_audit)
        assert chain_audit['local_softmax_vjp_exact'],'local probability/logit VJP path mismatch'
        assert not any(t.grad is not None for t in model.parameters())
        proposal=position_mutation_proposals(seq,gp,seed=lock['random_seed_base']+index)
        proposal.update(parent_index=index,group_id=row['group_id'],pdb_id=row['pdb_id'],parent=seq,lock_sha256=sha256(root/'lock.json'))
        torch.save(dict(q=q.detach().cpu(),p=p.detach().cpu(),gp=gp.cpu(),gq=gq.cpu(),coordinates=x.detach().cpu()),out/'gradient.pt')
        write_json(out/'candidates.json',proposal)
        report.update(proposal_sha256=sha256(out/'candidates.json'),gradient_sha256=sha256(out/'gradient.pt'),
                      chain_audit=chain_audit,gp_norm=float(gp.norm()),gq_norm=float(gq.norm()),chain_max_abs=float((gq-expected).abs().max()),
                      objective=parts,positions=proposal['positions'],unique_sequences=len(proposal['sequences']),
                      gradient_seconds=time.monotonic()-ts,gradient_nfe=1)
    else:
        manifest=json.loads((root/'candidates_lock.json').read_text());assert manifest['lock_sha256']==sha256(root/'lock.json')
        for p,d in manifest['proposal_hashes'].items():assert sha256(Path(p))==d
        report['candidate_lock_sha256']=sha256(root/'candidates_lock.json')
        for task in manifest['assignments'][index]:
            ts=time.monotonic();pi=task['parent_index'];si=task['sequence_index'];seq=task['sequence'];report['stage']=f'parent{pi}_sequence{si}';write_json(out/'report.json',report)
            native,atoms=native_sequence_features(seq);features=model.relative_position_encoding.generate_relp(device_tree(native,'cuda'))
            with torch.no_grad():
                tokens=alphabet.get_batch_converter()([('candidate',seq)])[2].cuda()
                e=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
                if si==0:
                    soft=soft_esm2(esm,alphabet,sequence_probabilities(seq,device='cuda'))
                    assert torch.equal(soft,e),'one-hot ESM parity failed'
                features['esm_token_embedding']=e;features=prepare_atom_pairs(features)
                topology=GeometryTopology(atoms,features['ref_pos'].cpu().numpy());ca=torch.tensor(np.flatnonzero(atoms.atom_name=='CA'),device='cuda')
                cond=packed(full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False));values={}
                topology_file=f'p{pi}_s{si}_topology.pt'
                torch.save(dict(atoms=atoms,reference=features['ref_pos'].cpu(),sequence=seq,ca=ca.cpu()),out/topology_file)
                for seed in lock['evaluation_seeds']:
                    x=diffusion_from_conditioning(model,features,identity_noise(atoms,seed,device='cuda'),cond,steps=1)
                    _,v=objective(x,topology,ca);coords=x.cpu().numpy();filename=f'p{pi}_s{si}_noise{seed}.npz'
                    np.savez_compressed(out/filename,coordinates=coords,sequence=seq,atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id)
                    v.update(chemistry=mutation_chemistry(atoms,features['ref_pos'].cpu().numpy(),seq,coords,calibration),
                        coordinate_file=filename,coordinate_sha256=sha256(out/filename));values[str(seed)]=v
            report['records'].append(dict(**task,values=values,seconds=time.monotonic()-ts,topology_file=topology_file,topology_sha256=sha256(out/topology_file),parent_esm_parity=si==0))
            write_json(out/'report.json',report)
    report.update(complete=True,stage='complete',seconds=time.monotonic()-started,peak_memory_bytes=torch.cuda.max_memory_allocated())
    write_json(out/'report.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['propose','evaluate'],required=True);p.add_argument('--worker',type=int,required=True);a=p.parse_args();run_position_utility(a.root.resolve(),a.mode,a.worker)
