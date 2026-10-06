"""Independent archived-coordinate, workload accounting and timing audit."""
import argparse,json,statistics
from pathlib import Path
import numpy as np
from fastglycan.paired_teacher_protocol import sha256,write_json


def audit_native_execution(root):
    lock=json.loads((root/'lock.json').read_text());r=json.loads((root/'report.json').read_text());assert r['complete']
    old=lock['source_native_lock'];records=r['records'];assert len(records)==99
    assert r['counts']==dict(c4=99,recycle=396,s1=396,replayed_outputs=396)
    for group in ['assets','code']:
        for p,h in lock[group].items():assert sha256(Path(p))==h,p
    replays=0
    for row in records:
        p=row['coordinates'];assert sha256(Path(p['path']))==p['sha256']
        a=old['archives'][row['label']];assert sha256(Path(a['path']))==a['sha256']
        x=np.load(p['path'])['coordinates'];y=np.load(a['path'])['coordinates'];assert np.array_equal(x,y);replays+=len(x)
        assert np.isfinite(row['wall_seconds']) and row['wall_seconds']>0
        assert sum(row['stages'].values())<=row['wall_seconds']+1e-6
    assert replays==396 and len(r['dependencies'])==18 and len(r['cache_diagnostics'])==18 and len(r['profiles'])==4
    cases=[]
    for case in lock['cases']:
        rows=[x for x in records if x['label']==case['label']];by={x['kind']:x for x in rows};assert len(by)==len(rows)
        assert all(k in by for k in ['warmup','steady_0','steady_1','steady_2','stage_breakdown'])
        values=[by[f'steady_{i}']['wall_seconds'] for i in range(3)];med=statistics.median(values);stages=by['stage_breakdown']['stages']
        cache=next(x for x in r['cache_diagnostics'] if x['label']==case['label']);assert cache['bitwise_equal'] and cache['rng_unchanged'] and len(cache['times'])==4
        cases.append(dict(label=case['label'],parent_index=case['parent_index'],position=case['position'],length=len(case['sequence']),steady_seconds=values,
            steady_median=med,steady_min=min(values),steady_max=max(values),synchronized_stage_seconds=stages,synchronized_wall=by['stage_breakdown']['wall_seconds'],
            profiled_wall={k:by[k]['wall_seconds'] for k in ['torch_profile','cpu_profile'] if k in by},
            peak_allocated_bytes=max(by[f'steady_{i}']['peak_allocated_bytes'] for i in range(3)),cache_recompute_mean_seconds=statistics.mean(x['pair_seconds']+x['atom_seconds'] for x in cache['times'])))
    write_json(root/'summary.json',dict(complete=True,cases=cases,first_invocation=next(x for x in records if x['kind']=='first_invocation'),
        model_load_seconds=r['model_load_seconds'],gpu_profiles=sum(p['gpu_attribution_available'] for p in r['profiles']),profile_only=True,no_optimization=True))
    write_json(root/'independent_audit.json',dict(complete=True,coordinates_replayed=replays,workloads=len(records),steady_repeats=54,stage_breakdowns=18,operator_profiles=4,cpu_profiles=4,optimizer_updates=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);audit_native_execution(p.parse_args().root)
