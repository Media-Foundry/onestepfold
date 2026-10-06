"""Read-only task, replay, call-budget and candidate-selection audit."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from fastglycan.paired_teacher_protocol import sha256,write_json


def audit_prefix_reuse(root):
    load=lambda p:json.loads(Path(p).read_text());lock=load(root/'lock.json');report=load(root/'report.json');assert report['complete']
    for group in ['asset_hashes','code_hashes']:
        for p,h in lock[group].items():assert sha256(Path(p))==h
    gates=[load(root/f'gate_{i}/report.json') for i in range(4)]
    assert all(g['complete'] for g in gates)
    gr=[r for g in gates for r in g['records']];assert len(gr)==18
    assert all(r['zero_C4_bitwise'] and r['rng_restored_exactly'] and r['split_bitwise']==[2,3] for r in gr)
    tasks={};task_checks=0;replays=0;counts={k:0 for k in ['conditioning','recycle','s1','coordinate_replays','source_replays']}
    source_replays=0
    for wi in range(4):
        run=load(root/f'worker_{wi}/report.json');assert run['complete']
        for k in counts:counts[k]+=run['counts'][k]
        assert len(run['records'])==len(lock['assignments'][wi])*308
        assert len({(r['label'],r['cycles']) for r in run['records']})==len(run['records'])
        for source in run['sources']:
            label=source['label'];p=source['coordinates'];assert sha256(Path(p['path']))==p['sha256']
            archived=lock['archives'][label];assert sha256(Path(archived['path']))==archived['sha256']
            assert np.array_equal(np.load(p['path'])['coordinates'],np.load(archived['path'])['coordinates']);source_replays+=4
            assert source['prefix_bytes']>0
            for arm in [22,31]:
                copied=next(r for r in run['records'] if r['label']==label and r['cycles']==arm)
                assert copied['coordinates']==p and copied['timing']==source['timing'] and copied['wt_shared_source']
        for pi in lock['assignments'][wi]:
            setup=next(x['seconds'] for x in run['parent_setup'] if x['parent_index']==pi)
            for arm in [2,4,22,31]:
                rows=[x for x in run['records'] if x['parent_index']==pi and x['cycles']==arm]
                assert len(rows)==77
                tm=next(t for t in report['timings'] if t['parent_index']==pi and t['cycles']==arm)
                assert abs(tm['resident_screen_seconds']-setup-sum(r['timing']['total_seconds'] for r in rows))<1e-8
        for row in run['records']:
            label=row['label'];invinfo=lock['native'][label];assert sha256(Path(invinfo['path']))==invinfo['sha256'];inv=dict(np.load(invinfo['path']))
            cp=row['coordinates'];assert sha256(Path(cp['path']))==cp['sha256'];co=np.load(cp['path'])['coordinates'];ca=inv['atom_names']=='CA'
            gt=dict(np.load(lock['prior_lock']['gt'][str(row['parent_index'])]['path']));gca=gt['atom_names']=='CA';ref=gt['coordinates'][gca].astype(float);mask=gt['mask'][gca]
            i,j=np.triu_indices(len(ref),3);keep=mask[i]&mask[j];i,j=i[keep],j[keep];target=np.linalg.norm(ref[i]-ref[j],axis=1);scores=[]
            for ni,x in enumerate(co):
                x=x[ca].astype(float);e=abs(np.linalg.norm(x[i]-x[j],axis=1)-target);s=float(np.mean(np.minimum(e,1)**2/2+np.maximum(e-1,0)))
                assert abs(s-row["scores"][ni]["task"])<1e-12; scores.append(s);task_checks+=1
            tasks[label,row['cycles']]=np.array(scores)
            t=row['timing'];assert all(np.isfinite(v) and v>=0 for v in t.values())
            components=['native_seconds','device_atom_seconds','esm_seconds','trunk_seconds','decode_4noise_seconds','screen_score_seconds','coordinate_write_seconds']
            assert sum(t[k] for k in components)<=t['total_seconds']+1e-6
            if row['cycles']==4:
                archived=lock['archives'][label];assert sha256(Path(archived['path']))==archived['sha256'];assert np.array_equal(co,np.load(archived['path'])['coordinates']);replays+=4
    assert counts=={k:lock['expected'][k] for k in counts};assert replays==2772 and source_replays==36 and task_checks==11088
    selection=0;aa=lock['prior_lock']['aa']
    for s in report['sites']:
        pi,pos,cycle=s['parent_index'],s['position'],s['cycles'];wt=lock['prior_lock']['rows'][pi]['sequence'][pos];names=[a for a in aa if a!=wt]
        y=np.array([tasks[f'p{pi}_s{pos+1}_{a}',4]-tasks[f'p{pi}_wt',4] for a in names]).T
        x=np.array([tasks[f'p{pi}_s{pos+1}_{a}',cycle]-tasks[f'p{pi}_wt',cycle] for a in names]).T
        for group,ns in [('old',[0,1]),('new',[2,3]),('all',[0,1,2,3])]:
            ys=y[ns].mean(0);xs=x[ns].mean(0);a=s['selection']['aggregate'][group];rho=float(spearmanr(ys,xs).statistic) if np.ptp(ys) and np.ptp(xs) else None
            assert (rho is None and a['spearman'] is None) or abs(rho-a['spearman'])<1e-12;selection+=1
        chosen=np.argmin(x[:2].mean(0));new=y[2:].mean(0);cross=s['selection']['cross_noise'];assert names[chosen]==cross['student_old_choice']
        assert abs(new[chosen]-new.min()-cross['regret_to_new_best'])<1e-12
    for s in report['structures']:
        if s['cycles']==4:
            assert abs(s['all_atom_lddt']-1)<1e-12 and abs(s['ca_lddt']-1)<1e-12 and s['local_ca_rmsd_global_frame']<1e-10
            assert not s['new_failure'] and not s['repaired_failure']
    write_json(root/'independent_audit.json',dict(complete=True,counts=counts,coordinate_replays=replays,source_replays=source_replays,integrity_cases=len(gr),segment_checks=2*len(gr),task_checks=task_checks,selection_checks=selection,optimizer_updates=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);audit_prefix_reuse(p.parse_args().root)
