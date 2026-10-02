"""Last bounded linear diagnostic: complete fixed-WT-chart JVP plus residual PCA."""
import argparse,gc,gzip,json,shutil,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features,device_tree
from fastglycan.models.soft_esm import AMINO_ACIDS,sequence_probabilities
from fastglycan.models.differentiable_mini import full_recycle_pairformer,prepare_atom_pairs,diffusion_from_conditioning
from fastglycan.composite_derivatives import without_checkpoint_wrappers
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.conditioning_swaps import DecoderFeatureTrace
from fastglycan.functional_response_rank import pack_conditioning
from fastglycan.global_response_rank import GLOBAL_RANKS
from fastglycan.jacobian_residual_rank import JacobianResidualBasis,hard_replacement_direction,checkpointed_reverse,archived_reference_coordinates
import run_global_response_rank as scoring
VARIANTS=('raw','balanced')
ARMS=('exact','baseline','tangent_only')+tuple(f'{v}_k{k}' for v in VARIANTS for k in GLOBAL_RANKS)


def prepare_jacobian_residual(root):
    prior=root.parent/'global_response_rank_v1_20261002';old=rt.load_json(prior/'lock.json');assert rt.load_json(prior/'controller_execution.json')['complete'];assert not (root/'lock.json').exists()
    for name in ['jacobian_residual_preflight_20261002','jacobian_residual_long_checkpoint_preflight_20261002']:
        assert rt.load_json(root.parent/name/'report.json')['complete']
    for item in old['conditioning_manifest']:assert sha256(Path(old['states'])/item['path'])==item['sha256']
    files=[dict(path=str(p.relative_to(prior)),sha256=sha256(p)) for pattern in ['worker_*/*_inventory.npz','worker_*/*_coordinates.npz'] for p in prior.glob(pattern)];assert len(files)==1920
    lock=dict(old);lock.update(schema='jacobian_residual_rank_v1',control_root=str(prior),prior_lock_sha256=sha256(prior/'lock.json'),input_files=files,
        arms=ARMS,variants=VARIANTS,expected_nfe=41820,expected_jvp=950,expected_c4=970,expected_recycle=3880,
        scope='probability-space JVP at exactly hard WT on fixed WT atom chart; full ERC+ESM+C4; residual includes graph mismatch',
        code_hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']},
        duality_seed=228101,duality_rtol=.005,duality_atol=1e-6,training=False)
    write_json(root/'lock.json',lock)


def run_jacobian_residual(root,index):
    lock=rt.load_json(root/'lock.json');prior=Path(lock['control_root']);states=Path(lock['states']);torch.set_num_threads(1);start=time.monotonic()
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h,p
    out=root/f'worker_{index}';out.mkdir(exist_ok=False);report=dict(complete=False,worker=index,parents=[],stage='load',lock_sha256=sha256(root/'lock.json'))
    def save():write_json(out/'report.json',report)
    save();runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    for p,h in lock['weights_sha256'].items():assert sha256(Path(p))==h,p
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
    report['runtime']=dict(torch=torch.__version__,hip=torch.version.hip,device=torch.cuda.get_device_name(0))
    counts=dict(recycle=0,nfe=0,hard_rebuild=0,exact_replay=0,baseline_replay=0,jvp=0,vjp_forward=0,wt_forward=0,deduplicated_calls=0);reads=set()
    hooks=[model.pairformer_stack.register_forward_hook(lambda *a:counts.__setitem__('recycle',counts['recycle']+1)),model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('nfe',counts['nfe']+1))]
    hashes={f['path']:f['sha256'] for f in lock['conditioning_manifest']+lock['input_files']}
    def load_state(label,seq):
        p=states/f'worker_{index}/{label}_conditioning.pt';assert sha256(p)==hashes[str(p.relative_to(states))];packet=torch.load(p,map_location='cpu',weights_only=False);assert packet['sequence']==seq
        return tuple(t.cuda() for t in packet['conditioning'])
    def chemical_input(label,seq):
        invpath=prior/f'worker_{index}/{label}_inventory.npz';xyzpath=prior/f'worker_{index}/{label}_coordinates.npz'
        for p in [invpath,xyzpath]:assert sha256(p)==hashes[str(p.relative_to(prior))]
        inv=dict(np.load(invpath));native,atoms=native_sequence_features(seq)
        for key,values in [('atom_names',atoms.atom_name),('residue_ids',atoms.res_id),('chain_ids',atoms.chain_id),('bonds',atoms.bonds.as_array()),('reference',native['ref_pos'].numpy())]:assert np.array_equal(inv[key],values),key
        shutil.copy2(invpath,out/f'{label}_inventory.npz');counts['hard_rebuild']+=1
        return DecoderFeatureTrace(prepare_atom_pairs(model.relative_position_encoding.generate_relp(device_tree(native,'cuda')))),atoms,archived_reference_coordinates(np.load(xyzpath)['coordinates'],is_wt=label.endswith('_wt'))
    def decode(f,atoms,c):
        with torch.no_grad():result=np.stack([diffusion_from_conditioning(model,f,identity_noise(atoms,seed,device='cuda'),pack_conditioning(c),steps=1).squeeze(0).cpu().numpy() for seed in lock['seeds']])
        reads.update(f.reads);assert np.isfinite(result).all();return result
    with without_checkpoint_wrappers(model):
        for pi in lock['assignments'][index]:
            row=lock['rows'][pi];seq=row['sequence'];wt=load_state(f'p{pi}_wt',seq)
            templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates);p0=sequence_probabilities(seq,device='cuda')
            def forward(p):return full_recycle_pairformer(model,chart.features(p,check_chart=False),N_cycle=4,inplace_safe=False,mc_dropout=False)[1:]
            with torch.no_grad():base=forward(p0)
            counts['wt_forward']+=1;assert all(torch.equal(x,y) for x,y in zip(base,wt[1:])),'WT chart parity'
            wf,wa,wold=chemical_input(f'p{pi}_wt',seq);wxyz=decode(wf,wa,wt);assert np.array_equal(wxyz,wold[0]) and np.array_equal(wxyz,wold[1]);counts['exact_replay']+=1;counts['baseline_replay']+=1
            np.savez_compressed(out/f'p{pi}_wt_coordinates.npz',coordinates=wxyz,seeds=lock['seeds']);sites=[];duality=[]
            for si,pos in enumerate(row['positions']):
                ids=[i for i,a in enumerate(AMINO_ACIDS) if a!=seq[pos]];target=[];tangents=[];jvp_records=[]
                for ai in ids:
                    aa=AMINO_ACIDS[ai];label=f'p{pi}_s{pos+1}_{aa}';report.update(stage='jvp',active=label,counts=dict(counts));save();d=hard_replacement_direction(p0,pos,ai);torch.cuda.synchronize();t=time.monotonic()
                    with torch.no_grad():primal,tangent=torch.func.jvp(forward,(p0,),(d,))
                    torch.cuda.synchronize();seconds=time.monotonic()-t;counts['jvp']+=1
                    assert all(torch.equal(x,y) for x,y in zip(primal,base)),'JVP primal WT mismatch';assert all(torch.isfinite(x).all() for x in tangent)
                    tangent=tuple(x.detach() for x in tangent);tangents.append(tangent);jvp_records.append(dict(aa=aa,seconds=seconds,norms=[float(x.double().norm()) for x in tangent],primal_exact=True))
                    if si==0 and ai==ids[0]:
                        with checkpointed_reverse(model):
                            q=p0.detach().requires_grad_();y=forward(q);assert all(torch.equal(a,b) for a,b in zip(y,base)), 'checkpointed primal';counts['vjp_forward']+=1;gen=torch.Generator(device='cuda').manual_seed(lock['duality_seed']+pi)
                            for probe in range(2):
                                w=[torch.randn(x.shape,device='cuda',generator=gen)/x.numel()**.5 for x in y];loss=sum((x.double()*v.double()).sum() for x,v in zip(y,w));g,=torch.autograd.grad(loss,q,retain_graph=probe==0)
                                a=float((g.double()*d.double()).sum());b=float(sum((x.double()*v.double()).sum() for x,v in zip(tangent,w)));error=abs(a-b);passed=error<=lock['duality_atol']+lock['duality_rtol']*max(abs(a),abs(b))
                                duality.append(dict(position=pos,aa=aa,probe=probe,vjp=a,jvp=b,relative_error=error/max(abs(a),abs(b),1e-30),passed=passed));assert passed,'forward/reverse mismatch'
                        del q,y,loss,g,w;gc.collect();torch.cuda.empty_cache()
                    target.append(load_state(label,seq[:pos]+aa+seq[pos+1:]))
                ts,tz=(torch.stack([c[j] for c in tangents]) for j in range(2));hs,hz=(torch.stack([c[j] for c in target]) for j in [1,2]);basis=JacobianResidualBasis(wt[1],wt[2],hs,hz,ts,tz)
                path=out/f'p{pi}_s{pos+1}_tangents.pt';torch.save(dict(s=ts.cpu(),z=tz.cpu(),nonwt_indices=ids,probability_direction='e_a-e_WT',fixed_graph_sequence=seq),path)
                site=dict(position=pos,wt_index=AMINO_ACIDS.index(seq[pos]),nonwt_indices=ids,evidence=basis.evidence(),jvp_records=jvp_records,tangent_file=path.name,tangent_sha256=sha256(path),mutants=[])
                for mi,ai in enumerate(ids):
                    aa=AMINO_ACIDS[ai];label=f'p{pi}_s{pos+1}_{aa}';report.update(stage='decode',active=label,counts=dict(counts));save();f,atoms,old=chemical_input(label,seq[:pos]+aa+seq[pos+1:]);c=target[mi]
                    exact=decode(f,atoms,c);baseline=decode(f,atoms,(wt[0],c[1],c[2]));assert np.array_equal(exact,old[0]) and np.array_equal(baseline,old[1]);counts['exact_replay']+=1;counts['baseline_replay']+=1
                    outputs=[exact,baseline,decode(f,atoms,(wt[0],*basis.tangent_only(mi)))];full=[];zero=None
                    for variant in VARIANTS:
                        for k in GLOBAL_RANKS:
                            s,z=basis.reconstruct(mi,variant,k)
                            if k==0 and variant=='balanced':
                                assert all(torch.equal(x,y) for x,y in zip((s,z),zero[0]));xyz=zero[1];counts['deduplicated_calls']+=2
                            else:xyz=decode(f,atoms,(wt[0],s,z))
                            if k==0 and variant=='raw':zero=((s,z),xyz)
                            if k==18:
                                ie=max(float((s-c[1]).abs().max()),float((z-c[2]).abs().max()));ce=float(np.max(np.abs(xyz-baseline)));assert ie<=lock['full_rank_input_tolerance'] and ce<=lock['full_rank_coordinate_tolerance'];full.append(dict(variant=variant,input_max_error=ie,coordinate_max_error=ce))
                            outputs.append(xyz)
                    path=out/f'{label}_coordinates.npz';np.savez_compressed(path,coordinates=np.stack(outputs),arms=ARMS,seeds=lock['seeds']);site['mutants'].append(dict(aa=aa,label=label,coordinate_sha256=sha256(path),full_rank_checks=full))
                sites.append(site);del basis,target,tangents,ts,tz,hs,hz;gc.collect();torch.cuda.empty_cache()
            report['parents'].append(dict(parent_index=pi,sites=sites,duality=duality));save();del chart,templates,base,wt;gc.collect();torch.cuda.empty_cache()
    for h in hooks:h.remove()
    n=len(lock['assignments'][index]);assert counts==dict(recycle=n*388,nfe=n*4182,hard_rebuild=n*96,exact_replay=n*96,baseline_replay=n*96,jvp=n*95,vjp_forward=n,wt_forward=n,deduplicated_calls=n*190),counts
    report.update(complete=True,stage='complete',counts=counts,decoder_feature_reads=sorted(reads),seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated());save()


def collect_jacobian_residual(root):
    scoring.ARMS=ARMS;scoring.GLOBAL_VARIANTS=VARIANTS;scoring.collect_global_response_rank(root)
    lock=rt.load_json(root/'lock.json');summary=rt.load_json(root/'summary.json');old=rt.load_json(Path(lock['control_root'])/'summary.json')['summary'];rng=np.random.default_rng(228101);boot=rng.integers(0,10,(10000,10));comparison={}
    for v in VARIANTS:
        for k in GLOBAL_RANKS:
            name=f'{v}_k{k}';a=summary['summary'][name];b=old[name];parts={}
            for key in ['spearman','top1_match','top1_regret']:
                x=np.array(a['ranking']['exact']['False'][key]['per_protein'])-np.array(b['ranking']['exact']['False'][key]['per_protein']);parts[key]=dict(mean=float(x.mean()),protein_bootstrap95=np.quantile(x[boot].mean(1),[.025,.975]).tolist(),per_protein=x.tolist())
            comparison[name]=dict(paired=parts,local_tail_change=a['local_over_1a']-b['local_over_1a'],new_geometry_failure_change=a['new_compression_chemistry_failure']-b['new_compression_chemistry_failure'])
    write_json(root/'comparison.json',comparison)
    p=root/'report.md';p.write_text(p.read_text().replace('# Full s/z functional rank with WT s_inputs','# Fixed-WT Jacobian + full residual functional rank').replace('Entire target s/z reconstructed; mean and coefficients are in-sample oracle quantities.','Probability-space fixed-WT-graph JVP plus oracle residual PCA; WT s_inputs and target chemistry. Raw/balanced labels denote RESIDUAL metrics, not the previous direct PCA.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','run','score','collect'],required=True);p.add_argument('--index',type=int,default=0);a=p.parse_args()
    if a.mode=='prepare':prepare_jacobian_residual(a.root)
    elif a.mode=='run':run_jacobian_residual(a.root,a.index)
    elif a.mode=='score':scoring.ARMS=ARMS;scoring.score_global_response_rank(a.root,a.index)
    else:collect_jacobian_residual(a.root)
