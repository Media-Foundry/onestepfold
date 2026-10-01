"""CPU-only target-GT evaluation, separate from all Chord inference processes."""
import argparse
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.chord_edit import backbone_indices
from fastglycan.chord_evaluation import edit_backbone_metrics
from fastglycan.diffusion_pilot_metrics import prepare_pilot_scoring,score_diffusion_pilot


def score_chord_edit(root):
    lock=rt.load_json(root/'lock.json');calibration=rt.load_json(root/'code/docs/connection_reference_bands.json')
    for p,h in lock['input_hashes'].items():assert sha256(Path(p))==h,p
    records=[];experimental=[];workers=[]
    for pi,pair in enumerate(lock['pairs']):
        folder=root/'inputs'/str(pi);report=rt.load_json(root/f'worker_{pi}/report.json');assert report['complete'];workers.append(report)
        sm=dict(np.load(folder/'source_gt.npz'));tm=dict(np.load(folder/'target_gt.npz'))
        sn=torch.load(folder/'source_native.pt',map_location='cpu',weights_only=False)
        tn=torch.load(folder/'target_native.pt',map_location='cpu',weights_only=False)
        si=backbone_indices(sn['atoms'],len(pair['source_sequence']));ti=backbone_indices(tn['atoms'],len(pair['target_sequence']))
        source=sm['coordinates'][si[:,1]];target=tm['coordinates'][ti[:,1]];local=np.load(folder/'local_region.npy')
        context=prepare_pilot_scoring(tm,tn['atoms'].bonds.as_array(),pair['target_sequence'])
        copy=edit_backbone_metrics(source,source,target,local)
        # Experimental chemistry only if full native inventory is observed; no zeros scored as atoms.
        baselines={}
        for role,m,n,seq in [('source',sm,sn,pair['source_sequence']),('target',tm,tn,pair['target_sequence'])]:
            baselines[role]=score_diffusion_pilot(m['coordinates'],prepare_pilot_scoring(m,n['atoms'].bonds.as_array(),seq),calibration) if m['mask'].all() else dict(unavailable='incomplete native inventory',missing=int((~m['mask']).sum()))
        experimental.append(dict(pair_index=pi,source=pair['source'],target=pair['target'],mutation=pair['mutation'],copy=copy,geometry=baselines))
        for item in report['records']:
            p=root/f'worker_{pi}/noise_{item["seed"]}.npz';assert sha256(p)==item['output_sha256'];xs=np.load(p)
            arms={'copy_source':dict(backbone=copy,full=None)}
            for name in ['cold_s1','cold_s2','source_sigma16','source_sigma1','naive_refined','smooth_refined']:
                x=xs[name];assert x.shape==tm['coordinates'].shape
                arms[name]=dict(backbone=edit_backbone_metrics(x[ti[:,1]],source,target,local),full=score_diffusion_pilot(x,context,calibration))
            for name in ['naive','smooth']:
                arms[name+'_backbone']=dict(backbone=edit_backbone_metrics(xs[name+'_backbone'][:,1],source,target,local),full=None)
            self_refine=xs['no_edit_refined'][si[:,1]]
            no_edit=edit_backbone_metrics(self_refine,source,source,local)
            records.append(dict(pair_index=pi,source=pair['source'],target=pair['target'],seed=item['seed'],arms=arms,no_edit_refinement=no_edit))
    methods=list(records[0]['arms']);summary={}
    for method in methods:
        rows=[r['arms'][method] for r in records]
        bbkeys=['ca_lddt','ca_aligned_rmsd','local_target_rmsd','nonlocal_target_rmsd','nonlocal_motion']
        values={k:float(np.mean([r['backbone'][k] for r in rows])) for k in bbkeys}
        values['local_better_than_copy']=sum(r['arms'][method]['backbone']['local_target_rmsd']<r['arms']['copy_source']['backbone']['local_target_rmsd'] for r in records)
        values['local_better_both_seeds']=sum(all(r['arms'][method]['backbone']['local_target_rmsd']<r['arms']['copy_source']['backbone']['local_target_rmsd'] for r in records if r['pair_index']==pi) for pi in range(4))
        if rows[0]['full'] is not None:
            values['all_atom_lddt']=float(np.mean([r['full']['all_atom_lddt'] for r in rows]))
            values['severe_pairs_total']=sum(r['full']['geometry']['severe_pairs'] for r in rows)
            values['zero_severe_strict_checked']=sum(r['full']['geometry']['severe_pairs']==0 and r['full']['geometry']['strict_checked_chirality'] for r in rows)
        summary[method]=values
    result=dict(complete=True,development_pairs=4,noise_instances=8,records=records,experimental=experimental,summary=summary,
        inference_reports=workers,lock_sha256=sha256(root/'lock.json'),deployment_accepted=False,
        scope='hard target sequence editing; experimental differences not solely mutation effects; no native disulfide augmentation')
    write_json(root/'report.json',result)
    lines=['# ChordFold editing pilot v1','', 'Four development pairs × two seeds. No training or recycle compression.','',
        '|Method|CA-lDDT|Global CA RMSD|Local target RMSD|Nonlocal motion|Local beats copy|Severe pairs|Zero severe + checked chirality|',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,v in summary.items():lines.append(f'|{name}|{v["ca_lddt"]:.6f}|{v["ca_aligned_rmsd"]:.4f}|{v["local_target_rmsd"]:.4f}|{v["nonlocal_motion"]:.4f}|{v["local_better_than_copy"]}/8|{v.get("severe_pairs_total","N/A")}|{v.get("zero_severe_strict_checked","N/A")}|')
    lines+=['','Raw paired metrics, native chemistry limitations, timing and actual query counts are retained in report.json.',
        'The sigma-domain edit is a proxy, not a validated transfer of ChordEdit theory. Copy has no target all-atom score.']
    (root/'report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();score_chord_edit(a.root)
