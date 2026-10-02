"""Standalone descriptive figures for the locked coverage experiment."""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot_pair_coverage(out):
    plt.rcParams.update({'font.size':9,'figure.dpi':140,'axes.spines.top':False,'axes.spines.right':False})
    curves=pd.read_csv(out/'learning_curve.csv')
    fig,ax=plt.subplots(figsize=(7,4))
    for arm,g in curves.groupby('arm'):
        p=g.groupby(['step','parent_index']).nmse.mean().groupby('step').mean()
        ax.plot(p.index,p.values,marker='o',label=arm)
    ax.set(xlabel='Total updates (same budget in both arms)',ylabel='Train NMSE (equal protein weight)',ylim=(0,1.1))
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(out/'learning_curve.png');plt.close(fig)
    s=pd.read_csv(out/'selection.csv')
    s=s[(s.reference=='baseline')&(s.noise_group=='all')&s.common_holdout&(~s.parent_index.isin([3,4,5,7,12,18,19,22]))]
    fig,axes=plt.subplots(2,2,figsize=(9,8),sharex=True,sharey=True)
    for ax,arm in zip(axes.flat,['restricted_s231301','restricted_s231303','expanded_s231301','expanded_s231303']):
        x=s[s.arm=='wt_z'].set_index(['parent_index','position_1based'])
        y=s[s.arm==arm].set_index(['parent_index','position_1based']).loc[x.index]
        for label,aa,color in [('Covered in both','TYAN','#2166ac'),('Newly covered','DLVI','#d6604d'),('Uncovered in both','CEFGHKMPQRSW','#777777')]:
            keep=x.source_aa.isin(list(aa));ax.scatter(x[keep].spearman,y[keep].spearman,color=color,label=label,s=25,alpha=.8)
        ax.plot([-1,1],[-1,1],color='black',lw=.7,ls='--');ax.set(title=arm,xlim=(-1,1),ylim=(-1,1),xlabel='WT-z Spearman',ylabel='Student Spearman')
    axes[0,0].legend(fontsize=7);fig.suptitle('32 held sites / 16 proteins; four-noise mean scores\nDevelopment panel; points are not independent proteins',fontsize=10)
    fig.tight_layout();fig.savefig(out/'unseen_site_ranking.png');plt.close(fig)
    d=pd.read_csv(out/'prior_polar.csv');fig,axes=plt.subplots(1,2,figsize=(9,3.8),sharex=True,sharey=True)
    for ax,seed in zip(axes,[231301,231303]):
        g=d[d.arm==f'e8192_s{seed}']
        for role,color in [('train','#2166ac'),('unseen_site','#fdae61'),('unseen_protein','#b2182b')]:
            r=g[g.role==role];ax.scatter(r.cosine,r.amplitude_ratio,s=12,color=color,alpha=.7,label=role)
        c=np.linspace(0,1,100);ax.plot(c,2*c,ls='--',color='gray',lw=.7,label='NMSE = 1 boundary')
        ax.set(title=f'Prior endpoint {seed}',xlabel='Direction cosine',ylabel='Predicted / teacher norm',xlim=(-.15,1.02),ylim=(0,2.5))
    axes[0].legend(fontsize=7);fig.tight_layout();fig.savefig(out/'prior_amplitude_direction.png');plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    plot_pair_coverage(p.parse_args().out)
