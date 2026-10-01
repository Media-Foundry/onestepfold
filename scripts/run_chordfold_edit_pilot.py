"""Frozen hard-condition edit probe; target labels are confined to CPU scoring."""
import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np
import torch

from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.chord_edit import (backbone_indices, lift_backbone,
    initialize_target_atoms, chord_backbone_update, ChordDenoiser)
from fastglycan.models.soft_sequence_chart import native_sequence_features, device_tree
from fastglycan.models.differentiable_mini import full_recycle_pairformer, prepare_atom_pairs, diffusion_from_conditioning
from onestepfold.data.gt_materializer import ATOM37_INDEX


def prepare_chord_edit(root, inventory):
    """Validate frozen metadata-selected pairs, rebuild native inputs, lock all hashes."""
    selection=rt.load_json(inventory); pairs=selection['pairs']; assert len(pairs)==4
    assert not (root/'lock.json').exists()
    prior=rt.load_json(root.parent/'noise_diversity_assessment_v1_20261001_retry1/original/lock.json')
    for p,h in prior['weights_sha256'].items(): assert sha256(Path(p))==h,p
    inputs={str(inventory):sha256(inventory)}; records=[]
    for pi,pair in enumerate(pairs):
        a,b=pair['a'],pair['b'];sa,sb=a['sequence'],b['sequence']
        assert len(sa)==len(sb) and sum(x!=y for x,y in zip(sa,sb))==1
        assert a['pdb_id']!=b['pdb_id'] and len(pair['shared_accessions'])>0
        folder=root/'inputs'/str(pi);folder.mkdir(parents=True)
        metadata={}; accessions=[]
        for role,row in [('source',a),('target',b)]:
            data=Path(pair['source_root'])/'examples'/row['group_id']; meta=rt.load_json(data/'gt.json');gt=dict(np.load(data/'gt.npz'))
            for p in [data/'gt.json',data/'gt.npz']:inputs[str(p)]=sha256(p)
            sequence=row['sequence']; chain=meta['chains'][0]
            assert len(meta['chains'])==1 and chain['sequence']==sequence
            assert meta['qa']['chain_break_count']==0 and meta['qa']['modified_residue_count']==0
            assert gt['residue_mask'].all() and np.unique(gt['chain_index']).size==1
            assert gt['atom37_mask'][:,[ATOM37_INDEX[x] for x in ['N','CA','C','O']]].all()
            native,atoms=native_sequence_features(sequence)
            ref=native['ref_pos'].cpu().numpy(); coords=np.zeros_like(ref); mask=np.zeros(len(atoms),dtype=bool)
            for i,(r,name) in enumerate(zip(atoms.res_id,atoms.atom_name)):
                if str(name) in ATOM37_INDEX:
                    ri=int(r)-1;ai=ATOM37_INDEX[str(name)];mask[i]=gt['atom37_mask'][ri,ai]
                    if mask[i]:coords[i]=gt['atom37_positions'][ri,ai]
            ix=backbone_indices(atoms,len(sequence));assert mask[ix].all() and np.isfinite(coords[mask]).all()
            # GT mapping lives in a separate file, never loaded by the inference worker for target.
            np.savez_compressed(folder/f'{role}_gt.npz',coordinates=coords,mask=mask,reference=ref,
                atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id)
            torch.save(dict(features=native,atoms=atoms,sequence=sequence),folder/f'{role}_native.pt')
            if role=='source':
                reference=torch.from_numpy(ref); backbone=torch.from_numpy(coords[ix])
                clean=lift_backbone(reference,atoms.res_id,ix,reference[torch.as_tensor(ix)],backbone)
                clean[torch.from_numpy(mask)]=torch.from_numpy(coords[mask])
                np.save(folder/'source_clean.npy',clean.numpy())
                ca=coords[ix[:,1]];pos=pair['position']
                local=(np.linalg.norm(ca-ca[pos],axis=1)<=8.) | (np.abs(np.arange(len(sequence))-pos)<=2)
                assert (~local).sum()>=3
                np.save(folder/'local_region.npy',local)
            sg=np.flatnonzero((atoms.atom_name=='SG')&mask);close=[];bonds=atoms.bonds.as_array()[:,:2]
            for k,i in enumerate(sg):
                for j in sg[k+1:]:
                    d=float(np.linalg.norm(coords[i]-coords[j]))
                    if d<2.5:
                        bonded=bool(((bonds==[i,j]).all(1)|(bonds==[j,i]).all(1)).any())
                        close.append(dict(residues=[int(atoms.res_id[i]),int(atoms.res_id[j])],distance=d,native_bond=bonded))
            metadata[role]=dict(pdb_id=row['pdb_id'],group_id=row['group_id'],length=len(sequence),
                native_atoms=len(atoms),missing_observed_atoms=int((~mask).sum()),sg_proximity=close,
                source_metadata=meta)
        records.append(dict(index=pi,source=a['pdb_id'],target=b['pdb_id'],source_sequence=sa,target_sequence=sb,
            mutation=f'{sa[pair["position"]]}{pair["position"]+1}{sb[pair["position"]]}',metadata=metadata))
    hashes={str(p):sha256(p) for p in (root/'inputs').rglob('*') if p.is_file()}
    code={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']}
    write_json(root/'lock.json',dict(pairs=records,input_hashes=hashes,provenance_hashes=inputs,code_hashes=code,
        weights_sha256=prior['weights_sha256'],seeds=[221003,221021],sigma_high=16.,sigma_low=12.,sigma_refine=1.,
        model=rt.MODEL,cycles=4,workers=4,source='experimental',training=False,target_gt_in_inference=False))


def run_chord_edit_case(root,index):
    lock=rt.load_json(root/'lock.json');pair=lock['pairs'][index];folder=root/'inputs'/str(index)
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h,p
    for p,h in lock['input_hashes'].items():
        # Target GT is neither read nor hashed in the prediction process.
        if not p.endswith('target_gt.npz'):assert sha256(Path(p))==h,p
    out=root/f'worker_{index}';out.mkdir(exist_ok=False);torch.set_num_threads(1)
    start=time.monotonic(); report=dict(complete=False,index=index,records=[],lock_sha256=sha256(root/'lock.json'),stage='load')
    def save():write_json(out/'report.json',report)
    save();runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    for p,h in lock['weights_sha256'].items():assert sha256(Path(p))==h,p
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    from fastglycan.hybrid_proposals import identity_noise
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir)
    esm.eval().requires_grad_(False);report['load_seconds']=time.monotonic()-start
    report['runtime']=dict(torch=torch.__version__,hip=torch.version.hip,gpu=torch.cuda.get_device_name(0),dtype='float32',batch=1)
    def timed(fn):
        torch.cuda.synchronize();t=time.monotonic();value=fn();torch.cuda.synchronize();return value,time.monotonic()-t
    counts=dict(recycle=0,denoiser=0)
    hooks=[model.pairformer_stack.register_forward_hook(lambda *a:counts.__setitem__('recycle',counts['recycle']+1)),
           model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('denoiser',counts['denoiser']+1))]
    def prepare(role):
        sequence=pair[f'{role}_sequence']; archived=torch.load(folder/f'{role}_native.pt',map_location='cpu',weights_only=False)
        def features():
            native,atoms=native_sequence_features(sequence)
            assert np.array_equal(atoms.atom_name,archived['atoms'].atom_name)
            assert np.array_equal(atoms.res_id,archived['atoms'].res_id)
            for k,v in native.items():
                if isinstance(v,torch.Tensor):assert torch.equal(v,archived['features'][k]),k
            f=model.relative_position_encoding.generate_relp(device_tree(native,'cuda'))
            tokens=alphabet.get_batch_converter()([(role,sequence)])[2].cuda()
            f['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
            return prepare_atom_pairs(f),atoms
        (f,atoms),ft=timed(features)
        before=counts['recycle'];c,ct=timed(lambda:full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False))
        assert counts['recycle']-before==4
        # Match previously audited packed conditioning storage/layout.
        shapes=[x.shape for x in c];sizes=[x.numel() for x in c]
        c=tuple(x.reshape(s) for x,s in zip(torch.cat([x.flatten() for x in c]).split(sizes),shapes))
        decoder,dt=timed(lambda:ChordDenoiser(model,f,c))
        return f,atoms,c,decoder,dict(features_esm_seconds=ft,c4_seconds=ct,decoder_cache_seconds=dt)
    with torch.no_grad():
        sf,sa,sc,sd,st=prepare('source');tf,ta,tc,td,tt=prepare('target')
        source=torch.from_numpy(np.load(folder/'source_clean.npy')).cuda()
        si=torch.as_tensor(backbone_indices(sa,len(pair['source_sequence'])),device='cuda')
        ti=torch.as_tensor(backbone_indices(ta,len(pair['target_sequence'])),device='cuda')
        target,init_time=timed(lambda:initialize_target_atoms(sa,source,ta,tf['ref_pos'],pair['source_sequence'],pair['target_sequence']))
        sb=source[si]; assert torch.equal(target[ti],sb)
        report.update(source_preparation=st,target_preparation=tt,sidechain_initialization_seconds=init_time,stage='predict');save()
        for ni,seed in enumerate(lock['seeds']):
            sn=identity_noise(sa,seed,device='cuda')[0]/2560.;tn=identity_noise(ta,seed,device='cuda')[0]/2560.
            assert torch.equal(sn[si],tn[ti]);dtime={};xs={}
            for steps in [1,2]:xs[f'cold_s{steps}'],dtime[f'cold_s{steps}']=timed(lambda:td.cold_sample(tn*2560.,steps))
            replay=diffusion_from_conditioning(model,tf,(tn*2560.)[None],tc,steps=1)[0]
            assert torch.equal(replay,xs['cold_s1']), 'native cold S1 parity'
            hi,lo=lock['sigma_high'],lock['sigma_low']
            sh,dtime['source_high']=timed(lambda:sd.denoise(source+hi*sn,hi))
            th,dtime['target_high']=timed(lambda:td.denoise(target+hi*tn,hi))
            sl,dtime['source_low']=timed(lambda:sd.denoise(source+lo*sn,lo))
            tl,dtime['target_low']=timed(lambda:td.denoise(target+lo*tn,lo))
            sh2=sd.denoise(source+hi*sn,hi);sl2=sd.denoise(source+lo*sn,lo)
            assert torch.equal(sh,sh2) and torch.equal(sl,sl2)
            same1,same2,_,_=chord_backbone_update(sb,sh[si],sh2[si],sl[si],sl2[si],sigma_high=hi,sigma_low=lo)
            assert torch.equal(same1,sb) and torch.equal(same2,sb)
            naive,smooth,hf,smf=chord_backbone_update(sb,sh[si],th[ti],sl[si],tl[ti],sigma_high=hi,sigma_low=lo)
            xs['source_sigma16']=th
            xs['source_sigma1'],dtime['target_refine_source']=timed(lambda:td.denoise(target+tn,1.))
            self_refine=sd.denoise(source+sn,1.)
            for name,backbone in [('naive',naive),('smooth',smooth)]:
                lifted,dtime[f'{name}_lift']=timed(lambda:lift_backbone(target,ta.res_id,ti,target[ti],backbone))
                xs[f'{name}_refined'],dtime[f'{name}_refine']=timed(lambda:td.denoise(lifted+tn,1.))
            assert all(torch.isfinite(x).all() for x in xs.values())
            path=out/f'noise_{seed}.npz'
            np.savez_compressed(path,**{k:v.cpu().numpy() for k,v in xs.items()},source_backbone=sb.cpu().numpy(),
                naive_backbone=naive.cpu().numpy(),smooth_backbone=smooth.cpu().numpy(),
                high_field=hf.cpu().numpy(),smooth_field=smf.cpu().numpy(),no_edit_refined=self_refine.cpu().numpy())
            costs=dict(copy_source=dict(nfe=0,first_seconds=0.,cached_seconds=0.))
            src=sum(st.values());tgt=sum(tt.values())
            for name,nfe,compute,uses_source in [
                ('cold_s1',1,dtime['cold_s1'],False),('cold_s2',2,dtime['cold_s2'],False),
                ('source_sigma16',1,dtime['target_high']+init_time,False),
                ('source_sigma1',1,dtime['target_refine_source']+init_time,False),
                ('naive_refined',3,dtime['source_high']+dtime['target_high']+dtime['naive_lift']+dtime['naive_refine']+init_time,True),
                ('smooth_refined',5,sum(dtime[k] for k in ['source_high','source_low','target_high','target_low','smooth_lift','smooth_refine'])+init_time,True)]:
                cached=compute-(dtime['source_high']+(dtime['source_low'] if name=='smooth_refined' else 0.) if uses_source else 0.)
                costs[name]=dict(nfe=nfe,cached_nfe=nfe-(2 if name=='smooth_refined' else 1 if name=='naive_refined' else 0),
                    first_seconds=tgt+compute+(src if uses_source else 0),cached_seconds=tgt+cached)
            item=dict(seed=seed,noise_identity=True,cold_parity_exact=True,no_edit_cancellation_exact=True,
                output_sha256=sha256(path),query_seconds=dtime,costs=costs)
            if ni==0:
                # Actual same-target replay, with fresh target features/C4 and cached source outputs.
                begin=time.monotonic();rf,ra,rc,rd,rtimes=prepare('target')
                rh=rd.denoise(target+hi*tn,hi);rl=rd.denoise(target+lo*tn,lo)
                _,rb,_,_=chord_backbone_update(sb,sh[si],rh[ti],sl[si],rl[ti],sigma_high=hi,sigma_low=lo)
                ry=rd.denoise(lift_backbone(target,ta.res_id,ti,target[ti],rb)+tn,1.)
                torch.cuda.synchronize();item['same_variant_cached_replay_seconds']=time.monotonic()-begin
                item['cached_replay_exact']=torch.equal(ry,xs['smooth_refined']);assert item['cached_replay_exact']
                item['recomputed_target_preparation']=rtimes
                del rf,rc,rd,ry,rh,rl,rb
            report['records'].append(item);save()
    for hook in hooks:hook.remove()
    report.update(complete=True,stage='complete',actual_calls=counts,seconds=time.monotonic()-start,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved());save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','run'],required=True)
    p.add_argument('--inventory',type=Path);p.add_argument('--index',type=int,default=0);a=p.parse_args()
    if a.mode=='prepare':prepare_chord_edit(a.root,a.inventory)
    else:run_chord_edit_case(a.root,a.index)
