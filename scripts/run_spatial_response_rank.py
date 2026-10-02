"""Frozen per-mutant spatial compression, no new ESM/C4, no AA-axis fitting."""
import argparse,json,shutil,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import prepare_atom_pairs,diffusion_from_conditioning
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.conditioning_swaps import DecoderFeatureTrace
from fastglycan.functional_response_rank import pack_conditioning
from fastglycan.jacobian_residual_rank import archived_reference_coordinates
from fastglycan.spatial_response_rank import SpatialResponseBasis,SPATIAL_RANKS,SPATIAL_VARIANTS
import run_global_response_rank as scoring

# k in serialized names is a legacy scorer convention: here it ALWAYS means spatial R.
ARMS=('exact','baseline')+tuple(f'{v}_k{k}' for v in SPATIAL_VARIANTS for k in SPATIAL_RANKS)


def prepare_spatial_response_rank(root):
    prior=root.parent/'global_response_rank_v1_20261002';old=rt.load_json(prior/'lock.json')
    assert rt.load_json(prior/'controller_execution.json')['complete'] and not (root/'lock.json').exists()
    assert rt.load_json(root/'preflight.json')['complete']
    for item in old['conditioning_manifest']:assert sha256(Path(old['states'])/item['path'])==item['sha256']
    for p,h in old['weights_sha256'].items():assert sha256(Path(p))==h
    files=[dict(path=str(p.relative_to(prior)),sha256=sha256(p)) for pattern in ['worker_*/*_inventory.npz','worker_*/*_coordinates.npz'] for p in prior.glob(pattern)]
    assert len(files)==1920
    lock=dict(old);lock.update(schema='spatial_response_rank_v1',control_root=str(prior),prior_lock_sha256=sha256(prior/'lock.json'),
        input_files=files,arms=ARMS,variants=SPATIAL_VARIANTS,ranks=SPATIAL_RANKS,expected_nfe=28520,expected_c4=0,
        scope='per-mutant WT-anchored spatial Delta z; exact target s; WT s_inputs; native target chemistry; no AA centering',
        code_hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']},training=False)
    write_json(root/'lock.json',lock)


def run_spatial_response_rank(root,index):
    lock=rt.load_json(root/'lock.json');prior=Path(lock['control_root']);states=Path(lock['states']);torch.set_num_threads(1);start=time.monotonic()
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h,p
    for p,h in lock['weights_sha256'].items():assert sha256(Path(p))==h,p
    out=root/f'worker_{index}';out.mkdir(exist_ok=False);report=dict(complete=False,worker=index,parents=[],stage='load',lock_sha256=sha256(root/'lock.json'))
    def save():write_json(out/'report.json',report)
    save();runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    counts=dict(recycle=0,nfe=0,hard_rebuild=0,exact_replay=0,baseline_replay=0,decompositions=0,deduplicated_calls=0);reads=set()
    def forbidden(*args):counts['recycle']+=1;raise AssertionError('C4 forbidden')
    hooks=[model.pairformer_stack.register_forward_pre_hook(forbidden),model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('nfe',counts['nfe']+1))]
    hashes={f['path']:f['sha256'] for f in lock['conditioning_manifest']+lock['input_files']}
    def load_state(label,seq):
        p=states/f'worker_{index}/{label}_conditioning.pt';assert sha256(p)==hashes[str(p.relative_to(states))]
        packet=torch.load(p,map_location='cpu',weights_only=False);assert packet['sequence']==seq
        return tuple(t.cuda() for t in packet['conditioning'])
    def chemical_input(label,seq):
        invpath=prior/f'worker_{index}/{label}_inventory.npz';xyzpath=prior/f'worker_{index}/{label}_coordinates.npz'
        for p in [invpath,xyzpath]:assert sha256(p)==hashes[str(p.relative_to(prior))]
        inv=dict(np.load(invpath));native,atoms=native_sequence_features(seq)
        for key,values in [('atom_names',atoms.atom_name),('residue_ids',atoms.res_id),('chain_ids',atoms.chain_id),('bonds',atoms.bonds.as_array()),('reference',native['ref_pos'].numpy())]:assert np.array_equal(inv[key],values),key
        shutil.copy2(invpath,out/f'{label}_inventory.npz');counts['hard_rebuild']+=1
        return DecoderFeatureTrace(prepare_atom_pairs(model.relative_position_encoding.generate_relp(device_tree(native,'cuda')))),atoms,archived_reference_coordinates(np.load(xyzpath)['coordinates'],is_wt=label.endswith('_wt'))
    def decode(f,atoms,c):
        result=np.stack([diffusion_from_conditioning(model,f,identity_noise(atoms,seed,device='cuda'),pack_conditioning(c),steps=1).squeeze(0).cpu().numpy() for seed in lock['seeds']])
        reads.update(f.reads);assert np.isfinite(result).all();return result
    report['runtime']=dict(torch=torch.__version__,hip=torch.version.hip,device=torch.cuda.get_device_name(0))
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            row=lock['rows'][pi];seq=row['sequence'];wt=load_state(f'p{pi}_wt',seq);wf,wa,wold=chemical_input(f'p{pi}_wt',seq);wxyz=decode(wf,wa,wt)
            assert np.array_equal(wxyz,wold[0]) and np.array_equal(wxyz,wold[1]);counts['exact_replay']+=1;counts['baseline_replay']+=1
            np.savez_compressed(out/f'p{pi}_wt_coordinates.npz',coordinates=wxyz,seeds=lock['seeds']);sites=[]
            for pos in row['positions']:
                site=dict(position=pos,wt_index=lock['aa'].index(seq[pos]),mutants=[])
                for aa in lock['aa']:
                    if aa==seq[pos]:continue
                    label=f'p{pi}_s{pos+1}_{aa}';target_seq=seq[:pos]+aa+seq[pos+1:];report.update(stage='decompose_decode',active=label,counts=dict(counts));save()
                    c=load_state(label,target_seq);f,atoms,old=chemical_input(label,target_seq)
                    exact=decode(f,atoms,c);baseline=decode(f,atoms,(wt[0],c[1],c[2]));assert np.array_equal(exact,old[0]) and np.array_equal(baseline,old[1]),'reference replay'
                    counts['exact_replay']+=1;counts['baseline_replay']+=1
                    torch.cuda.synchronize();t=time.monotonic();basis=SpatialResponseBasis(wt[2],c[2]);torch.cuda.synchronize();decompose_seconds=time.monotonic()-t;counts['decompositions']+=1
                    evidence=basis.evidence();outputs=[exact,baseline];full=[];times=[];zero=None
                    # Save projected matrices for a predeclared CPU audit: first AA at each site.
                    audit=aa==next(a for a in lock['aa'] if a!=seq[pos]);audit_states={}
                    for variant in SPATIAL_VARIANTS:
                        for rank in SPATIAL_RANKS:
                            torch.cuda.synchronize();t=time.monotonic();z=basis.reconstruct(variant,rank);torch.cuda.synchronize();seconds=time.monotonic()-t
                            times.append(dict(variant=variant,rank=rank,seconds=seconds))
                            if audit and rank in (8,16,'full'):audit_states[f'{variant}_{rank}']=z.cpu()
                            if variant=='shared' and rank==0:
                                assert torch.equal(z,wt[2]);xyz=zero;counts['deduplicated_calls']+=2
                            else:xyz=decode(f,atoms,(wt[0],c[1],z))
                            if variant=='channel' and rank==0:assert torch.equal(z,wt[2]);zero=xyz
                            if rank=='full':
                                ie=float((z-c[2]).abs().max());ce=float(np.max(np.abs(xyz-baseline)))
                                assert ie<=lock['full_rank_input_tolerance'] and ce<=lock['full_rank_coordinate_tolerance'],(variant,ie,ce)
                                full.append(dict(variant=variant,input_max_error=ie,coordinate_max_error=ce))
                            outputs.append(xyz)
                    path=out/f'{label}_coordinates.npz';np.savez_compressed(path,coordinates=np.stack(outputs),arms=ARMS,seeds=lock['seeds'])
                    item=dict(aa=aa,label=label,coordinate_sha256=sha256(path),full_rank_checks=full,evidence=evidence,decomposition_seconds=decompose_seconds,reconstruction_times=times)
                    if audit:
                        patha=out/f'{label}_spatial_audit.pt';torch.save(audit_states,patha);item['audit_file']=patha.name;item['audit_sha256']=sha256(patha)
                    site['mutants'].append(item);del basis,c
                sites.append(site)
            report['parents'].append(dict(parent_index=pi,sites=sites));save()
    for h in hooks:h.remove()
    n=len(lock['assignments'][index]);assert counts==dict(recycle=0,nfe=n*2852,hard_rebuild=n*96,exact_replay=n*96,baseline_replay=n*96,decompositions=n*95,deduplicated_calls=n*190),counts
    report.update(complete=True,stage='complete',counts=counts,decoder_feature_reads=sorted(reads),seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated());save()


def configure_spatial_scoring():
    scoring.ARMS=ARMS;scoring.GLOBAL_VARIANTS=SPATIAL_VARIANTS;scoring.GLOBAL_RANKS=SPATIAL_RANKS


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--mode',required=True,choices=['prepare','run','score','collect']);p.add_argument('--index',type=int,default=0);a=p.parse_args()
    configure_spatial_scoring()
    if a.mode=='prepare':prepare_spatial_response_rank(a.root)
    elif a.mode=='run':run_spatial_response_rank(a.root,a.index)
    elif a.mode=='score':scoring.score_global_response_rank(a.root,a.index)
    else:
        scoring.collect_global_response_rank(a.root)
        report=a.root/'report.md';text=report.read_text().replace('# Full s/z functional rank with WT s_inputs','# Spatial Delta z functional rank').replace('Entire target s/z reconstructed; mean and coefficients are in-sample oracle quantities.','Per-mutant spatial Delta z oracle reconstruction, exact target s, WT s_inputs, target chemistry. No AA centering/compression.').replace('|Variant|K|','|Variant|Spatial R|');report.write_text(text)
