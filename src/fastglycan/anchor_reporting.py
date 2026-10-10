"""Tables and publication artifacts for an already verified anchored trial."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from fastglycan.fullbatch_results import verify_fullbatch_history


def selection_detail_rows(score, control, seed):
    """Keep old-noise choice and new-noise teacher regret on distinct axes."""
    lookup={(r['site_key'],r['arm']):r for r in score['sites']}
    previous={r['site_key']:r for r in control['sites'] if r['arm']=='correct'}
    rows=[]
    for row in score['sites']:
        if row['arm']!='correct':continue
        site=row['site_key'];exact=np.asarray(lookup[site,'exact']['tasks'])
        first_noise=min(r['noise'] for r in score['outputs'] if r['site_key']==site)
        choices=[r['aa'] for r in score['outputs']
                 if (r['site_key'],r['arm'],r['noise'])==(site,'exact',first_noise)]
        assert len(set(choices))==len(choices)==exact.shape[1]
        methods={'anchor':row,'control':previous[site],
                 **{k:lookup[site,k] for k in ('disabled','exact','oracle_pair','mismatched') if (site,k) in lookup}}
        for name,pred in methods.items():
            scores=np.asarray(pred['tasks']);selected=int(np.argmin(scores[0]))
            assert choices[selected]==pred['old_selected']
            ordered=np.sort(scores[0],kind='stable')
            regret=float(exact[1,selected]-exact[1].min())
            assert np.isclose(regret,pred['old_select_new_regret'],rtol=1e-12,atol=1e-12)
            rows.append(dict(seed=seed,step=score['step'],role=row['role'],parent=row['parent'],pdb=row['pdb'],
                site=site,method=name,selected=choices[selected],
                predicted_old_margin=float(ordered[1]-ordered[0]),
                exact_old_regret=float(exact[0,selected]-exact[0].min()),
                exact_new_regret=regret,
                exact_old_choice=choices[int(np.argmin(exact[0]))],
                exact_new_choice=choices[int(np.argmin(exact[1]))]))
    return rows


def _write_table(path, rows):
    with path.open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def render_anchor_report(root, output):
    """Consume completed, hash-verified evidence; never select a checkpoint."""
    root,output=Path(root),Path(output)
    read=lambda p:json.loads(p.read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    verification,analysis=read(root/'verification.json'),read(root/'analysis.json')
    lock=read(root/'training_lock.json')
    assert verification['complete'] and analysis['complete']
    assert verification['lock_sha256']==sha(root/'training_lock.json')
    for name,digest in read(root/'manifest.json')['files'].items():assert sha(root/name)==digest,name
    post=read(root/'postprocess_manifest.json')
    assert post['complete']
    for name,digest in post['files'].items():assert sha(root/name)==digest,name
    assert analysis['primary_step']==128 and not analysis['promoted']
    summaries,choices,trajectories=[],[],{}
    for seed in lock['seeds']:
        run=analysis['runs'][str(seed)]
        control=root/'controls/adamw'/str(seed)
        old_history=[json.loads(x) for x in (control/'history.jsonl').read_text().splitlines()]
        old_report=read(control/'report.json');old_tensor=read(control/'tensor_verification.json')
        old_ledger=verify_fullbatch_history(old_history,lock,old_report,old_tensor['objectives'])
        trajectories[str(seed)]={'anchor':run['optimization'],'control':old_ledger}
        for node in run['nodes']:
            step=node['step']
            for role in node['summary']:
                methods={'anchor':node['summary'][role]['correct'],
                         'control':node['control_summary'][role]['correct'],
                         **{k:node['summary'][role][k] for k in ('disabled','oracle_pair','exact')}}
                for method,values in methods.items():
                    latent=node['latent'][role] if method=='anchor' else node['control_latent'][role] if method=='control' else {}
                    row=dict(seed=seed,step=step,role=role,method=method)
                    for key in ('parents','sites','outputs','spearman','centered_response_rmse','regret',
                                'regret_parent_median','regret_parent_max','top1','geometry_pass',
                                'disabled_pass_to_fail','disabled_fail_to_pass','severe_pairs','wrong_centres',
                                'local_p95','local_p99','local_max','local_over1'):
                        row[key]=values[key]
                    for key in ('raw_nmse','common_nmse','centered_nmse','centered_energy_ratio','centered_cosine','common_fraction'):
                        row['latent_'+key]=latent.get(key)
                    summaries.append(row)
            with gzip.open(root/f'runs/anchor/{seed}/scores_{step}.json.gz','rt') as f:score=json.load(f)
            with gzip.open(control/f'scores_{step}.json.gz','rt') as f:old_score=json.load(f)
            choices.extend(selection_detail_rows(score,old_score,seed))
    output.mkdir(parents=True,exist_ok=False)
    _write_table(output/'fixed_node_metrics.csv',summaries)
    _write_table(output/'selection_details.csv',choices)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'savefig.dpi':180,'figure.constrained_layout.use':True})
    colors={'anchor':'#167b9b','control':'#bb653c'}
    fig,axes=plt.subplots(2,2,figsize=(10,6.5))
    for column,seed in enumerate(lock['seeds']):
        for name,ledger in trajectories[str(seed)].items():
            initial=ledger['gradient_trials'][0]
            states=ledger['accepted_states']
            x=[0]+[s['gradient_passes'] for s in states]
            axes[0,column].plot(x,[initial['raw']]+[s['after'] for s in states],color=colors[name],label=name)
            # Terminal centered loss was not recorded in the accepted-state ledger.
            known=[s for s in states if s['after_centered'] is not None]
            axes[1,column].plot([0]+[s['gradient_passes'] for s in known],
                [initial['centered']]+[s['after_centered'] for s in known],color=colors[name],label=name)
        axes[0,column].set_title(f'Seed {seed}')
        axes[0,column].set_ylabel('Full TRAIN objective (site weighted)')
        axes[1,column].set_ylabel('Centered TRAIN objective (site weighted)')
        for ax in axes[:,column]:ax.set_xlabel('Full-gradient updates');ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Matched candidate exposure; reference-anchor work is additional')
    for ext in ('png','pdf'):fig.savefig(output/f'optimization.{ext}')
    plt.close(fig)

    roles=sorted({r['role'] for r in summaries if r['method']=='anchor'})
    fig,axes=plt.subplots(len(roles),2,figsize=(10,3*len(roles)),squeeze=False)
    for column,seed in enumerate(lock['seeds']):
        for ri,role in enumerate(roles):
            ax=axes[ri,column]
            for method in ('anchor','control'):
                rows=[r for r in summaries if (r['seed'],r['role'],r['method'])==(seed,role,method)]
                ax.plot([r['step'] for r in rows],[r['latent_centered_nmse'] for r in rows],
                        marker='o',color=colors[method],label=method)
            ax.axhline(1,color='#555555',linestyle=':',label='zero residual')
            ax.set_title(f'{role} / seed {seed}');ax.set_ylabel('AA residual NMSE (protein weighted)')
            ax.set_xlabel('Fixed update');ax.grid(alpha=.2);ax.legend()
    fig.suptitle('All fixed checkpoints; 128 is the primary endpoint')
    for ext in ('png','pdf'):fig.savefig(output/f'latent_aa_recovery.{ext}')
    plt.close(fig)

    metrics=[('spearman','Spearman'),('centered_response_rmse','AA distance response RMSE (Å)'),
             ('regret','Old-select / new-evaluate raw regret'),('geometry_pass','Checked geometry passes')]
    # Keep the source contract's explicit development role names.
    held='dev_unseen_protein'
    assert held in roles,roles
    fig,axes=plt.subplots(4,2,figsize=(10,10))
    for column,seed in enumerate(lock['seeds']):
        for ri,(field,label) in enumerate(metrics):
            ax=axes[ri,column]
            for method in ('anchor','control','disabled','oracle_pair'):
                rows=[r for r in summaries if (r['seed'],r['role'],r['method'])==(seed,held,method)]
                ax.plot([r['step'] for r in rows],[r[field] for r in rows],marker='o' if method in colors else None,
                    color=colors.get(method, '#555555' if method=='disabled' else '#58914b'),
                    linestyle='-' if method in colors else '--',label=method)
            ax.set_ylabel(label);ax.set_xlabel('Fixed update');ax.grid(alpha=.2)
            if ri==0:ax.set_title(f'Seed {seed}');ax.legend()
    fig.suptitle('New-protein development panel; quality axes are separate')
    for ext in ('png','pdf'):fig.savefig(output/f'held_quality.{ext}')
    plt.close(fig)
    manifest=dict(complete=True,source_lock_sha256=sha(root/'training_lock.json'),
        source_analysis_sha256=sha(root/'analysis.json'),primary_step=128,
        equal_candidate_exposure=True,equal_compute=False,all_panels_development=True,
        rows=dict(metrics=len(summaries),selection=len(choices)),
        files={p.name:sha(p) for p in output.iterdir() if p.is_file()})
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
