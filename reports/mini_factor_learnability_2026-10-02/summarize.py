"""Recompute tables/figures from complete locked reports, no model selection."""
import csv,gzip,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_text())

def summarize():
    memory=[load(p) for p in sorted(ROOT.glob('stage_*/report.json'))]
    audit=load(ROOT/'memorization_audit.json');byrun={r['run']:r for r in audit['checkpoint_replays']};rows=[]
    for report in memory:
        index=next(p.parent.name for p in ROOT.glob('stage_*/report.json') if load(p)['seed']==report['seed'] and load(p)['arm']==report['arm'])
        h=report['history'][-1];a=byrun[index]
        rows.append(dict(arm=report['arm'],seed=report['seed'],updates=h['step'],nmse=h['mean_nmse'],oracle_floor=np.mean(report['sites'][0]['oracle_floor']),factor_loss=h['sites'][0]['factor_loss'],centered_nmse=a['centered_response_relative_squared_error'],shared_mean_nmse=a['shared_mean_relative_squared_error'],nmse_min=a['nmse_range'][0],nmse_max=a['nmse_range'][1],parameters=report['parameters'],seconds=report['seconds'],peak_bytes=report['peak_allocated_bytes']))
    with (ROOT/'memorization.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
    with gzip.open(ROOT/'sparse/report.json.gz','rt') as f:report=json.load(f)
    mut=[m for w in report['workers'] for p in w['parents'] for s in p['sites'] for m in s['mutants']]
    transition=load(ROOT/'sparse_audit.json')['geometry_transitions'];summary=report['summary'];out=[];per_protein={};rng=np.random.default_rng(231501)
    parents=sorted({s['parent_index'] for s in report['sites']});boot=rng.integers(0,len(parents),(10000,len(parents)));paired={}
    for arm in ['oracle_r32','rowcol','contact','top_row_budget','top_contact_budget']:
        m=summary[arm];size=[x['evidence']['representation_fraction'][arm] for x in mut];nmse=[x['evidence']['latent_nmse'][arm] for x in mut];t=transition.get(arm,{'fixed_r32_failures':[],'new_failures_relative_r32':[]})
        out.append(dict(arm=arm,latent_nmse=np.mean(nmse),storage_mean=np.mean(size),storage_min=min(size),storage_max=max(size),rho=m['ranking']['spearman'],top1=m['top1_count'],regret=m['ranking']['top1_regret'],local_mean=m['local_mean'],local_max=m['local_max'],geometry_pass=m['geometry_pass'],new_geometry_vs_baseline=m['new_geometry_vs_baseline'],fixed_of_original13=len(t['fixed_r32_failures']),new_vs_r32=len(t['new_failures_relative_r32'])))
        per_protein[arm]={}
        for pi in parents:
            sites=[s for s in report['sites'] if s['parent_index']==pi];ranks=[r for s in sites for r in s['ranking'] if r['arm']==arm and r['reference']=='exact' and not r['includes_wt']];outputs=[r for s in sites for r in s['outputs'] if r['arm']==arm and not r['is_wt']]
            per_protein[arm][str(pi)]=dict(pdb_id=sites[0]['pdb_id'],spearman=np.mean([r['spearman'] for r in ranks]),top1=sum(r['top1_match'] for r in ranks),new_geometry=sum(r['new_compression_chemistry_failure'] for r in outputs),local_mean=np.mean([r['fidelity']['local_ca_rmsd_global_frame'] for r in outputs]))
        delta=np.array([per_protein[arm][str(p)]['spearman']-per_protein['oracle_r32'][str(p)]['spearman'] for p in parents]);paired[arm]=dict(rho_delta_mean=delta.mean(),protein_bootstrap95=np.quantile(delta[boot].mean(1),[.025,.975]).tolist())
    with (ROOT/'sparse_oracle.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=out[0],lineterminator='\n');w.writeheader();w.writerows(out)
    (ROOT/'derived_summary.json').write_text(json.dumps(dict(memory=rows,sparse=out,per_protein=per_protein,paired_vs_r32=paired),indent=2)+'\n')
    fig,ax=plt.subplots(figsize=(7,4))
    for arm,label,color in [('reconstruction','Shared network: reconstruction','#0072B2'),('canonical','Shared network: canonical factors','#D55E00'),('free_factors','Independent factor table (control)','#009E73')]:
        runs=[r for r in memory if r['arm']==arm];x=[h['step'] for h in runs[0]['history']];y=np.array([[h['mean_nmse'] for h in r['history']] for r in runs]);ax.plot(x,y.mean(0),label=label,color=color);ax.fill_between(x,y.min(0),y.max(0),alpha=.2,color=color)
    ax.axhline(rows[0]['oracle_floor'],color='k',linestyle=':',label='Oracle R32 floor');ax.axhline(.1,color='gray',linestyle='--',label='Predeclared ladder threshold')
    ax.set(xlabel='Updates (all 19 candidates per update)',ylabel='Mean normalized full response MSE',title='1W53 site 37: latent-only memorization, two seeds');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(ROOT/'memorization.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(9,3.5));names=['R32','+ row/col','+ contact','+ top(row budget)','+ top(contact budget)']
    axes[0].bar(names,[x['new_geometry_vs_baseline'] for x in out],color='#D55E00');axes[0].set(ylabel='New failures vs baseline / 608',ylim=(0,16))
    axes[1].bar(names,[x['top1'] for x in out],color='#0072B2');axes[1].set(ylabel='Top-1 agreement / 32',ylim=(0,32))
    for ax in axes:ax.tick_params(axis='x',rotation=30)
    fig.suptitle('Oracle sparse residuals: ranking gains do not clear geometry failures');fig.tight_layout();fig.savefig(ROOT/'sparse_oracle.png',dpi=180);plt.close(fig)

if __name__=='__main__':summarize()
