#!/usr/bin/env python3
"""Read-only decomposition of the completed position pilot; no new selection."""
import argparse,hashlib,io,json,tarfile,time
from pathlib import Path
import numpy as np
import torch
from scipy.stats import spearmanr
from fastglycan.models.soft_esm import AMINO_ACIDS
from fastglycan.paired_teacher_protocol import sha256,write_json

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();begin=time.monotonic();root=args.source
assert not args.output.exists()
manifest=json.loads((root/'completed_manifest.json').read_text());lookup={};gradients={};proposals={}
with tarfile.open(root/'completed.tar.gz') as archive:
    for member in archive.getmembers():
        if not member.isfile():continue
        if not (member.name.startswith('worker_') and member.name.endswith('/report.json')) and not (member.name.startswith('proposal_') and member.name.endswith(('/gradient.pt','/candidates.json','/report.json'))):continue
        payload=archive.extractfile(member).read();assert hashlib.sha256(payload).hexdigest()==manifest[member.name]['sha256']
        if member.name.startswith('worker_'):
            report=json.loads(payload);assert report['complete']
            for row in report['records']:
                key=(row['parent_index'],row['sequence']);assert key not in lookup;lookup[key]=row
        elif member.name.endswith('/gradient.pt'):
            gradients[int(member.name.split('/')[0].split('_')[1])]=torch.load(io.BytesIO(payload),map_location='cpu',weights_only=False)
        elif member.name.endswith('/candidates.json'):
            proposal=json.loads(payload);proposals[proposal['parent_index']]=proposal
assert len(lookup)==137 and len(gradients)==len(proposals)==4
reconstruction=[];results=[]
for parent_index,proposal in sorted(proposals.items()):
    baseline=lookup[parent_index,proposal['parent']]['values'];gp=gradients[parent_index]['gp'].double().numpy()
    for arm,options in proposal['arms'].items():
        assert len(options)==19
        local=np.array([gp[o['position'],AMINO_ACIDS.index(o['to_aa'])]-gp[o['position'],AMINO_ACIDS.index(o['from_aa'])] for o in options])
        matrices={key:np.empty((19,3)) for key in ['task','total']};components=[]
        for i,option in enumerate(options):
            c=[]
            for j,seed in enumerate([800011,800029,800053]):
                value=lookup[parent_index,option['sequence']]['values'][str(seed)];parent=baseline[str(seed)]
                for key in matrices:matrices[key][i,j]=value[key]-parent[key]
                terms=value['task_components'];reconstruction.append(abs(value['task']-(-terms['contact']+terms['clash']+.1*terms['chain'])))
                geom=value['geometry_terms'];reconstruction.append(abs(value['total']-(value['task']+geom['bond']+2*geom['peptide']+geom['clash']+.2*geom['chirality'])))
                c.append([-1*(terms['contact']-parent['task_components']['contact']),terms['clash']-parent['task_components']['clash'],.1*(terms['chain']-parent['task_components']['chain'])])
            components.append(c)
        components=np.asarray(components);assert np.max(np.abs(components.sum(-1)-matrices['task']))<1e-12
        statistics={}
        for key,y in matrices.items():
            grand=y.mean();mutation=y.mean(1,keepdims=True)-grand;seed=y.mean(0,keepdims=True)-grand;interaction=y-grand-mutation-seed
            energies=np.array([3*np.square(mutation).sum(),19*np.square(seed).sum(),np.square(interaction).sum()])
            denominator=np.square(y-grand).sum();assert np.isclose(energies.sum(),denominator,atol=1e-15,rtol=1e-12)
            statistics[key]=dict(dev_confirmation_mean_spearman=float(spearmanr(y[:,0],y[:,1:].mean(1)).statistic),
                local_score_spearman_each_noise=[float(spearmanr(local,y[:,j]).statistic) for j in range(3)],
                local_score_spearman_confirmation_mean=float(spearmanr(local,y[:,1:].mean(1)).statistic),
                local_score_spearman_three_noise_mean=float(spearmanr(local,y.mean(1)).statistic),
                centered_energy=float(denominator),descriptive_energy_fractions=(energies/denominator).tolist() if denominator>0 else None,
                delta_matrix=y.tolist())
        results.append(dict(parent_index=parent_index,pdb_id=proposal['pdb_id'],arm=arm,position=options[0]['position']+1,
            local_scores=local.tolist(),replacements=[o['to_aa'] for o in options],
            weighted_confirmation_task_components=components[:,1:,:].mean((0,1)).tolist(),statistics=statistics))
assert max(reconstruction)<1e-6
write_json(args.output,dict(complete=True,posthoc=True,new_inference=0,source_hashes={name:sha256(root/name) for name in ['completed.tar.gz','completed_manifest.json','completed_analysis.json']},
    script_sha256=sha256(Path(__file__)),seconds=time.monotonic()-begin,reconstruction_max_abs=max(reconstruction),
    component_order=['negative_contact','ca_clash','0.1_ca_chain'],energy_order=['mutation_main','noise_main','interaction'],
    noise_order=[800011,800029,800053],results=results,
    limitations='Eight selected-site panels, four TRAIN parents, with 1BFT duplicate arms. Descriptive fixed-three-noise decomposition, not population variance or new confirmation. No thresholds, candidates or selections changed.'))
print(json.dumps(dict(rows=len(results),reconstruction_max_abs=max(reconstruction),output=str(args.output))))
