"""All fixed single-context nodes and historical matched-exposure comparisons."""
import gzip
import json
from pathlib import Path
import numpy as np


def analyze_candidate_fit(root):
    lock = json.loads((root / 'training_lock.json').read_text())
    old_root = root.parent / 'mini_pair_recovery_2026-10-09'
    runs = {}
    for arm in lock['arms']:
        for seed in lock['seeds']:
            folder = root / 'runs' / arm / str(seed)
            report = json.loads((folder / 'report.json').read_text())
            history = [json.loads(line) for line in (folder / 'history.jsonl').read_text().splitlines()]
            with gzip.open(old_root / 'runs' / arm / str(seed) / 'scores_8208.json.gz', 'rt') as f:
                historical = json.load(f)
            historical_site = next(r for r in historical['sites'] if r['site_key']=='p3_s37' and r['arm']=='correct')
            old_ev = json.loads((old_root / 'runs' / arm / str(seed) / 'evaluation_8208.json').read_text())
            historical_latent = next(r['moments'] for r in old_ev['latent'] if r['site']=='p3_s37')
            nodes = []
            for step in lock['checkpoints']:
                ev = json.loads((folder / f'evaluation_{step}.json').read_text())
                with gzip.open(folder / f'scores_{step}.json.gz', 'rt') as f:
                    score = json.load(f)
                selected = {r['arm']: dict(aa=r['old_selected'], regret=r['old_select_new_regret'],
                                          mean_noise_spearman=r['aggregate_ranking']['spearman'],
                                          noise_spearman=[v['spearman'] for v in r['ranking']]) for r in score['sites']}
                candidate_nmse = np.array([r['moments']['raw']['nmse'] for r in ev['candidate_stats']])
                nodes.append(dict(step=step, exposures=step*2//19, latent=ev['latent'][0]['moments'],
                                  mismatch_latent=ev['mismatch_latent'], objective=ev['objective'],
                                  summary=score['summary']['train'], selections=selected,
                                  individual_raw_nmse=dict(mean=float(candidate_nmse.mean()),
                                      median=float(np.median(candidate_nmse)),minimum=float(candidate_nmse.min()),
                                      maximum=float(candidate_nmse.max()),below_zero_baseline=int((candidate_nmse<1).sum())),
                                  parameter_movement_squared=ev['parameter_movement_squared']))
            chunks = []
            for end in range(304, 8209, 304):
                hh = history[end-304:end]
                chunks.append(dict(step=end, mean_loss=float(np.mean([r['loss'] for r in hh])),
                                   clipped=sum(r['clipped'] for r in hh),
                                   gradient_mean=float(np.mean([r['gradient_norm'] for r in hh]))))
            runs[f'{arm}_{seed}'] = dict(nodes=nodes, historical_joint=dict(
                updates=8208,exposures=32,latent=historical_latent,site=historical_site),
                clipped_total=sum(r['clipped'] for r in history),learning_chunks=chunks,
                seconds=report['seconds'],peak_allocated_bytes=report['peak_allocated_bytes'],
                gradient_audits=report['gradient_audits'])
    result = dict(complete=True,runs=runs,site='1W53 T37',parents=1,sites=1,candidates=19,
                  main_node=8208,matched_exposure_node=304,independent_confirmation=False,
                  no_causal_capacity_or_gradient_conflict_identification=True)
    (root / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, axes = plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for name, run in runs.items():
        nodes=run['nodes'];xs=[r['exposures'] for r in nodes]
        axes[0].plot(xs,[r['latent']['raw']['nmse'] for r in nodes],marker='o',label=name)
        axes[1].plot(xs,[r['latent']['centered']['nmse'] for r in nodes],marker='o',label=name)
    for ax,title in zip(axes,('Full residual','AA-centered residual')):
        ax.set(title=title,xlabel='Exposures per candidate',ylabel='Residual NMSE')
        ax.axhline(1,color='black',linestyle=':',linewidth=1)
        ax.axvline(32,color='grey',linestyle='--',linewidth=1)
        ax.grid(alpha=.2)
    axes[1].legend(fontsize=8)
    fig.suptitle('1W53 T37: single-context fitting (no transfer evaluation)')
    fig.savefig(root/'learning_curve.png',dpi=160);plt.close(fig)


if __name__ == '__main__':
    analyze_candidate_fit(Path(__file__).resolve().parent)
