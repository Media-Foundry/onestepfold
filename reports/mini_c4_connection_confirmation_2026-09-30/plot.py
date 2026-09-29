"""Render frozen per-protein two-noise means; no candidate selection."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root = Path(__file__).resolve().parent
rows = [p for p in json.loads((root/'summary.json').read_text())['proteins'] if p['complete']]
fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), layout='constrained')
for ax, metric, title in zip(axes, ['aa', 'ca'], ['All-atom lDDT', 'Cα-lDDT']):
    for i, row in enumerate(rows):
        for x, key, color, label in [(0, 'raw', '#777777', 'Raw C4/S1'),
                (1, 'original', '#b56736', 'Original repair'),
                (2, 'calibrated', '#247a97', 'Calibrated repair')]:
            ax.scatter(i+(x-1)*.2, row[f'{key}_{metric}'], color=color, s=28,
                       label=label if i == 0 else None)
        ax.plot([i, i+.2], [row[f'original_{metric}'], row[f'calibrated_{metric}']],
                color='#247a97', lw=1)
    ax.set_xticks(range(len(rows)), [p['pdb_id'].upper() for p in rows], rotation=35)
    ax.set_ylabel(title); ax.grid(axis='y', alpha=.2); ax.set_ylim(.67, 1.0)
axes[0].legend(fontsize=8, loc='upper left')
fig.suptitle('Frozen C4/S1 development confirmation: two-noise mean per protein', fontsize=11)
fig.savefig(root/'quality.png', dpi=170); fig.savefig(root/'quality.pdf')
