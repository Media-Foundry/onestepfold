"""Expose existing aligned-Cα RMSD alongside local-distance quality metrics."""
import numpy as np


def summarize_global_structure(records, lock):
    rows={r['group_id']:r for r in lock['rows']}
    members=[g for group in lock['cohorts'].values() for g in group]
    if len(rows)!=len(lock['rows']) or len(members)!=len(set(members)) or set(members)!=set(rows):
        raise ValueError('cohorts must partition unique proteins')
    lookup={(r['group_id'],r['seed'],r['model']):r for r in records}
    expected={(g,s,m) for g,r in rows.items()
              for s in (lock['train_seeds'] if r['role']=='train' else lock['validation_seeds'])
              for m in lock['models']}
    if len(lookup)!=len(records) or set(lookup)!=expected:
        raise ValueError('missing or duplicate prediction; preserve full denominator')
    if any(not np.isfinite(r['ca_aligned_rmsd']) or r['ca_aligned_rmsd']<0 for r in records):
        raise ValueError('RMSD must be finite and nonnegative')
    summary={};paired=[]
    lines=['## Global structure: aligned Cα RMSD (Å)','',
        'Lower RMSD is better. Positive candidate − reference differences mean deterioration, '
        'opposite to lDDT. These are the existing GT-aligned RMSD scores, without a new alignment '
        'or atom mask. Average both locked noises within each protein before aggregation. '
        'Intervals resample proteins, conditional on the fixed noises. This adds no acceptance threshold.','']
    for cohort,groups in lock['cohorts'].items():
        n=len(groups)
        if n==0:raise ValueError('empty cohort')
        boot=np.random.default_rng(lock['bootstrap']['seed']).integers(0,n,size=(lock['bootstrap']['replicates'],n))
        arrays={};models={};contrasts=[];tail=max(1,int(np.ceil(.05*n)))
        lines.extend([f'### {cohort}: {n} proteins','',
            '|Model|Mean|Median|P95|P99|Worst5% mean|','|---|---:|---:|---:|---:|---:|'])
        for model in lock['models']:
            values=[]
            for g in groups:
                seeds=lock['train_seeds'] if rows[g]['role']=='train' else lock['validation_seeds']
                values.append(np.mean([lookup[g,s,model]['ca_aligned_rmsd'] for s in seeds]))
            x=np.asarray(values);arrays[model]=x
            m=dict(mean=float(x.mean()),median=float(np.median(x)),p95=float(np.quantile(x,.95)),
                   p99=float(np.quantile(x,.99)),worst5_mean=float(np.sort(x)[-tail:].mean()))
            models[model]=m
            lines.append(f"|{model}|{m['mean']:.6f}|{m['median']:.6f}|{m['p95']:.6f}|{m['p99']:.6f}|{m['worst5_mean']:.6f}|")
        lines.extend(['','|Candidate − reference|Mean Δ|95% CI|P95 Δ|P99 Δ|Worst5% Δ mean|RMSD increased, proteins|',
            '|---|---:|---|---:|---:|---:|---:|'])
        for candidate,reference in lock['contrasts']:
            delta=arrays[candidate]-arrays[reference]
            p=dict(candidate=candidate,reference=reference,mean=float(delta.mean()),
                ci95=np.quantile(delta[boot].mean(1),[.025,.975]).tolist(),
                p95=float(np.quantile(delta,.95)),p99=float(np.quantile(delta,.99)),
                worst5_mean=float(np.sort(delta)[-tail:].mean()),increased_proteins=int((delta>0).sum()))
            contrasts.append(p);lo,hi=p['ci95']
            lines.append(f"|{candidate} − {reference}|{p['mean']:+.6f}|[{lo:+.6f}, {hi:+.6f}]|"
                f"{p['p95']:+.6f}|{p['p99']:+.6f}|{p['worst5_mean']:+.6f}|{p['increased_proteins']}/{n}|")
            for i,g in enumerate(groups):
                seeds=lock['train_seeds'] if rows[g]['role']=='train' else lock['validation_seeds']
                paired.append(dict(cohort=cohort,group_id=g,candidate=candidate,reference=reference,
                    delta_rmsd=float(delta[i]),per_noise=[dict(seed=s,
                        delta_rmsd=lookup[g,s,candidate]['ca_aligned_rmsd']-lookup[g,s,reference]['ca_aligned_rmsd']) for s in seeds]))
        summary[cohort]=dict(proteins=n,models=models,contrasts=contrasts);lines.append('')
    return dict(complete=True,summary=summary,paired=paired,markdown='\n'.join(lines))
