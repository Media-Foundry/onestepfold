"""Bounded full-hard-sequence C4 endpoint collection and post-hoc local spectra."""
import argparse
import hashlib
import time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import full_recycle_pairformer,prepare_atom_pairs
from fastglycan.hard_response_rank import analyze_hard_response_site

AA='ACDEFGHIKLMNPQRSTVWY'


def prepare_hard_response_rank(root):
    priorpath=root.parent/'noise_diversity_assessment_v1_20261001_retry1/original/lock.json'
    prior=rt.load_json(priorpath);assert not (root/'lock.json').exists()
    excluded={'1en7','5i27','2d00','3pmd','1l12','1l04','1tay','1tdy','1gob','2rn2','1izr','1izq'}
    candidates=[r for r in prior['rows'] if r['role']=='train' and set(r['sequence'])<=set(AA) and r['pdb_id'].lower() not in excluded]
    candidates.sort(key=lambda r:hashlib.sha256(('hard-response-rank-v1:20261002:'+r['group_id']).encode()).hexdigest())
    rows=[];used=set();eligible=[]
    for lo,hi,count in [(80,128,4),(129,192,3),(193,256,3)]:
        pool=[r for r in candidates if lo<=len(r['sequence'])<=hi];eligible.append(dict(low=lo,high=hi,count=len(pool)))
        chosen=[]
        for row in pool:
            accession=set(row.get('accessions',[]))
            if not accession or accession&used:continue
            used|=accession;chosen.append(row)
            if len(chosen)==count:break
        assert len(chosen)==count,(lo,hi)
        for row in chosen:
            positions=sorted(range(len(row['sequence'])),key=lambda i:hashlib.sha256(('hard-response-site-v1:20261002:'+row['group_id']+':'+str(i)).encode()).hexdigest())[:5]
            rows.append(dict(index=len(rows),group_id=row['group_id'],pdb_id=row['pdb_id'],sequence=row['sequence'],accessions=row['accessions'],positions=positions,
                source_metadata=row,stratum=[lo,hi]))
    assignments=[[] for _ in range(8)];load=[0]*8
    for row in sorted(rows,key=lambda r:len(r['sequence']),reverse=True):
        i=min(range(8),key=lambda j:load[j]);assignments[i].append(row['index']);load[i]+=len(row['sequence'])**2
    for p,h in prior['weights_sha256'].items():assert sha256(Path(p))==h,p
    write_json(root/'lock.json',dict(schema='hard_response_rank_v1',rows=rows,eligible=eligible,assignments=assignments,amino_acids=AA,
        weights_sha256=prior['weights_sha256'],prior_sha256=sha256(priorpath),cycles=4,model=rt.MODEL,workers=8,
        code_hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']},
        unique_hard_sequences=960,replay_forwards=20,expected_c4_forwards=980,expected_recycle_calls=3920,
        expected_denoiser_calls=0,bootstrap_seed=224001,bootstrap_repeats=10000,training=False))


def run_hard_response_rank(root,index):
    lock=rt.load_json(root/'lock.json');torch.set_num_threads(1);start=time.monotonic()
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h,p
    out=root/f'worker_{index}';out.mkdir(exist_ok=False)
    report=dict(complete=False,stage='load',records=[],lock_sha256=sha256(root/'lock.json'),worker=index)
    def save():write_json(out/'report.json',report)
    save();runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    for p,h in lock['weights_sha256'].items():assert sha256(Path(p))==h,p
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir)
    esm.eval().requires_grad_(False);report['load_seconds']=time.monotonic()-start
    report['runtime']=dict(torch=torch.__version__,hip=torch.version.hip,gpu=torch.cuda.get_device_name(0),model_dtype=str(next(model.parameters()).dtype),esm_dtype=str(next(esm.parameters()).dtype))
    counts=dict(recycle=0,denoiser=0,forwards=0);times=[]
    hooks=[model.pairformer_stack.register_forward_hook(lambda *a:counts.__setitem__('recycle',counts['recycle']+1)),
           model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('denoiser',counts['denoiser']+1))]
    def forward(sequence,positions):
        torch.cuda.synchronize();t=time.monotonic();native,atoms=native_sequence_features(sequence)
        identities=[(str(c),int(r),str(a)) for c,r,a in zip(atoms.chain_id,atoms.res_id,atoms.atom_name)]
        import json
        identity_sha=hashlib.sha256(json.dumps(identities,separators=(',',':')).encode()).hexdigest()
        topology_sha=hashlib.sha256(atoms.bonds.as_array().tobytes()).hexdigest()
        f=model.relative_position_encoding.generate_relp(device_tree(native,'cuda'))
        tokens=alphabet.get_batch_converter()([('hard',sequence)])[2].cuda()
        f['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
        f=prepare_atom_pairs(f);torch.cuda.synchronize();features_seconds=time.monotonic()-t;t=time.monotonic();before=counts['recycle']
        inputs,s,z=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False)
        assert counts['recycle']-before==4 and counts['denoiser']==0
        assert s.shape[0]==z.shape[0]==z.shape[1]==len(sequence)
        assert s.dtype==z.dtype==torch.float32
        assert torch.isfinite(s).all() and torch.isfinite(z).all()
        torch.cuda.synchronize();c4_seconds=time.monotonic()-t
        pos=torch.tensor(positions,device=s.device)
        values=dict(s_site=s[pos].cpu().numpy(),z_row=z[pos,:,:].cpu().numpy(),z_col=z[:,pos,:].permute(1,0,2).cpu().numpy(),s_inputs_site=inputs[pos].cpu().numpy())
        metadata=dict(atoms=len(atoms),atom_identity_sha256=identity_sha,topology_sha256=topology_sha,
            mutated_site_atom_names={str(i):atoms.atom_name[atoms.res_id==i+1].tolist() for i in positions})
        counts['forwards']+=1;times.append(dict(features_esm_seconds=features_seconds,c4_seconds=c4_seconds))
        return values,metadata
    with torch.no_grad():
        for parent_index in lock['assignments'][index]:
            row=lock['rows'][parent_index];seq=row['sequence'];positions=row['positions'];report['stage']=f'parent_{parent_index}';save()
            wt,wm=forward(seq,positions);repeat,rm=forward(seq,positions)
            assert wm==rm and all(np.array_equal(wt[k],repeat[k]) for k in wt),'WT exact replay'
            for site_index,pos in enumerate(positions):
                arrays={k:np.empty((20,*v.shape[1:]),dtype=np.float32) for k,v in wt.items()};ledger=[]
                first_nonwt=next(a for a in AA if a!=seq[pos]);replay_passed=None
                for ai,aa in enumerate(AA):
                    if aa==seq[pos]:
                        values={k:v[site_index:site_index+1] for k,v in wt.items()};meta=wm
                    else:
                        mutant=seq[:pos]+aa+seq[pos+1:];values,meta=forward(mutant,[pos])
                        if site_index==0 and aa==first_nonwt:
                            rep,repmeta=forward(mutant,[pos]);replay_passed=meta==repmeta and all(np.array_equal(values[k],rep[k]) for k in values)
                            assert replay_passed,'mutant exact replay'
                    for k in arrays:arrays[k][ai]=values[k][0]
                    ledger.append(dict(amino_acid=aa,is_wt=aa==seq[pos],**meta))
                filename=f'p{parent_index}_site{pos+1}.npz';np.savez_compressed(out/filename,**arrays)
                analysis=analyze_hard_response_site(arrays,AA.index(seq[pos]),pos)
                item=dict(parent_index=parent_index,pdb_id=row['pdb_id'],position_0based=pos,position_1based=pos+1,wt=seq[pos],amino_acids=AA,
                    endpoint_file=filename,endpoint_sha256=sha256(out/filename),wt_replay_exact=True,mutant_replay_exact=replay_passed,ledger=ledger,analysis=analysis)
                report['records'].append(item);report['counts']=dict(counts);save()
    for h in hooks:h.remove()
    n=len(lock['assignments'][index]);assert counts==dict(recycle=n*392,denoiser=0,forwards=n*98)
    report.update(complete=True,stage='complete',counts=counts,forward_timings=times,seconds=time.monotonic()-start,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved());save()


def collect_hard_response_rank(root):
    lock=rt.load_json(root/'lock.json');workers=[rt.load_json(root/f'worker_{i}/report.json') for i in range(8)]
    assert all(w['complete'] and w['lock_sha256']==sha256(root/'lock.json') for w in workers)
    records=sorted([r for w in workers for r in w['records']],key=lambda r:(r['parent_index'],r['position_0based']))
    assert len(records)==50 and len({(r['parent_index'],r['position_0based']) for r in records})==50
    assert sum(w['counts']['forwards'] for w in workers)==980 and sum(w['counts']['recycle'] for w in workers)==3920
    for w in workers:
        for r in w['records']:assert sha256(root/f'worker_{w["worker"]}'/r['endpoint_file'])==r['endpoint_sha256']
    rng=np.random.default_rng(lock['bootstrap_seed']);boot=rng.integers(0,10,size=(lock['bootstrap_repeats'],10));summaries={}
    for variant in records[0]['analysis']['spectra']:
        summaries[variant]={}
        for centering in ['wt_anchored','mutant_centered']:
            rows=[r['analysis']['spectra'][variant][centering] for r in records];valid=[i for i,x in enumerate(rows) if not x['zero_signal']]
            if len(valid)!=50:
                summaries[variant][centering]=dict(informative_sites=len(valid),zero_signal_sites=50-len(valid),summary_unavailable='retain zero-signal denominator; inspect per-site records');continue
            energies=np.array([r['cumulative_energy'][:5] for r in rows]);parent=np.array([energies[[i for i,r in enumerate(records) if r['parent_index']==pi]].mean(0) for pi in range(10)])
            interval=np.quantile(parent[boot].mean(1),[.025,.975],axis=0)
            summaries[variant][centering]=dict(informative_sites=50,mean_energy_k1_to_k5=energies.mean(0).tolist(),
                median_energy_k1_to_k5=np.median(energies,axis=0).tolist(),protein_bootstrap95=interval.T.tolist(),
                sites_energy3_at_least95=int((energies[:,2]>=.95).sum()),sites_energy5_at_least95=int((energies[:,4]>=.95).sum()),
                median_rank95=float(np.median([r['rank95'] for r in rows])),min_rank95=min(r['rank95'] for r in rows),max_rank95=max(r['rank95'] for r in rows),
                per_protein_mean_energy=parent.tolist())
    write_json(root/'report.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),parents=lock['rows'],sites=records,
        summaries=summaries,workers=workers,training=False,deployment_accepted=False,scope='post-hoc local response spectra only'))
    lines=['# C4 hard-mutant response rank v1','','50 sites in10 development proteins;19 non-WT response vectors/site.','',
        '|Variant|Centering|K1|K2|K3|K4|K5|E3≥95%|E5≥95%|Median rank95|','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for variant,summary in summaries.items():
        for kind,v in summary.items():
            if v.get('mean_energy_k1_to_k5') is None:continue
            lines.append('|'+variant+'|'+kind+'|'+ '|'.join(f'{x:.4f}' for x in v['mean_energy_k1_to_k5'])+f'|{v["sites_energy3_at_least95"]}/50|{v["sites_energy5_at_least95"]}/50|{v["median_rank95"]}|')
    lines+=['','These are in-sample compression ratios, not prediction accuracy, global-z rank, decoder quality or speedup.']
    (root/'report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--mode',required=True,choices=['prepare','run','collect']);p.add_argument('--index',type=int,default=0);a=p.parse_args()
    if a.mode=='prepare':prepare_hard_response_rank(a.root)
    elif a.mode=='collect':collect_hard_response_rank(a.root)
    else:run_hard_response_rank(a.root,a.index)
