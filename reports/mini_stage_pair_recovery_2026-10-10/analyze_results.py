"""All fixed nodes, equal-parent summaries, and paired final-versus-hint effects."""
import gzip,json
from pathlib import Path
import numpy as np
from fastglycan.reference_editor_metrics import paired_parent_interval


def analyze_stage_results(root, *, interim=False):
    runs={};comparisons={}
    for cohort in (('n1',) if interim else ('n1','n15')):
        lock=json.loads((root/cohort/'training_lock.json').read_text())
        for arm in ('final','hint'):
            for seed in (272001,272003):
                folder=root/cohort/'runs'/arm/str(seed)
                report=json.loads((folder/'report.json').read_text())
                history=[json.loads(line) for line in (folder/'history.jsonl').read_text().splitlines()]
                nodes=[]
                for step in lock['checkpoints']:
                    ev=json.loads((folder/f'evaluation_{step}.json').read_text())
                    with gzip.open(folder/f'scores_{step}.json.gz','rt') as f:score=json.load(f)
                    pooled={}
                    for role in sorted({r['role'] for r in ev['latent']}):
                        rr=[r for r in ev['latent'] if r['role']==role];parents=[]
                        for parent in sorted({r['parent'] for r in rr}):
                            pp=[r for r in rr if r['parent']==parent];row=dict(parent=parent,sites=len(pp))
                            for mode in ('raw','common','centered'):
                                for field in ('nmse','energy_ratio','cosine'):
                                    v=[r['moments'][mode][field] for r in pp if r['moments'][mode][field] is not None]
                                    row[f'{mode}_{field}']=float(np.mean(v)) if v else None
                            row['common_fraction']=float(np.mean([r['moments']['common']['predicted_energy']/r['moments']['raw']['predicted_energy'] for r in pp])) if step else None
                            if step==8208:row['mismatch_centered_nmse']=float(np.mean([r['mismatch']['centered']['nmse'] for r in pp]))
                            if role=='train':row['hint_centered_nmse']=float(np.mean([r['hint_moments']['centered']['nmse'] for r in pp]))
                            parents.append(row)
                        summary=dict(parents=len(parents),sites=len(rr),parent_summaries=parents)
                        for key in parents[0]:
                            if key in ('parent','sites'):continue
                            values=[r[key] for r in parents if r[key] is not None]
                            summary[key]=float(np.mean(values)) if values else None
                        pooled[role]=summary
                    lookup={(r['site_key'],r['arm']):r for r in score['sites']};choices=[]
                    for row in score['sites']:
                        if row['arm']!='correct':continue
                        base=lookup[row['site_key'],'disabled'];oracle=lookup[row['site_key'],'oracle_pair']
                        choice=dict(site=row['site_key'],pdb=row['pdb'],role=row['role'],aa=row['old_selected'],
                                    baseline_aa=base['old_selected'],oracle_aa=oracle['old_selected'],
                                    regret=row['old_select_new_regret'],baseline_regret=base['old_select_new_regret'],
                                    regret_change=row['old_select_new_regret']-base['old_select_new_regret'])
                        if step==8208:
                            wrong=lookup[row['site_key'],'mismatched'];choice.update(mismatch_aa=wrong['old_selected'],mismatch_regret=wrong['old_select_new_regret'])
                        choices.append(choice)
                    nodes.append(dict(step=step,latent=pooled,summary=score['summary'],contrasts=score['contrasts'],choices=choices))
                chunks=[]
                for end in range(304,8209,304):
                    hh=history[end-304:end]
                    chunks.append(dict(step=end,objective=float(np.mean([r['loss'] for r in hh])),
                        final_loss=float(np.mean([p['final'] for r in hh for p in r['loss_parts']])),
                        clipped=sum(r['clipped'] for r in hh)))
                runs[f'{cohort}_{arm}_{seed}']=dict(nodes=nodes,learning_chunks=chunks,clipped_total=sum(r['clipped'] for r in history),
                    seconds=report['seconds'],peak_allocated_bytes=report['peak_allocated_bytes'],first_gradient=report['gradient_audits'][0])
        for seed in (272001,272003):
            a=runs[f'{cohort}_hint_{seed}']['nodes'][-1];b=runs[f'{cohort}_final_{seed}']['nodes'][-1]
            for role in a['summary']:
                if cohort=='n15':
                    comparisons[f'{cohort}_{seed}_{role}']={field:paired_parent_interval(
                        a['summary'][role]['correct']['parent_summaries'],b['summary'][role]['correct']['parent_summaries'],field)
                        for field in ('spearman','regret','centered_response_rmse')}
                else:
                    comparisons[f'{cohort}_{seed}_{role}']={field:a['summary'][role]['correct'][field]-b['summary'][role]['correct'][field]
                        for field in ('spearman','regret','centered_response_rmse')}
    result=dict(complete=True,runs=runs,hint_minus_final=comparisons,all_panels_development=True,promoted=False,
                analyzed_cohorts=['n1'] if interim else ['n1','n15'],scientific_experiment_complete=not interim)
    (root/('analysis_interim.json' if interim else 'analysis.json')).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('ANALYZED',len(runs),'runs')


if __name__=='__main__':
    root=Path(__file__).resolve().parent
    analyze_stage_results(root,interim=not (root/'manifest.json').exists())
