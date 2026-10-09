"""Completed single-site results only; no pending joint results are plotted."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
data=json.loads((root/'analysis_interim.json').read_text())
old=json.loads((root.parent/'mini_pair_candidate_fit_2026-10-10/analysis.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(10,4.1),constrained_layout=True)
for arm,colour in [('final','#235c9e'),('hint','#d06a24')]:
    for seed,style in [(272001,'-'),(272003,'--')]:
        nodes=data['runs'][f'n1_{arm}_{seed}']['nodes']
        axes[0].plot([x['step'] for x in nodes],[x['latent']['train']['centered_nmse'] for x in nodes],
                     style,marker='o',markersize=4,color=colour,label=f'{arm}, {seed}')
        axes[1].plot([x['step'] for x in nodes],[x['summary']['train']['correct']['centered_response_rmse'] for x in nodes],
                     style,marker='o',markersize=4,color=colour,label=f'{arm}, {seed}')
for init in ('pretrained','random'):
    points=[old['runs'][f'{init}_{s}']['nodes'][-1] for s in (272001,272003)]
    axes[0].scatter([8208]*2,[x['latent']['centered']['nmse'] for x in points],marker='x',color='#666666',s=40,
                    label='Previous appended model' if init=='pretrained' else None)
    axes[1].scatter([8208]*2,[x['summary']['correct']['centered_response_rmse'] for x in points],marker='x',color='#666666',s=40)
axes[0].axhline(1,color='#999999',linestyle=':')
axes[1].axhline(nodes[0]['summary']['train']['disabled']['centered_response_rmse'],color='#999999',linestyle=':',label='No correction')
axes[1].axhline(nodes[0]['summary']['train']['oracle_pair']['centered_response_rmse'],color='#539c55',linestyle=':',label='Oracle pair')
axes[0].set_ylabel('AA residual NMSE (lower is better)')
axes[1].set_ylabel('AA structure-response RMSE / Å')
for ax in axes:
    ax.set_xlabel('Updates; all fixed nodes shown')
    ax.grid(alpha=.2);ax.set_xlim(-100,8500);ax.legend(fontsize=8)
fig.suptitle('1W53 T37 TRAIN fit: same 8208-update budget, no transfer claim')
fig.savefig(root/'single_site_curve.png',dpi=170)
fig.savefig(root/'single_site_curve.pdf')
