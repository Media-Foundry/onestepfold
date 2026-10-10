"""Plot only independently verified fixed-node results and accepted trajectories."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
read = lambda name: json.loads((root / name).read_text())
assert read('verification.json')['complete']
analysis, lock = read('analysis.json'), read('training_lock.json')
fig, axes = plt.subplots(1, 3, figsize=(13.2, 3.9), constrained_layout=True)
colors = {'adamw': '#0072B2', 'lbfgs': '#D55E00'}
for name, run in analysis['runs'].items():
    arm, seed = name.split('_')
    color, style = colors[arm], '-' if seed == '272001' else '--'
    label = f'{arm} / {seed}'
    states = run['optimization']['accepted_states']
    axes[0].plot([0] + [r['gradient_passes'] for r in states],
                 [lock['initial_objective']] + [r['after'] for r in states],
                 color=color, linestyle=style, label=label)
    for ax, role in zip(axes[1:], ['train', 'dev_unseen_protein']):
        ax.plot([n['step'] for n in run['nodes']],
                [n['latent'][role]['centered_nmse'] for n in run['nodes']],
                color=color, linestyle=style, marker='o', markersize=4)
for ax in axes:
    ax.set_xlabel('Full TRAIN gradient evaluations')
    ax.set_xticks([0, 32, 64, 96, 128])
    ax.grid(alpha=.2)
axes[0].set_title('TRAIN objective at returned states')
axes[0].set_ylabel('Site-weighted J')
axes[0].legend(fontsize=8, frameon=False)
axes[1].set_title('TRAIN AA residual (zoomed scale)')
axes[2].set_title('New-protein AA residual (zoomed scale)')
for ax in axes[1:]:
    ax.axhline(1, color='black', linewidth=.8, alpha=.65)
    ax.set_ylabel('Protein-weighted centered NMSE')
    ax.set_ylim(.98, 1.002)
fig.savefig(root / 'optimization_and_aa_response.png', dpi=180)
fig.savefig(root / 'optimization_and_aa_response.pdf')
plt.close(fig)
