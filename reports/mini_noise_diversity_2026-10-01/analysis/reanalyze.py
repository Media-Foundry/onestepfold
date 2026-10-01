"""Offline final checks and paired summaries; no inference or threshold changes."""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
from fastglycan.folding_evaluation import summarize_folding_cohorts
from fastglycan.folding_global_metrics import summarize_global_structure
from fastglycan.evaluation_reuse import expected_evaluation_calls
root=Path('reports/mini_noise_diversity_2026-10-01');arc=root/'assessment_complete';sources={}
def read(p):
    p=Path(p)
    if not p.exists():p=p.with_suffix(p.suffix+'.gz')
    b=p.read_bytes();sources[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def raw_sha(p):
    p=Path(p)
    if not p.exists():p=p.with_suffix(p.suffix+'.gz')
    b=p.read_bytes();return hashlib.sha256(gzip.decompress(b) if p.suffix=='.gz' else b).hexdigest()
def passed(x):return x['geometry']['severe_pairs']==0 and x['geometry']['strict_checked_chirality']
def delta_summary(x):
    x=np.asarray(x);rng=np.random.default_rng(20261001);boot=rng.integers(0,len(x),size=(10000,len(x)))
    return dict(mean=float(x.mean()),ci95=np.quantile(x[boot].mean(1),[.025,.975]).tolist())
execution=read(arc/'controller_execution.json');assert execution['complete'] and all(x['exit_code']==0 for x in execution['jobs'])
audit=read(root/'terminal/terminal_audit.json');assert audit['complete']
reports={};locks={};hashes={};transitions={};extremes={}
for panel in ['original','noise']:
    lock=read(arc/panel/'lock.json');report=read(arc/panel/'report.json');locks[panel]=lock;reports[panel]=report
    assert report['complete'] and report['lock_sha256']==raw_sha(arc/panel/'lock.json')
    assert lock['checkpoints']==audit['checkpoints'] and lock['checkpoint_training_locks']==audit['training_locks']
    seen=[];hashes[panel]={}
    for i,assignment in enumerate(lock['assignments']):
        w=read(arc/panel/f'worker_{i}/report.json');assert w['complete'] and w['lock_sha256']==report['lock_sha256']
        assert w['calls']==expected_evaluation_calls(lock,assignment) and w['probe_nfe']==7
        assert all(all(x.values()) for x in w['probe'].values())
        assert [x['group_id'] for x in w['rows']]==[x['group_id'] for x in assignment]
        for row in w['rows']:
            seen.append(row['group_id'])
            for x in row['entries']:hashes[panel][row['group_id'],x['seed'],x['model']]=x['sha256']
    assert len(seen)==len(set(seen))==len(lock['rows'])
    records=report['records'];lookup={(r['group_id'],r['seed'],r['model']):r for r in records}
    assert len(lookup)==len(records)==lock['planned_outputs'] and report['metric_max_abs']<1e-10
    for name,saved in report['summaries'].items():
        sub=dict(lock);sub['train_seeds']=lock['train_seeds'] if panel=='original' else ([600001,600011] if name=='seen' else [920003,920009,920021,920033])
        part=records if panel=='original' else [x for x in records if x['seed'] in sub['train_seeds']]
        assert summarize_folding_cohorts(part,sub)==saved['cohorts']
        assert summarize_global_structure(part,sub)==saved['global_structure']
        rows={r['group_id']:r for r in lock['rows']}
        for cohort,groups in sub['cohorts'].items():
            states=[];pstates=[];severe_delta=[];per_noise_bad=[]
            for g in groups:
                seeds=sub['train_seeds'] if rows[g]['role']=='train' else sub['validation_seeds']
                pp=[]
                for s in seeds:
                    f,d=lookup[g,s,'fixed'],lookup[g,s,'diverse'];states.append((passed(f),passed(d)));pp.append((passed(f),passed(d)))
                    severe_delta.append((g,s,d['geometry']['severe_pairs']-f['geometry']['severe_pairs']))
                    if d['all_atom_lddt']-f['all_atom_lddt'] < -.05 or d['ca_lddt']-f['ca_lddt']<-.05:
                        per_noise_bad.append(dict(pdb=f['pdb_id'],group_id=g,seed=s,delta_aa=d['all_atom_lddt']-f['all_atom_lddt'],delta_ca=d['ca_lddt']-f['ca_lddt']))
                pstates.append((all(a for a,b in pp),all(b for a,b in pp)))
            key=f'{panel}/{name}/{cohort}'
            transitions[key]=dict(instances={f'{a}_to_{b}':sum(x==a and y==b for x,y in states) for a in [False,True] for b in [False,True]},
                proteins_all_noises={f'{a}_to_{b}':sum(x==a and y==b for x,y in pstates) for a in [False,True] for b in [False,True]},
                protein_joint_pass_delta=delta_summary([int(b)-int(a) for a,b in pstates]),per_noise_quality_drop_gt005=per_noise_bad,
                top_severe_improvements=sorted(severe_delta,key=lambda x:x[2])[:5],top_severe_worsenings=sorted(severe_delta,key=lambda x:x[2],reverse=True)[:5])
            paired=saved['cohorts']['paired'];paired=[p for p in paired if p['cohort']==cohort]
            extremes[key]=[dict(pdb=rows[p['group_id']]['pdb_id'],**p) for p in sorted(paired,key=lambda p:p['delta_aa'])[:3]]
for key,sha in hashes['noise'].items():
    if key[1] in [600001,600011]:assert hashes['original'][key]==sha
for a in ['fixed','diverse']:
    replay=read(arc/'original'/f'flag_replay_{a}/report.json')
    assert replay['complete'] and replay['matched_state_exact'] and replay['parameter_updates']==0 and replay['parameters_unchanged']
    assert replay['checkpoint_sha256']==audit['checkpoints'][a]['sha256'] and len(replay['records'])==64
    assert all(x['exact'] for row in replay['records'] for x in row['states'].values())
oldroot=Path('reports/mini_noise_transfer_2026-10-01');old=read(oldroot/'report.json');ol=read(oldroot/'lock.json')
assert ol['checkpoints']['retained']['sha256']=='7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829'
assert {r['group_id']:r for r in ol['rows']}=={r['group_id']:r for r in locks['noise']['rows']}
for path,h in ol['input_hashes'].items():
    if path in locks['noise']['input_hashes']:assert h==locks['noise']['input_hashes'][path]
rr=[dict(r,model='retained') for r in old['records'] if r['model']=='retained']+reports['noise']['records']
lookup={(r['group_id'],r['seed'],r['model']):r for r in rr};groups=sorted({r['group_id'] for r in rr})
parent={};deltas={}
for name,seeds in [('seen',[600001,600011]),('new',[920003,920009,920021,920033])]:
    sub=dict(locks['noise'],models=['retained','fixed','diverse'],contrasts=[['fixed','retained'],['diverse','retained']],train_seeds=seeds)
    part=[r for r in rr if r['seed'] in seeds]
    parent[name]=dict(cohorts=summarize_folding_cohorts(part,sub),global_structure=summarize_global_structure(part,sub))
    deltas[name]={k:[np.mean([lookup[g,s,'diverse'][k]-lookup[g,s,'fixed'][k] for s in seeds]) for g in groups] for k in ['all_atom_lddt','ca_lddt','ca_aligned_rmsd']}
interaction={k:delta_summary(np.array(deltas['new'][k])-deltas['seen'][k]) for k in deltas['new']}
out=dict(complete=True,transitions=transitions,worst_paired=extremes,parent_train32=parent,new_minus_seen_interaction=interaction,
    archive_sources=sources,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),prediction_nfe=2204,
    matched_flag_replay_nfe=256,engineering_nfe=112,duplicate_old_noise_coordinates_exact=128,
    validation_seeds=locks['original']['validation_seeds'],scope='development paired results; parent reference only for matched TRAIN32; no additional inference')
(root/'analysis/reanalysis.json').write_text(json.dumps(out,indent=2)+'\n')
print('verified',len(sources),'sources, all summary recomputations and 128 duplicate coordinates')
for k,v in transitions.items():print(k,v['instances'],v['proteins_all_noises'],v['protein_joint_pass_delta'])
print('interaction',interaction)
for s in parent:
 p=parent[s]['cohorts']['summary']['train_probe32'];print('parent',s,p['models']);print('gains',p['contrasts']);print('rmsd',parent[s]['global_structure']['summary']['train_probe32']['contrasts'])
