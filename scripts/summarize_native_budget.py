"""Protein-aware native compute/quality curve; no promotion or adaptive budget."""
import argparse,json,csv
from pathlib import Path
from collections import defaultdict
import numpy as np


def summarize_native_budget(root):
    load=lambda p:json.loads(Path(p).read_text());assert load(root/'independent_audit.json')['complete'];r=load(root/'report.json');lock=load(root/'lock.json')
    out=root/'analysis';out.mkdir(exist_ok=True);groups={};selection=[]
    def protein_stats(rows,key):
        per=defaultdict(list)
        for v in rows:
            if v[key] is not None:per[v['parent_index']].append(v[key])
        pp={str(k):float(np.mean(v)) for k,v in per.items()};a=list(pp.values())
        return dict(mean=float(np.mean(a)) if a else None,median=float(np.median(a)) if a else None,maximum=max(a) if a else None,per_protein=pp)
    for s in r['sites']:
        selection.append(dict(parent_index=s['parent_index'],pdb_id=s['pdb_id'],position=s['position'],source_aa=s['source_aa'],cycles=s['cycles'],role=s['role'],
            **s['selection']['aggregate']['all'],**s['selection']['cross_noise'],selected_both_new_actual_geometry=all(x['zero_severe_strict_checked_chirality'] for x in s['selected_actual_geometry'][2:]),
            selected_both_new_C4_geometry=all(x['zero_severe_strict_checked_chirality'] for x in s['selected_C4_geometry'][2:])))
    for role in ['development','stress']:
        for cycle in [1,2,4]:
            ss=[s for s in selection if s['role']==role and s['cycles']==cycle]
            q=[s for s in r['structures'] if s['role']==role and s['cycles']==cycle and s['position'] is not None]
            stats={m:protein_stats(ss,m) for m in ['spearman','top1_regret','regret_to_new_best','extra_regret_vs_teacher_old_choice','task_mae','top3_recall','top5_recall']}
            structural={}
            for m in ['all_atom_lddt','ca_lddt','ca_aligned_rmsd','local_ca_rmsd_global_frame','ca_pair_distance_rmse','contact_disagreement']:
                values=np.array([v[m] for v in q]);structural[m]=dict(protein=protein_stats(q,m),p95=float(np.quantile(values,.95)),p99=float(np.quantile(values,.99)),maximum=float(values.max()))
            parents={s['parent_index'] for s in ss};tm=[]
            for pi in sorted(parents):
                a=next(t for t in r['timings'] if t['parent_index']==pi and t['cycles']==cycle);b=next(t for t in r['timings'] if t['parent_index']==pi and t['cycles']==4)
                tm.append(dict(parent_index=pi,resident_ratio=a['resident_screen_seconds']/b['resident_screen_seconds'],first_use_ratio=a['first_use_screen_seconds']/b['first_use_screen_seconds'],resident_seconds=a['resident_screen_seconds'],trunk_seconds=a['trunk_seconds'],esm_seconds=a['esm_seconds'],score_seconds=a['screen_score_seconds']))
            groups[f'{role}:C{cycle}']=dict(sites=len(ss),proteins=len(parents),top1=sum(s['top1_match'] for s in ss),metrics=stats,structure=structural,instances=len(q),
                absolute_geometry_pass=sum(s['geometry']['zero_severe_strict_checked_chirality'] for s in q),new_failures=sum(s['new_failure'] for s in q),repaired_failures=sum(s['repaired_failure'] for s in q),
                local_above_1=sum(s['local_ca_rmsd_global_frame']>1 for s in q),selected_geometry=sum(s['selected_both_new_actual_geometry'] for s in ss),timing=tm,
                resident_geometric_mean_ratio=float(np.exp(np.mean(np.log([t['resident_ratio'] for t in tm])))))
    for name,rows in [('selection',selection),('timings',r['timings']),('wt_gt',r['wt_gt'])]:
        with (out/f'{name}.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (out/'summary.json').write_text(json.dumps(dict(complete=True,groups=groups,promotion=False),indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);summarize_native_budget(p.parse_args().root)
