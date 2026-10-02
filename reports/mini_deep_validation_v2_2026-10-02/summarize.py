"""Final-only aggregation of all preregistered arms; no holdout selection."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_text())

def summarize():
    assert read(ROOT/'execution.json')['complete']
    plan=read(ROOT/'planned_jobs.json');rows=[];curves=[];peraa=[]
    for job in plan['A']+plan['B']:
        report=read(ROOT/'runs'/job['id']/'report.json');assert report['complete'];last=report['history'][-1];site=last['sites'][0];arch=job['architecture']
        family='free' if job['kind']=='free' else ('dense' if arch.get('output')=='dense' else arch.get('size','small')+'_'+('content' if arch.get('content') else 'bias'))
        row=dict(job=job['id'],phase=job['phase'],family=family,input=arch.get('input_mode','none'),lr=job['lr'],seed=job['seed'],parameters=report['parameters'],nmse=last['mean_nmse'],centered_nmse=last['centered_nmse'],energy=site['energy_ratio'],centered_energy=site['centered_energy_ratio'],oracle_floor=np.mean(report['oracle_floors'][0]['nmse']),seconds=report['seconds'],peak_bytes=report['peak_allocated_bytes'],primary=last['mean_nmse']<=.1,secondary=last['mean_nmse']<=.12)
        rows.append(row)
        for h in report['history']:
            m=h['sites'][0];curves.append(dict(job=job['id'],step=h['step'],nmse=h['mean_nmse'],centered_nmse=h['centered_nmse'],energy=m['energy_ratio'],centered_energy=m['centered_energy_ratio'],seconds=h['seconds']))
            for a,value in enumerate(m['nmse']):peraa.append(dict(job=job['id'],step=h['step'],candidate_index=a,nmse=value))
    for filename,table in [('terminal.csv',rows),('curves.csv',curves),('per_aa.csv',peraa)]:
        with (ROOT/filename).open('w') as f:w=csv.DictWriter(f,fieldnames=table[0],lineterminator='\n');w.writeheader();w.writerows(table)
    families=['free','small_bias','large_bias','small_content','large_content','dense'];aggregate={}
    for family in families:
        group=[r for r in rows if r['phase']=='A' and r['family']==family];aggregate[family]={}
        for lr in sorted({r['lr'] for r in group}):
            g=[r for r in group if r['lr']==lr];aggregate[family][str(lr)]=dict(mean=np.mean([r['nmse'] for r in g]),seeds=[r['nmse'] for r in g],centered=[r['centered_nmse'] for r in g],energy=[r['energy'] for r in g],centered_energy=[r['centered_energy'] for r in g],primary_both=all(r['primary'] for r in g),parameters=g[0]['parameters'])
    oracle={mode:[r for r in rows if r['phase']=='B' and r['input']==mode] for mode in ['wt','site','full']}
    (ROOT/'derived_summary.json').write_text(json.dumps(dict(A=aggregate,B=oracle,decisions=read(ROOT/'decisions.json')),indent=2)+'\n')
    fig,ax=plt.subplots(figsize=(8,4.5))
    for family in families:
        jobs=[r['job'] for r in rows if r['phase']=='A' and r['family']==family and (r['lr']==3e-4 or family=='free')];values=[]
        for job in jobs:
            data=[c for c in curves if c['job']==job];x=np.array([c['step'] for c in data]);values.append([c['nmse'] for c in data])
        y=np.array(values);ax.plot(x,y.mean(0),marker='.',label=family);ax.fill_between(x,y.min(0),y.max(0),alpha=.12)
    ax.axhline(.1,color='gray',ls='--',label='student primary gate');ax.axhline(rows[0]['oracle_floor'],color='k',ls=':',label='oracle R32 floor');ax.set(xlabel='Continuous updates (19-AA batch)',ylabel='Full-response normalized MSE',title='Single-site continuous fitting; neural LR=3e-4, free LR=0.01');ax.legend(ncol=2,fontsize=8);fig.tight_layout();fig.savefig(ROOT/'learning_curves.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(9,3.8))
    for family in families[1:]:
        g=aggregate[family];x=np.array([float(k) for k in g]);y=np.array([v['mean'] for v in g.values()]);axes[0].plot(x,y,marker='o',label=family)
    axes[0].set(xscale='log',xlabel='Learning rate',ylabel='8192-step mean NMSE',title='Frozen LR grid');axes[0].legend(fontsize=7)
    for i,mode in enumerate(oracle):
        y=[r['nmse'] for r in oracle[mode]];axes[1].bar(i,np.mean(y));axes[1].scatter([i]*2,y,color='black',s=12)
    axes[1].set(xticks=range(3),xticklabels=['WT inputs','Target site','Full target'],ylabel='8192-step mean NMSE',title='Matched large-content input adapter')
    for ax in axes:ax.axhline(.1,color='gray',ls='--')
    fig.tight_layout();fig.savefig(ROOT/'controls.png',dpi=180);plt.close(fig)

if __name__=='__main__':summarize()
