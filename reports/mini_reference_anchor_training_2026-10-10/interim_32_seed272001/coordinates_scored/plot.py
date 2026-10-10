"""Render the fixed-node, per-protein changes from the verified comparison."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parent
source = root/'functional_comparison.json'
record = json.loads(source.read_text())
assert record['interim'] and not record['promoted']
panel = record['panels']['dev_unseen_protein']
parents = panel['parent_comparison']
fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)
for ax, field, divisor, title in zip(axes, ['centered_response_rmse', 'regret'],
        [1, len(parents)], ['AA distance response RMSE change (Å)', 'Contribution to mean regret change']):
    values = np.asarray([r['differences'][field]/divisor for r in parents])
    span = max(np.ptp(values), 1e-6)
    ax.barh(np.arange(len(parents)), values,
            color=['#b45b32' if v > 0 else '#247ba0' for v in values])
    ax.axvline(0, color='#4a4a4a', linewidth=.8)
    ax.set_xlim(min(0, values.min())-.22*span, max(0, values.max())+.3*span)
    ax.set_title(title, fontsize=12)
    ax.set_xlabel('Anchored32 − matched AdamW32; negative is better')
    ax.grid(axis='x', alpha=.2); ax.set_axisbelow(True)
    for y, value in enumerate(values):
        ax.text(value+(.025*span if value >= 0 else -.025*span), y, f'{value:+.4f}',
                va='center', ha='left' if value >= 0 else 'right', fontsize=9)
    ax.spines[['top','right']].set_visible(False)
axes[0].set_yticks(np.arange(len(parents)), [r['pdb'] for r in parents])
axes[0].invert_yaxis()
fig.suptitle('Fixed checkpoint32 · seed272001 · nine reused development proteins', fontsize=14)
fig.text(.5, .02, 'One interim seed; native tensor replay pending. No checkpoint selection or promotion.',
         ha='center', fontsize=10)
fig.tight_layout(rect=[0, .06, 1, .94])
for suffix in ('png','pdf'):
    fig.savefig(root/f'protein_changes.{suffix}', dpi=180)
plt.close(fig)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(root/'figure_provenance.json').write_text(json.dumps(dict(source_sha256=sha(source),
    script_sha256=sha(Path(__file__)), outputs={name: sha(root/name) for name in
    ('protein_changes.png','protein_changes.pdf')}), indent=2)+'\n')
