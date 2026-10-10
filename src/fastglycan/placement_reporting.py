"""Standalone scientific tables and figures for verified placement results."""
import csv
import json
from pathlib import Path

from fastglycan.fullbatch_results import _json, _sha


def render_placement_results(root, output):
    root,output=Path(root),Path(output)
    lock=_json(root/'training_lock.json');analysis=_json(root/'analysis.json')
    verification=_json(root/'verification.json')
    assert analysis['complete'] and verification['complete'] and analysis['primary_step']==128
    assert analysis['lock_sha256']==verification['lock_sha256']==_sha(root/'training_lock.json')
    assert not analysis['promoted'] and analysis['equal_trainable_parameters'] and not analysis['equal_compute']
    output.mkdir(parents=True,exist_ok=False)
    summaries=[];selections=[];contributions=[];geometry=[];trajectory=[]
    for seed in lock['seeds']:
        run=analysis['runs'][str(seed)]
        for arm,ledger in run['optimization'].items():
            trajectory.extend(dict(seed=seed,method=arm,**row) for row in ledger['states'])
        for node in run['nodes']:
            step=node['step'];selections.extend(node['selection_details'])
            contributions.extend(dict(seed=seed,step=step,**row) for row in node['choices'])
            for role,detail in node['geometry'].items():
                geometry.extend(dict(seed=seed,step=step,role=role,**row) for row in detail['parents'])
            for role in node['summary']['early']:
                methods={arm:node['summary'][arm][role]['correct'] for arm in lock['arms']}
                methods.update({k:node['summary']['early'][role][k] for k in ('disabled','oracle_pair','exact')})
                if step==128:
                    methods.update({arm+'_mismatched':node['summary'][arm][role]['mismatched'] for arm in lock['arms']})
                for method,value in methods.items():
                    row=dict(seed=seed,step=step,role=role,method=method)
                    for field in ('parents','sites','outputs','spearman','centered_response_rmse','regret',
                        'regret_parent_median','regret_parent_max','top1','geometry_pass','disabled_pass_to_fail',
                        'disabled_fail_to_pass','severe_pairs','wrong_centres','aa_lddt','local_p95','local_p99','local_max','local_over1'):
                        row[field]=value[field]
                    latent=node['latent'][method][role] if method in lock['arms'] else {}
                    for field in ('raw_nmse','common_nmse','centered_nmse','centered_energy_ratio','centered_cosine','common_fraction'):
                        row['latent_'+field]=latent.get(field)
                    summaries.append(row)

    def write(name,rows):
        with (output/name).open('x',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    for name,rows in [('fixed_node_metrics.csv',summaries),('selection_details.csv',selections),
                     ('regret_contributions.csv',contributions),('geometry_transitions.csv',geometry),
                     ('optimization_states.csv',trajectory)]:write(name,rows)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.constrained_layout.use':True,'savefig.dpi':180})
    colors={'late':'#bb653c','early':'#167b9b','disabled':'#555555','oracle_pair':'#58914b'}
    def save(fig,name):
        for ext in ('png','pdf'):fig.savefig(output/f'{name}.{ext}')
        plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(10,6.5))
    for col,seed in enumerate(lock['seeds']):
        for method in lock['arms']:
            rows=[r for r in trajectory if r['seed']==seed and r['method']==method]
            for ri,field in enumerate(('raw','centered')):
                valid=[r for r in rows if r[field] is not None]
                axes[ri,col].plot([r['state_step'] for r in valid],[r[field] for r in valid],color=colors[method],label=method)
        axes[0,col].set_title(f'Seed {seed}')
        for ri,label in enumerate(('Full TRAIN objective','AA-centered TRAIN objective')):
            axes[ri,col].set_xlabel('Completed full-gradient updates');axes[ri,col].set_ylabel(label)
            axes[ri,col].grid(alpha=.2);axes[ri,col].legend()
    fig.suptitle('Same trainable parameter count and exposure; different frozen computation')
    save(fig,'optimization')

    roles=sorted({r['role'] for r in summaries})
    fig,axes=plt.subplots(len(roles),2,figsize=(10,3*len(roles)),squeeze=False)
    for col,seed in enumerate(lock['seeds']):
        for ri,role in enumerate(roles):
            ax=axes[ri,col]
            for method in lock['arms']:
                rows=[r for r in summaries if (r['seed'],r['role'],r['method'])==(seed,role,method)]
                ax.plot([r['step'] for r in rows],[r['latent_centered_nmse'] for r in rows],marker='o',color=colors[method],label=method)
            ax.axhline(1,color='#555555',linestyle=':',label='zero correction')
            ax.set_title(f'{role} / seed {seed}');ax.set_ylabel('AA pair residual NMSE (protein weighted)')
            ax.set_xlabel('Fixed update');ax.grid(alpha=.2);ax.legend()
    fig.suptitle('All fixed nodes; update 128 is primary')
    save(fig,'pair_response')

    held='dev_unseen_protein';assert held in roles
    metrics=[('spearman','Mean-score Spearman'),('centered_response_rmse','AA distance response RMSE (Å)'),
             ('regret','Old-select / new-evaluate raw regret'),('geometry_pass','Checked geometry passes')]
    fig,axes=plt.subplots(4,2,figsize=(10,10))
    for col,seed in enumerate(lock['seeds']):
        for ri,(field,label) in enumerate(metrics):
            ax=axes[ri,col]
            for method in ('late','early','disabled','oracle_pair'):
                rows=[r for r in summaries if (r['seed'],r['role'],r['method'])==(seed,held,method)]
                ax.plot([r['step'] for r in rows],[r[field] for r in rows],color=colors[method],
                        linestyle='-' if method in lock['arms'] else '--',marker='o' if method in lock['arms'] else None,label=method)
            ax.set_ylabel(label);ax.set_xlabel('Fixed update');ax.grid(alpha=.2)
            if ri==0:ax.set_title(f'Seed {seed}');ax.legend()
    fig.suptitle('Reused new-protein development panel: distinct quality and risk measures')
    save(fig,'development_quality')
    manifest=dict(complete=True,source_analysis_sha256=_sha(root/'analysis.json'),primary_step=128,
        all_panels_development=True,equal_compute=False,inference_speedup_measured=False,
        rows=dict(metrics=len(summaries),selections=len(selections),contributions=len(contributions),geometry=len(geometry)),
        files={p.name:_sha(p) for p in output.iterdir() if p.is_file()})
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
