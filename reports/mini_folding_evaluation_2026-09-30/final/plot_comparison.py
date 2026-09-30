"""Plot frozen cohort summaries; never recompute or select experimental results."""
import gzip
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
data = gzip.decompress((root / 'cohorts.json.gz').read_bytes())
provenance = json.loads((root / 'provenance.json').read_text())
expected = next(v for k,v in provenance['inputs'].items() if k.endswith('/cohorts.json'))
assert hashlib.sha256(data).hexdigest() == expected
summary = json.loads(data)['summary']
cohorts = ['new_validation32', 'original_train128', 'added_train295']
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
for ax, metric, label in zip(axes, ['all_atom_lddt', 'ca_lddt'], ['All-atom lDDT change', 'Cα-lDDT change']):
    for candidate, offset, color, name in [('train128', -.11, '#8e44ad', 'TRAIN128 continuation'), ('expanded', .11, '#168c82', 'TRAIN423 continuation')]:
        for j, cohort in enumerate(cohorts):
            c = next(x for x in summary[cohort]['contrasts'] if x['candidate']==candidate and x['reference']=='retained')
            d = c['quality'][metric]; mean = d['mean']; lo,hi = d['ci95']
            ax.errorbar(mean, j+offset, xerr=[[mean-lo],[hi-mean]], fmt='o', color=color, capsize=3, label=name if j==0 else None)
    ax.axvline(0, color='#555555', linestyle='--', linewidth=1)
    ax.set_xlabel(label); ax.grid(axis='x', alpha=.18)
axes[0].set_yticks(range(3), ['New VAL32', 'Original TRAIN128', 'Added TRAIN295'])
axes[0].invert_yaxis(); axes[1].legend(loc='upper right', fontsize=8)
fig.suptitle('Fixed-terminal changes versus retained C4/S1', fontsize=14)
fig.text(.5, .025, 'Protein means over two fixed noises; 95% protein-bootstrap intervals. Geometry is reported separately.', ha='center', fontsize=9)
fig.tight_layout(rect=(0, .06, 1, .93))
fig.savefig(root / 'cohort_quality.png', dpi=180)
fig.savefig(root / 'cohort_quality.pdf')
