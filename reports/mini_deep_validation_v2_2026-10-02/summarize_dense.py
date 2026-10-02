"""Final-only supplemental curves; original protocol summaries remain unchanged."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def summarize_dense():
    root=Path(__file__).resolve().parent/'whole_field_dense';assert json.loads((root/'execution.json').read_text())['complete'];rows=[];curves=[]
    for p in sorted((root/'runs').glob('*/report.json')):
        r=json.loads(p.read_text());assert r['complete'];j=r['job'];last=r['history'][-1];site=last['sites'][0]
        rows.append(dict(job=j['id'],lr=j['lr'],seed=j['seed'],parameters=r['parameters'],nmse=last['mean_nmse'],centered_nmse=last['centered_nmse'],energy=site['energy_ratio'],centered_energy=site['centered_energy_ratio'],seconds=r['seconds'],peak_bytes=r['peak_allocated_bytes']))
        for h in r['history']:curves.append(dict(job=j['id'],lr=j['lr'],seed=j['seed'],step=h['step'],nmse=h['mean_nmse'],centered_nmse=h['centered_nmse']))
    for name,data in [('terminal.csv',rows),('curves.csv',curves)]:
        with (root/name).open('w') as f:w=csv.DictWriter(f,fieldnames=data[0],lineterminator='\n');w.writeheader();w.writerows(data)
    fig,ax=plt.subplots(figsize=(7,4))
    for lr in [1e-4,3e-4,1e-3]:
        data=[[c for c in curves if c['lr']==lr and c['seed']==s] for s in [231301,231303]];x=[c['step'] for c in data[0]];y=np.array([[c['nmse'] for c in d] for d in data]);ax.plot(x,y.mean(0),marker='o',label=f'LR={lr:g}');ax.fill_between(x,y.min(0),y.max(0),alpha=.15)
    ax.axhline(.1,color='gray',ls='--',label='primary fitting gate');ax.set(yscale='log',xlabel='Updates, full 19-AA batch',ylabel='Normalized response MSE',title='Corrected whole-field dense: fresh zero readout, same one site');ax.legend();fig.tight_layout();fig.savefig(root/'learning_curves.png',dpi=180);plt.close(fig)


if __name__=='__main__':summarize_dense()
