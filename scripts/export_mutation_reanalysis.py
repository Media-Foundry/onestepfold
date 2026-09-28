#!/usr/bin/env python3
"""Export posthoc descriptive tables without changing candidate acceptance."""
import argparse,csv,json
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root;out=root/'reanalysis';r=json.loads((out/'report.json').read_text());top=json.loads((out/'topology_rebuild.json').read_text());assert r['complete'] and top['complete'] and len(top['rows'])==33
parent=r['cases'][0];target=next(c for c in r['cases'] if c['sequence'][37]=='T' and sum(a!=b for a,b in zip(c['sequence'],parent['sequence']))==1)
def pairkey(x):return tuple(sorted((a['chain'],a['residue'],a['name']) for a in [x['a'],x['b']]))
with (out/'parent_y38t_pairs.tsv').open('w') as f:
 w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(['sequence','noise','atom_a','atom_b','distance_A','penetration_A','bond_graph_distance','severe','maximum','min_distance_to_res38_CA_A'])
 for name,case in [('parent',parent),('Y38T',target)]:
  for seed,v in case['values'].items():
   for x in v['pairs']:
    atoms=[f"{a['chain']}:{a['amino_acid']}{a['residue']}:{a['name']}" for a in [x['a'],x['b']]];w.writerow([name,seed,*atoms,x['distance'],x['penetration'],x['graph_distance'],x['severe'],x['is_maximum'],x['distance_to_res38_ca_min']])
with (out/'y38_ranking.tsv').open('w') as f:
 w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(['substitution','original_rank','local_score','noise','delta_total','delta_task','delta_bond','delta_peptide','delta_clash','delta_chirality'])
 for x in r['ranking']['rows']:
  for seed,v in x['deltas'].items():w.writerow([x['substitution'],x['original_gradient_rank'],x['score'],seed,*[v[k] for k in ['total','task','bond','peptide','clash','chirality']]])
summary=dict(scope='posthoc selected-candidate reanalysis, no inference or gate changes',regions={},parent_y38t={})
for seed in ['211','200003','200009']:
 region=lambda x:any(37<=a['residue']<=46 for a in [x['a'],x['b']]) and any(190<=a['residue']<=194 for a in [x['a'],x['b']])
 maximum=[next(x for x in c['values'][seed]['pairs'] if x['is_maximum']) for c in r['cases']]
 summary['regions'][seed]=dict(maximum_between_37_46_and_190_194=sum(region(x) for x in maximum),any_severe_between_37_46_and_190_194=sum(any(region(x) and x['severe'] for x in c['values'][seed]['pairs']) for c in r['cases']),any_severe_between_21_and_22=sum(any({x['a']['residue'],x['b']['residue']}=={21,22} and x['severe'] for x in c['values'][seed]['pairs']) for c in r['cases']),denominator=33)
 sets=[{pairkey(x) for x in c['values'][seed]['pairs'] if x['severe']} for c in [parent,target]];summary['parent_y38t'][seed]=dict(parent_severe=len(sets[0]),y38t_severe=len(sets[1]),shared_severe=len(sets[0]&sets[1]),maximum_identity_same=parent['values'][seed]['maximum_pair']==target['values'][seed]['maximum_pair'])
write_json(out/'summary.json',summary)
files=['report.json','topology_rebuild.json','parent_y38t_pairs.tsv','y38_ranking.tsv','summary.json'];write_json(out/'acceptance.json',dict(complete=True,original_report_matches=sha256(root/'report.json')==r['original_report_sha256'],no_new_predictions=True,model_deployment_accepted=False,artifacts={f:sha256(out/f) for f in files}))
