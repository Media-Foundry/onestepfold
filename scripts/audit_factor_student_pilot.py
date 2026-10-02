"""Independent cohort, exposure, terminal-state and saved-score audits."""
import argparse,gzip,json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from fastglycan.sequence_isolation import read_hsps
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.scaling_metrics import lddt_observed


def audit_factor_student(root):
    select=json.load(open(root/'selection.json'));t=json.load(open(root/'teacher_lock.json'));s=json.load(open(root/'student_lock.json'));parents={r['index']:r for r in t['rows']}
    components=select['all_components'];assert len({components[r['group_id']] for r in select['rows']})==24
    assert not {components[r['group_id']] for r in select['rows']} & set(select['blocked_components'])
    accessions=[set(r['accessions']) for r in select['rows']];assert all(not accessions[i]&accessions[j] for i in range(24) for j in range(i))
    aliases={g[:32]:g for g in components};chosen={r['group_id'] for r in select['rows']};edge_checks=0
    for h in read_hsps(root/'hits.tsv'):
        a,b=aliases[h.query],aliases[h.subject]
        if a!=b and h.evidence()['excluded']:
            assert components[a]==components[b]
            assert not (a in chosen and b in chosen);edge_checks+=1
    exposure=[];checkpoint=[]
    teacher_manifest={x['path']:x['sha256'] for x in json.load(open(root/'teacher_manifest.json'))}
    teacher_owner={pi:i for i,ps in enumerate(t['assignments']) for pi in ps}
    for i in range(2):
        report=json.load(open(root/f'train_{i}/report.json'));assert report['complete'] and report['updates']==s['updates'];steps=report['losses'];assert len(steps)==1024
        assert all(parents[x['parent_index']]['role']=='train' and x['position'] in parents[x['parent_index']]['positions'] and x['aa']!=parents[x['parent_index']]['sequence'][x['position']] for x in steps)
        assert sha256(root/f'train_{i}/final.pt')==report['checkpoint_sha256']
        checkpoint.append(report['checkpoint_sha256']);exposure.append([(x['parent_index'],x['position'],x['aa'],x['noise_index']) for x in steps])
    assert checkpoint[0]!=checkpoint[1] and exposure[0]==exposure[1]
    out=root/'evaluation';lock=json.load(open(out/'lock.json'))
    with gzip.open(out/'report.json.gz','rt') as f:r=json.load(f)
    ranking_checks=0;lddt_checks=0;max_error=0.;manifest=[];seen=set();refchecks=0
    for site in r['sites']:
        pi,pos=site['parent_index'],site['position'];wt=lock['aa'].index(parents[pi]['sequence'][pos]);wi=next(i for i,ps in enumerate(lock['assignments']) if pi in ps);work=out/f'worker_{wi}';tasks={}
        for arm in lock['arms']:
            for seed in lock['seeds']:tasks[arm,seed]=np.array([next(x['task'] for x in site['outputs'] if x['arm']==arm and x['noise']==seed and x['aa']==aa) for aa in lock['aa']])
        for q in site['ranking']:
            ids=np.arange(20) if q['includes_wt'] else np.delete(np.arange(20),wt);a=tasks[q['arm'],q['noise']][ids];b=tasks[q['reference'],q['noise']][ids];rho=float(spearmanr(a,b).statistic)
            assert abs(rho-q['spearman'])<1e-12
            regret=float(b[np.argsort(a,kind='stable')[0]]-b.min());assert abs(regret-q['top1_regret'])<1e-12;ranking_checks+=1
        for ai,aa in enumerate(lock['aa']):
            label=f'p{pi}_wt' if ai==wt else f'p{pi}_s{pos+1}_{aa}';p=work/f'{label}_coordinates.npz';co=np.load(p)['coordinates']
            if p not in seen:
                teacher_path=root/f'teacher_{teacher_owner[pi]}'/f'{label}_coordinates.npz'
                assert sha256(teacher_path)==teacher_manifest[str(teacher_path.relative_to(root))]
                original=np.load(teacher_path)['coordinates']
                if ai==wt:assert np.array_equal(co,original);refchecks+=1
                else:assert np.array_equal(co[0],original[0]) and np.array_equal(co[1],original[1]);refchecks+=2
                manifest.append(dict(path=str(p.relative_to(root)),sha256=sha256(p),bytes=p.stat().st_size));seen.add(p)
            if ai==next(j for j in range(20) if j!=wt):
                inv=dict(np.load(work/f'{label}_inventory.npz'))
                for k,arm in enumerate(lock['arms']):
                    for ri,group in [(0,'fidelity'),(1,'compression_fidelity')]:
                        value=lddt_observed(co[k,0],co[ri,0],inv['residue_ids'])['score'];saved=next(x[group]['all_atom_lddt'] for x in site['outputs'] if x['aa']==aa and x['noise']==lock['seeds'][0] and x['arm']==arm);max_error=max(max_error,abs(value-saved));lddt_checks+=1
    assert ranking_checks==24*5*2*2*2 and lddt_checks==24*6*2 and len(manifest)==468 and refchecks==924 and max_error<1e-12
    write_json(root/'independent_audit.json',dict(complete=True,sequence_components=24,qualifying_nonself_hsp_edges=edge_checks,training_exposures=[len(x) for x in exposure],identical_exposure_schedule=True,distinct_final_checkpoints=True,no_validation_training=True,coordinate_packets=len(manifest),teacher_reference_arrays_checked=refchecks,ranking_checks=ranking_checks,independent_lddt_checks=lddt_checks,max_lddt_error=max_error,validation_parents=8,training_probe_parents=4))
    write_json(root/'evaluation_coordinate_manifest.json',manifest)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();audit_factor_student(a.root)
