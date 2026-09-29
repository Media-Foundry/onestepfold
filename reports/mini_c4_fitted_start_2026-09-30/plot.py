"""Frozen two-noise protein means; paired changes, not best-of-seed results."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root = Path(__file__).resolve().parent
rows = [p for p in json.loads((root/'summary.json').read_text())['proteins'] if p['complete']]
fig, axes = plt.subplots(1, 2, figsize=(8.5, 4), layout='constrained')
for ax, key, title in zip(axes, ['delta_aa', 'delta_ca'], ['All-atom lDDT', 'Cα-lDDT']):
    values = [p[key] for p in rows]
    ax.barh(range(len(rows)), values, color=['#247a97' if x > 0 else '#b56736' for x in values])
    ax.set_yticks(range(len(rows)), [p['pdb_id'].upper() for p in rows]); ax.invert_yaxis()
    ax.axvline(0, color='black', lw=.8); ax.grid(axis='x', alpha=.2)
    ax.set_title(title); ax.set_xlabel('Fitted-start final − zero-start final')
fig.suptitle('7 development proteins: mean of two fixed noises', fontsize=12)
fig.savefig(root/'quality.png', dpi=180); fig.savefig(root/'quality.pdf')
