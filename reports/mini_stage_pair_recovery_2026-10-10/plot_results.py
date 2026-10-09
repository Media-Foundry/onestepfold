"""Plot every locked node, with historical same-cohort endpoints for context."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
data = json.loads((root/'analysis.json').read_text())
old_single = json.loads((root.parent/'mini_pair_candidate_fit_2026-10-10/analysis.json').read_text())
old_joint = json.loads((root.parent/'mini_pair_recovery_2026-10-09/analysis.json').read_text())
fig, axes = plt.subplots(2, 3, figsize=(13, 7.5), constrained_layout=True)
for col, (cohort, role, title) in enumerate([
        ('n1', 'train', 'Single TRAIN site: 1W53 T37'),
        ('n15', 'train', '15 TRAIN proteins / 27 sites'),
        ('n15', 'dev_unseen_protein', '9 development proteins / 18 sites')]):
    for arm, colour in [('final', '#235c9e'), ('hint', '#d06a24')]:
        for seed, style in [(272001, '-'), (272003, '--')]:
            nodes = data['runs'][f'{cohort}_{arm}_{seed}']['nodes']
            label = f'{arm}, {seed}'
            axes[0,col].plot([n['step'] for n in nodes],
                [n['latent'][role]['centered_nmse'] for n in nodes],
                style, color=colour, marker='o', markersize=4, label=label)
            axes[1,col].plot([n['step'] for n in nodes],
                [n['summary'][role]['correct']['centered_response_rmse'] for n in nodes],
                style, color=colour, marker='o', markersize=4, label=label)
    axes[0,col].axhline(1, color='#777777', linestyle=':', label='No correction')
    base = nodes[0]['summary'][role]['disabled']['centered_response_rmse']
    oracle = nodes[0]['summary'][role]['oracle_pair']['centered_response_rmse']
    axes[1,col].axhline(base, color='#777777', linestyle=':', label='No correction')
    axes[1,col].axhline(oracle, color='#539c55', linestyle=':', label='Oracle pair')
    old_latent, old_response = [], []
    for init in ('pretrained', 'random'):
        for seed in (272001, 272003):
            if cohort == 'n1':
                old = old_single['runs'][f'{init}_{seed}']['nodes'][-1]
                old_latent.append(old['latent']['centered']['nmse'])
                old_response.append(old['summary']['correct']['centered_response_rmse'])
            else:
                old = old_joint['endpoints'][f'{init}_{seed}_8208']
                old_latent.append(old['latent'][role]['centered_nmse'])
                old_response.append(old['summary'][role]['correct']['centered_response_rmse'])
    for row, values in enumerate([old_latent, old_response]):
        axes[row,col].scatter([8208]*4, values, marker='x', color='#555555', s=38,
                              label='Previous appended model (4 endpoints)', zorder=5)
        axes[row,col].grid(alpha=.2)
        axes[row,col].set_xlabel('Updates (terminal 8208 is primary)')
        axes[row,col].set_xlim(-100, 8450)
    axes[0,col].set_title(title)
    axes[0,col].set_ylabel('AA-centered residual NMSE (lower is better)')
    axes[1,col].set_ylabel('AA structure-response RMSE / Å')
axes[0,0].legend(fontsize=7, loc='lower left')
axes[1,2].legend(fontsize=7, loc='best')
fig.suptitle('Native stage alignment: fit, joint learning, and development transfer', fontsize=13)
fig.savefig(root/'learning_curve.png', dpi=170)
fig.savefig(root/'learning_curve.pdf')
