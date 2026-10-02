"""Final readout summaries, keeping raw versus R32-label errors and references apart."""
import csv,gzip,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def summarize_readouts():
    root=Path(__file__).resolve().parent
    def read(p):return json.loads(p.read_text())
    assert read(root/'execution.json')['complete'];plan=read(root/'planned_jobs.json');terminal=[];curves=[];aa=[]
    for job in plan['single']+plan['multi']:
        r=read(root/'runs'/job['id']/'report.json');assert r['complete'];last=r['history'][-1]
        terminal.append(dict(job=job['id'],phase=job['phase'],architecture=job['architecture'],target=job['label'],seed=job['seed'],parameters=r['parameters'],raw_nmse=last['raw_nmse'],label_nmse=last['label_nmse'],raw_centered_nmse=float(np.mean([x['raw']['centered_nmse'] for x in last['sites']])),raw_energy=float(np.mean([x['raw']['energy_ratio'] for x in last['sites']])),raw_centered_energy=float(np.mean([x['raw']['centered_energy_ratio'] for x in last['sites']])),seconds=r['seconds'],head20_median_seconds=float(np.median(r['head20_forward_seconds'])),peak_bytes=r['peak_allocated_bytes']))
        for h in r['history']:
            curves.append(dict(job=job['id'],phase=job['phase'],architecture=job['architecture'],target=job['label'],seed=job['seed'],step=h['step'],raw_nmse=h['raw_nmse'],label_nmse=h['label_nmse']))
            for site in h['sites']:
                for index,(raw,label) in enumerate(zip(site['raw']['nmse'],site['label']['nmse'])):aa.append(dict(job=job['id'],step=h['step'],parent=site['parent_index'],position_zero=site['position'],candidate_index=index,raw_nmse=raw,label_nmse=label))
    for filename,data in [('terminal.csv',terminal),('curves.csv',curves),('per_aa.csv',aa)]:
        with (root/filename).open('w') as f:w=csv.DictWriter(f,fieldnames=data[0],lineterminator='\n');w.writeheader();w.writerows(data)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,label in zip(axes,['raw','r32']):
        for kind in ['free_hidden','pair','channel']:
            rows=[[r for r in curves if r['phase']=='single' and r['architecture']==kind and r['target']==label and r['seed']==seed] for seed in [231301,231303]];x=[r['step'] for r in rows[0]];y=np.array([[r['label_nmse'] for r in rs] for rs in rows]);ax.plot(x,y.mean(0),label=kind,marker='.');ax.fill_between(x,y.min(0),y.max(0),alpha=.15)
        ax.set(xlabel='Updates (19-AA batch)',ylabel='MSE normalized to the trained matrix target',title='Raw hard target' if label=='raw' else 'Oracle R32 matrix target');ax.legend();ax.set_ylim(bottom=0)
    fig.tight_layout();fig.savefig(root/'learning_curves.png',dpi=180);plt.close(fig)
    with gzip.open(root/'functional/closure/report.json.gz','rt') as f:d=json.load(f)
    summary={}
    for arm in read(root/'functional/closure/lock.json')['arms']:
        rows=[x for s in d['sites'] for x in s['outputs'] if x['arm']==arm and not x['is_wt']];result={}
        for ref in ['exact','baseline']:
            ranking=[x for s in d['sites'] for x in s['ranking'] if x['arm']==arm and x['reference']==ref and not x['includes_wt']]
            if ranking:result[ref]=dict(spearman=float(np.mean([x['spearman'] for x in ranking])),top1=sum(x['top1_match'] for x in ranking),n=len(ranking),regret=float(np.mean([x['top1_regret'] for x in ranking])))
        rms=np.array([x['compression_fidelity']['local_ca_rmsd_global_frame'] for x in rows]);result.update(raw_instances=len(rows),local_vs_baseline=dict(mean=float(rms.mean()),p95=float(np.quantile(rms,.95)),p99=float(np.quantile(rms,.99)),max=float(rms.max()),over1=int((rms>1).sum())),new_geometry_vs_baseline=sum(x['new_compression_chemistry_failure'] for x in rows),geometry_pass=sum(x['geometry']['zero_severe_strict_checked_chirality'] for x in rows),aa_lddt_vs_baseline=float(np.mean([x['compression_fidelity']['all_atom_lddt'] for x in rows])))
        summary[arm]=result
    (root/'functional_summary.json').write_text(json.dumps(summary,indent=2)+'\n')


if __name__=='__main__':summarize_readouts()
