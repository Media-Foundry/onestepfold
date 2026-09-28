#!/usr/bin/env python3
"""One locked near-hard proposal batch; independent native hard reconstruction."""
import argparse,time
from pathlib import Path
from dataclasses import asdict
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.models.soft_esm import AMINO_ACIDS,sequence_probabilities,soft_esm2
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import full_recycle_pairformer,diffusion_from_conditioning,prepare_atom_pairs
from fastglycan.sequence_gate_metrics import contact_objective
from fastglycan.hybrid_geometry import GeometryTopology,GeometryRules
from fastglycan.hybrid_proposals import mutation_proposals,identity_noise


def packed(point):
    shapes=[x.shape for x in point];sizes=[x.numel() for x in point]
    return tuple(x.reshape(s) for x,s in zip(torch.cat([x.flatten() for x in point]).split(sizes),shapes))


def objective(x,topology,ca):
    task,task_parts=contact_objective(x,ca);terms,geometry=topology.terms(x)
    total=task+terms['bond']+2*terms['peptide']+terms['clash']+.2*terms['chirality']
    return total,dict(task=float(task.detach()),total=float(total.detach()),task_components=task_parts,
                     geometry_terms={k:float(v.detach()) for k,v in terms.items()},geometry=geometry)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['propose','evaluate'],required=True);p.add_argument('--worker',type=int,default=0);a=p.parse_args();root=a.root.resolve();lock=rt.load_json(root/'lock.json')
    assert lock['geometry_rules']==asdict(GeometryRules())
    for file,digest in lock['source_sha256'].items():assert sha256(root/'code'/file)==digest,file
    out=root/('proposal' if a.mode=='propose' else f'worker{a.worker}');out.mkdir(exist_ok=False);start=time.monotonic()
    r=dict(complete=False,stage='load',lock_sha256=sha256(root/'lock.json'),mode=a.mode,worker=a.worker,results=[])
    def save():write_json(out/'report.json',r)
    save();runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
    seq=lock['sequence']
    if a.mode=='propose':
        f=Path(lock['logits_source']);assert sha256(f)==lock['logits_source_sha256'];archive=torch.load(f,map_location='cpu',weights_only=False)
        templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates);topology=GeometryTopology(chart.atoms,chart.native['ref_pos'].cpu().numpy())
        q=archive['q'].cuda().detach().requires_grad_(True);p0=q.softmax(-1);anchor=p0.detach();r['stage']='gradient';save();ts=time.monotonic()
        features=chart.features(p0);cond=packed(full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False))
        x=diffusion_from_conditioning(model,features,identity_noise(chart.atoms,211,device='cuda'),cond,steps=1)
        total,parts=objective(x,topology,chart.ca_indices);kl=.01*(p0*(p0.log()-anchor.log())).sum(-1).mean();loss=total+kl
        gp,gq=torch.autograd.grad(loss,(p0,q));expected=p0*(gp-(gp*p0).sum(-1,keepdim=True))
        torch.save(dict(q=q.detach().cpu(),p=p0.detach().cpu(),gp=gp.cpu(),gq=gq.cpu(),expected=expected.detach().cpu(),coordinates=x.detach().cpu(),objective=parts,gradient_seconds=time.monotonic()-ts),out/'chain_probe.pt')
        assert torch.isfinite(gp).all() and torch.isfinite(gq).all();assert torch.allclose(gq,expected,rtol=1e-5,atol=1e-8)
        archived=np.load(lock['coordinate_source'])['coordinates'];assert sha256(Path(lock['coordinate_source']))==lock['coordinate_source_sha256']
        assert torch.equal(x.detach().cpu(),torch.from_numpy(archived)),'near-hard forward archive drift'
        options=mutation_proposals(seq,gp,budget=16,seed=lock['random_proposal_seed'])
        for arm in options:
            for o in options[arm]:o['local_substitution_score']=o.pop('predicted_delta')
        unique=[seq]+list(dict.fromkeys(o['sequence'] for arm in options.values() for o in arm))
        manifest=dict(parent=seq,arms=options,sequences=unique,evaluation_seeds=lock['evaluation_seeds'],confirmation_seeds=lock['confirmation_seeds'],random_proposal_seed=lock['random_proposal_seed'],lock_sha256=sha256(root/'lock.json'))
        torch.save(dict(q=q.detach().cpu(),p=p0.detach().cpu(),gp=gp.cpu(),gq=gq.cpu(),coordinates=x.detach().cpu()),out/'gradient.pt')
        write_json(root/'candidates.json',manifest)
        r.update(gradient_seconds=time.monotonic()-ts,near_hard_archive_exact=True,chain_max_abs=float((gq-expected).abs().max()),gp_norm=float(gp.norm()),gq_norm=float(gq.norm()),objective=parts,kl=float(kl),candidate_sha256=sha256(root/'candidates.json'),gradient_sha256=sha256(out/'gradient.pt'),unique_sequences=len(unique))
    else:
        manifest=rt.load_json(root/'candidates.json');assert rt.load_json(root/'proposal/report.json')['candidate_sha256']==sha256(root/'candidates.json');r['candidate_sha256']=sha256(root/'candidates.json')
        for index,sequence in enumerate(manifest['sequences']):
            if index%lock['workers']!=a.worker:continue
            ts=time.monotonic();r['stage']=f'sequence{index}';save();native,atoms=native_sequence_features(sequence);features=model.relative_position_encoding.generate_relp(device_tree(native,'cuda'))
            with torch.no_grad():
                tokens=alphabet.get_batch_converter()([('candidate',sequence)])[2].cuda()
                features['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
                if index==0:
                    soft=soft_esm2(esm,alphabet,sequence_probabilities(sequence,device='cuda'))
                    r['parent_esm_parity_max_abs']=float((soft-features['esm_token_embedding']).abs().max());assert torch.equal(soft,features['esm_token_embedding']),'hard ESM parity drift'
                features=prepare_atom_pairs(features);topology=GeometryTopology(atoms,features['ref_pos'].cpu().numpy());ca=torch.tensor(np.flatnonzero(atoms.atom_name=='CA'),device='cuda')
                conditioning=packed(full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False));values={}
                topology_file=f'sequence{index}_topology.pt';torch.save(dict(topology=topology,ca=ca.cpu(),sequence=sequence,atom_names=np.asarray(atoms.atom_name),residue_ids=np.asarray(atoms.res_id),chain_ids=np.asarray(atoms.chain_id)),out/topology_file)
                for seed in lock['evaluation_seeds']:
                    x=diffusion_from_conditioning(model,features,identity_noise(atoms,seed,device='cuda'),conditioning,steps=1)
                    _,v=objective(x,topology,ca);filename=f'sequence{index}_noise{seed}.npz';np.savez_compressed(out/filename,coordinates=x.cpu().numpy(),sequence=sequence,atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id)
                    v.update(coordinate_file=filename,coordinate_sha256=sha256(out/filename));values[str(seed)]=v
            r['results'].append(dict(index=index,sequence=sequence,values=values,seconds=time.monotonic()-ts,topology_file=topology_file,topology_sha256=sha256(out/topology_file)));save()
    r.update(complete=True,stage='complete',elapsed_seconds=time.monotonic()-start,peak_memory_gib=torch.cuda.max_memory_allocated()/2**30);save()
if __name__=='__main__':main()
