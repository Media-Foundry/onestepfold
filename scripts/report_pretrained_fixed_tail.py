#!/usr/bin/env python3
"""Follow cohorts chosen before continuation, without selecting new training targets."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

METRICS = ('all_atom_lddt', 'ca_lddt', 'tm_score_ca_observed')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def vectors(rows, groups):
    by = {}
    for row in rows:
        if row['split'] == 'validation':
            key = (row['group_id'], row['noise'])
            if key in by:
                raise ValueError('Duplicate target/noise')
            by[key] = row['quality']
    assert set(by) == {(g, n) for g in groups for n in (12345, 54321)}
    return {m: np.asarray([np.mean([by[g, n][m] for n in (12345, 54321)]) for g in groups]) for m in METRICS}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--parent', type=Path, required=True)
    p.add_argument('--continuation', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    lock = json.loads((a.parent/'lock.json').read_text())
    manifest = json.loads((a.parent/'data_manifest.json').read_text())
    ids = {r['group_id']: r for r in manifest['selection'] if r['split']=='validation'}
    groups = sorted(ids); assert len(groups)==128
    hashes = {}
    def scores(root, size, step):
        path = root/'scores'/f'{size}_{step:04d}.json'
        d = json.loads(path.read_text()); hashes[str(path)] = digest(path)
        assert d['complete'] and d['lock_sha256']==digest(root/'lock.json')
        return vectors(d['rows'], groups)
    base = scores(a.parent, 2048, 0)
    native_rows = []
    for name, h in lock['baseline_scores'].items():
        path=Path(name); assert digest(path)==h; hashes[name]=h
        native_rows.extend(r for r in json.loads(path.read_text())['rows'] if r['condition']=='native_reference')
    native=vectors(native_rows, groups)
    count=int(np.ceil(.05*len(groups)))
    cohorts={m:np.argsort(base[m],kind='stable')[:count] for m in METRICS}
    history={}; per_target=[]
    for size in (2048,8192):
        history[str(size)]={}
        stages=[(a.parent,s) for s in (0,512,1024,2048,4096)]
        if a.continuation:
            cl=json.loads((a.continuation/'lock.json').read_text())
            assert cl['parent_lock_sha256']==digest(a.parent/'lock.json')
            stages += [(a.continuation,s) for s in (8192,16384)]
        for root,step in stages:
            values=scores(root,size,step); stats={}
            for m in METRICS:
                fixed=cohorts[m]; dynamic=np.argsort(values[m],kind='stable')[:count]
                deltas=values[m][fixed]-base[m][fixed]
                rng=np.random.default_rng(20260927)
                draws=rng.integers(0,count,size=(5000,count))
                ci=np.quantile(deltas[draws].mean(axis=1),[.025,.975]).tolist()
                stats[m]={'all_mean':float(values[m].mean()),'fixed_initial_tail_mean':float(values[m][fixed].mean()),
                          'reranked_tail_mean':float(values[m][dynamic].mean()),'same_tail_members':set(fixed)==set(dynamic),
                          'fixed_tail_delta_vs_initial':float(deltas.mean()),'conditional_ci95':ci,
                          'all_harm_gt005_vs_initial':int(np.sum(values[m]-base[m]<-.05)),
                          'all_harm_gt005_vs_native':int(np.sum(values[m]-native[m]<-.05))}
            history[str(size)][str(step)]=stats
            for i,g in enumerate(groups):
                per_target.append({'size':size,'step':step,'group_id':g,'pdb_id':ids[g]['pdb_id'],
                                   'initial_all_atom_tail':bool(i in cohorts['all_atom_lddt']),
                                   **{m:float(values[m][i]) for m in METRICS}})
    result={'complete':True,'cohorts':{m:[groups[i] for i in v] for m,v in cohorts.items()},'history':history,
            'per_target':per_target,'input_sha256':hashes,'source_sha256':digest(Path(__file__)),
            'scope':'Exploratory reused-DEV analysis. Cohorts fixed by initial bridge, never used for training selection. Conditional within-cohort bootstrap, not independent confirmation; 2 K1 noises averaged, not best-of-K.'}
    a.output.mkdir(parents=True)
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Fixed initial-tail follow-up','','|TRAIN|Update|AA mean|Fixed 7 AA|Re-ranked AA tail|Same 7?|CA initial-tail mean|', '|---:|---:|---:|---:|---:|---|---:|']
    for size,steps in history.items():
        for step,row in steps.items():
            aa=row['all_atom_lddt'];ca=row['ca_lddt']
            lines.append(f"|{size}|{step}|{aa['all_mean']:.5f}|{aa['fixed_initial_tail_mean']:.5f}|{aa['reranked_tail_mean']:.5f}|{aa['same_tail_members']}|{ca['fixed_initial_tail_mean']:.5f}|")
    lines+=['',result['scope']]
    (a.output/'report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'complete':True,'output':str(a.output)}))

if __name__=='__main__':main()
