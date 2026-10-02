import csv,gzip,json,sys
from pathlib import Path
import numpy as np
root=Path(sys.argv[1]);prior=Path(sys.argv[2]);out=Path(sys.argv[3]);out.mkdir(exist_ok=True,parents=True)
with gzip.open(root/'report.json.gz','rt') as f:r=json.load(f)
p=json.load(open(prior/'summary.json'))['summary'];summaries={16:p['channel_k16'],24:r['summary']['channel_k24'],32:p['channel_k32']}
mut=[m for w in r['workers'] for parent in w['parents'] for site in parent['sites'] for m in site['mutants']];es=[m['evidence']['rows'][0] for m in mut]
bootstrap=np.random.default_rng(230601).integers(0,10,(10000,10));comparison={}
for a,b in [(24,16),(32,24)]:
 comparison[f'{a}_minus_{b}']={}
 for metric in ['spearman','top1_match','top1_regret']:
  x=np.array(summaries[a]['ranking']['exact']['False'][metric]['per_protein'])-np.array(summaries[b]['ranking']['exact']['False'][metric]['per_protein'])
  comparison[f'{a}_minus_{b}'][metric]=dict(mean=float(x.mean()),protein_bootstrap95=np.quantile(x[bootstrap].mean(1),[.025,.975]).tolist())
full=[f for m in mut for f in m['full_rank_checks']]
extra=dict(energy_mean=float(np.mean([e['energy_retained'] for e in es])),factor_to_dense=float(np.mean([e['factor_to_dense'] for e in es])),factor_range=[min(e['factor_to_dense'] for e in es),max(e['factor_to_dense'] for e in es)],full_rank_checks=len(full),full_input_error=max(x['input_max_error'] for x in full),full_coordinate_error=max(x['coordinate_max_error'] for x in full),counts={k:sum(w['counts'][k] for w in r['workers']) for k in r['workers'][0]['counts']},both_noise_top1_sites=sum(all(q['top1_match'] for q in s['ranking'] if q['arm']=='channel_k24' and q['reference']=='exact' and not q['includes_wt']) for s in r['sites']),comparison=comparison)
(out/'comparison.json').write_text(json.dumps(extra,indent=2)+'\n')
lines=['# R24 extension, paired with frozen R16/R32','','|R|rho|Top1 /100|regret|local mean A|>1A /1900|new geometry vs Baseline|','|---:|---:|---:|---:|---:|---:|---:|']
for k,s in summaries.items():
 q=s['ranking']['exact']['False'];lines.append(f'|{k}|{q["spearman"]["mean"]:.6f}|{round(q["top1_match"]["mean"]*100)}|{q["top1_regret"]["mean"]:.8f}|{s["fidelity"]["local_ca_rmsd_global_frame"]["mean"]:.6f}|{s["local_over_1a"]}|{s["new_compression_chemistry_failure"]}|')
(out/'report.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines));print(json.dumps(extra,indent=2))
rows=[dict(parent_index=s['parent_index'],pdb_id=s['pdb_id'],position=s['position'],**q) for s in r['sites'] for q in s['ranking']]
with open(out/'ranking_per_site.csv','w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
