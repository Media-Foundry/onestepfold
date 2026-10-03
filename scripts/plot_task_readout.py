"""Standalone plots for scalar-readout and archived-collapse development probes."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot_task_readout(out,collapse):
    plt.rcParams.update({'font.size':9,'figure.dpi':150,'axes.spines.top':False,'axes.spines.right':False})
    c=pd.read_csv(out/'learning.csv');fig,ax=plt.subplots(figsize=(8,4))
    for name,rows in c.groupby('method'):
        y=rows.groupby(['step','parent_index']).normalized_mse.mean().groupby('step').mean()
        ax.plot(y.index,y.values,marker='o',ls='--' if 'aa_only' in name else '-',label=name)
    ax.set(xlabel='Updates',ylabel='Train normalized task MSE (equal protein weight)',yscale='log')
    ax.legend(fontsize=7,ncol=2);fig.tight_layout();fig.savefig(out/'learning.png');plt.close(fig)
    g=pd.read_csv(out/'groups.csv');g=g[g.group=='unseen_protein'].set_index('method')
    methods=[f'{arm}_{kind}_s{seed}' for arm in ('restricted','expanded') for seed in (231301,231303) for kind in ('context','aa_only')]
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for ax,col,label in zip(axes,['rho','cross_regret'],['Four-noise mean-score Spearman','Old-select / new-evaluate regret']):
        ax.bar(np.arange(8),[g.loc[m,col] for m in methods],color=['#2166ac','#aaaaaa']*4)
        ax.axhline(g.loc['legacy_wt_z',col],color='#b2182b',ls='--',label='WT-z (oracle target s)')
        ax.set_xticks(np.arange(8),[m.replace('restricted','R').replace('expanded','E').replace('_s2313','_') for m in methods],rotation=45,ha='right')
        ax.set_ylabel(label);ax.legend(fontsize=8)
    fig.suptitle('16 development proteins / 32 held sites; higher rho and lower regret are different endpoints')
    fig.tight_layout();fig.savefig(out/'held_comparison.png');plt.close(fig)
    df=pd.read_csv(collapse/'layers.csv');keys=['query:0','mix:0','blocks.3:0','aa_readout:0','readout.0:0','readout.1:0','readout.2:0','readout.3:0']
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for job,step,label in [('expanded_s231301',0,'Initialization'),('expanded_s231301',32760,'Failed saved endpoint'),('expanded_s231303',32760,'Learning saved endpoint')]:
        rows=df[(df.job==job)&(df.step==step)&(df.parent_index==3)&(df.position==36)].set_index('layer')
        axes[0].plot(np.arange(len(keys)),np.maximum([rows.loc[k,'candidate_centered_rms'] for k in keys],1e-12),marker='o',label=label)
        axes[1].plot(np.arange(len(keys)),np.maximum([rows.loc[k,'gradient_norm'] for k in keys],1e-35),marker='o',label=label)
    for ax,ylabel in zip(axes,['Candidate-centered activation RMS (zero shown at 1e-12)','Activation gradient norm (zero shown at 1e-35)']):
        ax.set_xticks(np.arange(len(keys)),keys,rotation=40,ha='right');ax.set_ylabel(ylabel);ax.set_yscale('log')
    axes[0].legend(fontsize=7);fig.suptitle('Read-only 1W53 T37 probe; no optimizer updates')
    fig.tight_layout();fig.savefig(out/'collapse_path.png');plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--collapse',type=Path,required=True)
    a=p.parse_args();plot_task_readout(a.out,a.collapse)
