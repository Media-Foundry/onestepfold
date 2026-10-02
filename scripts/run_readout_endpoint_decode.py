"""All twelve failed-latent-gate endpoints: no parameter updates or new trunk calls."""
import argparse,copy,gzip,json,time
from pathlib import Path
import numpy as np
import torch
from scipy.stats import spearmanr
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.scaling_metrics import lddt_observed
from run_response_readouts import readout_data,make_readout,readout_predict,matrix_metrics
import deep_validation_outputs as output


def prepare_endpoint_audit(root):
    assert not (root/'lock.json').exists();prior=root.parent/'response_readout_v1_20261002';old=output.rt.load_json(prior/'lock.json');assert output.rt.load_json(prior/'execution.json')['complete']
    plan=output.rt.load_json(prior/'planned_jobs.json');assert len(plan['single'])==12;items=[]
    for job in plan['single']:
        report=output.rt.load_json(prior/'runs'/job['id']/'report.json');last=report['history'][-1];assert report['complete'] and last['step']==8192 and job['sites']==[[3,36]]
        p=Path(last['checkpoint']);assert sha256(p)==last['sha256'];items.append(dict(path=str(p),sha256=last['sha256'],job=job,terminal=last,source_report_sha256=sha256(prior/'runs'/job['id']/'report.json')))
    panel=copy.deepcopy(output.rt.load_json(prior/'functional/closure/lock.json'));panel['checkpoints']=items;panel['arms']=['exact','baseline','wt_z','oracle_r32']+[x['job']['id'] for x in items]
    write_json(root/'functional/endpoints/lock.json',panel)
    references=[dict(path=str(p),sha256=sha256(p)) for p in sorted((prior/'functional/closure/worker_0').glob('*_coordinates.npz'))];assert len(references)==20
    write_json(root/'lock.json',dict(schema='readout_endpoint_decode_v1',prior=str(prior),teachers=old['teachers'],prior_lock_sha256=sha256(prior/'lock.json'),teacher_lock_sha256=old['teacher_lock_sha256'],teacher_manifest_sha256=old['teacher_manifest_sha256'],checkpoints=items,references=references,panel_sha256=sha256(root/'functional/endpoints/lock.json'),expected_student_outputs=456,expected_s1_calls=610,training=False,protocol_sha256=sha256(root/'code/docs/mini_readout_endpoint_decode_v1.md'),code_hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']}))


def decode_endpoints(root):
    runtime=guarded_hip_runtime();lock=output.rt.load_json(root/'lock.json')
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h
    assert sha256(root/'functional/endpoints/lock.json')==lock['panel_sha256'];store=FactorTeacherStore(Path(lock['teachers']),training_only=True);data=readout_data(store,3,36);checks=[]
    def load_fixed_checkpoint(item):
        p=Path(item['path']);assert sha256(p)==item['sha256'];state=torch.load(p,map_location='cpu',weights_only=False);assert state['step']==8192 and state['job']==item['job'];net=make_readout(state['job'],[data]).eval();net.load_state_dict(state['state_dict'])
        with torch.no_grad():m=matrix_metrics(readout_predict(net,data),data,item['job']['label'])
        before=item['terminal']['sites'][0];error=max(float(np.max(np.abs(np.array(m[k]['nmse'])-np.array(before[k]['nmse'])))) for k in ['raw','label']);assert error<1e-5
        checks.append(dict(job=item['job']['id'],max_terminal_nmse_error=error,raw_nmse=m['raw']['mean_nmse'],label_nmse=m['label']['mean_nmse']));return net,state
    output.gpu_guard=guarded_hip_runtime;output.load_deep_checkpoint=load_fixed_checkpoint
    output.decode_deep_panel(root,'endpoints',0);worker=output.rt.load_json(root/'functional/endpoints/worker_0/report.json');assert worker['counts']['nfe']==610 and worker['counts']['c4']==0
    replays=[]
    for old in lock['references']:
        p=Path(old['path']);assert sha256(p)==old['sha256'];a=np.load(p)['coordinates'];new=root/'functional/endpoints/worker_0'/p.name;b=np.load(new)['coordinates'];assert np.array_equal(a,b) if 'wt_' in p.name else np.array_equal(a[:4],b[:4]);replays.append(dict(packet=p.name,reference_arms_bitwise=True))
    for item in lock['checkpoints']:assert sha256(Path(item['path']))==item['sha256']
    write_json(root/'replay_audit.json',dict(complete=True,runtime=runtime,checkpoint_replays=checks,reference_replays=replays,source_weights_unchanged=True,c4_calls=0,esm_calls=0,s1_calls=610))


def collect_endpoint_audit(root):
    panel=root/'functional/endpoints';output.collect_deep_panel(root,'endpoints');lock=output.rt.load_json(panel/'lock.json')
    with gzip.open(panel/'report.json.gz','rt') as f:record=json.load(f)
    site=record['sites'][0];summary={};outputs=site['outputs'];baseline={(x['aa'],x['noise']):x for x in outputs if x['arm']=='baseline'}
    for arm in lock['arms']:
        rows=[x for x in outputs if x['arm']==arm and not x['is_wt']];entry=dict(instances=len(rows),geometry_pass=sum(x['geometry']['zero_severe_strict_checked_chirality'] for x in rows),severe_pairs_total=sum(x['geometry']['severe_pairs'] for x in rows),checked_chirality_wrong_total=sum(x['geometry']['checked_chirality_wrong'] for x in rows))
        for ref,field in [('exact','fidelity'),('baseline','compression_fidelity')]:
            rankings=[x for x in site['ranking'] if x['arm']==arm and x['reference']==ref and not x['includes_wt']]
            if not rankings:
                for seed in lock['seeds']:
                    order=[x['aa'] for x in rows if x['noise']==seed]
                    values=lambda name: np.array([next(x['task'] for x in outputs if x['arm']==name and x['noise']==seed and x['aa']==aa) for aa in order])
                    rankings.append(dict(arm=arm,noise=seed,reference=ref,includes_wt=False,**output.scoring.ranking_fidelity(values(ref),values(arm))))
            rms=np.array([x[field]['local_ca_rmsd_global_frame'] for x in rows]);entry[ref]=dict(ranking=rankings,mean_spearman=float(np.mean([x['spearman'] for x in rankings])),top1=sum(x['top1_match'] for x in rankings),mean_regret=float(np.mean([x['top1_regret'] for x in rankings])),local_rmsd=dict(mean=float(rms.mean()),p95=float(np.quantile(rms,.95)),p99=float(np.quantile(rms,.99)),max=float(rms.max()),over1=int((rms>1).sum())),all_atom_lddt=float(np.mean([x[field]['all_atom_lddt'] for x in rows])),ca_lddt=float(np.mean([x[field]['ca_lddt'] for x in rows])))
        transitions=dict(pass_to_fail=[],fail_to_pass=[],pass_to_pass=[],fail_to_fail=[])
        for x in rows:
            b=baseline[x['aa'],x['noise']]['geometry'];g=x['geometry'];key=('pass' if b['zero_severe_strict_checked_chirality'] else 'fail')+'_to_'+('pass' if g['zero_severe_strict_checked_chirality'] else 'fail');transitions[key].append(dict(aa=x['aa'],noise=x['noise'],before=b,after=g))
        entry['geometry_transitions']=transitions;summary[arm]=entry
    write_json(root/'summary.json',dict(complete=True,summary=summary,oracle_target_s=True,new_training=False,new_acceptance_gate=False))


def audit_endpoint_scores(root):
    panel=root/'functional/endpoints';lock=output.rt.load_json(panel/'lock.json');site=output.rt.load_json(panel/'worker_0/p3_s37_scores.json');wt=lock['aa'].index(lock['rows'][3]['sequence'][36]);tasks={};rankchecks=lddtchecks=0
    for arm in lock['arms']:
        for seed in lock['seeds']:tasks[arm,seed]=np.array([next(x['task'] for x in site['outputs'] if x['arm']==arm and x['noise']==seed and x['aa']==aa) for aa in lock['aa']])
    for r in site['ranking']:
        ids=np.arange(20) if r['includes_wt'] else np.delete(np.arange(20),wt);a=tasks[r['arm'],r['noise']][ids];b=tasks[r['reference'],r['noise']][ids];assert abs(float(spearmanr(a,b).statistic)-r['spearman'])<1e-12;assert abs(float(b[np.argsort(a,kind='stable')[0]]-b.min())-r['top1_regret'])<1e-12;rankchecks+=1
    coords=[]
    for ai,aa in enumerate(lock['aa']):
        label='p3_wt' if ai==wt else f'p3_s37_{aa}';p=panel/'worker_0'/f'{label}_coordinates.npz';coords.append(dict(path=str(p),sha256=sha256(p)))
        if ai==wt:continue
        co=np.load(p)['coordinates'];inv=dict(np.load(panel/'worker_0'/f'{label}_inventory.npz'))
        if ai in [0,1,2]:
            for k,arm in enumerate(lock['arms']):
                for ni,seed in enumerate(lock['seeds']):
                    value=lddt_observed(co[k,ni],co[1,ni],inv['residue_ids'])['score'];expected=next(x['compression_fidelity']['all_atom_lddt'] for x in site['outputs'] if x['aa']==aa and x['noise']==seed and x['arm']==arm);assert abs(value-expected)<1e-12;lddtchecks+=1
    summary=output.rt.load_json(root/'summary.json')['summary']
    for arm,r in summary.items():
        tr=r['geometry_transitions'];assert sum(map(len,tr.values()))==38 and len(tr['pass_to_pass'])+len(tr['pass_to_fail'])==9
        assert r['geometry_pass']==len(tr['fail_to_pass'])+len(tr['pass_to_pass'])
    write_json(root/'coordinate_manifest.json',coords);write_json(root/'score_audit.json',dict(complete=True,ranking_checks=rankchecks,independent_lddt_checks=lddtchecks,geometry_transition_accounting=True,coordinate_packets=len(coords)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','decode','score','collect','audit'],required=True);p.add_argument('--index',type=int,default=0);a=p.parse_args()
    if a.mode=='prepare':prepare_endpoint_audit(a.root)
    elif a.mode=='decode':decode_endpoints(a.root)
    elif a.mode=='score':
        output.scoring.ARMS=tuple(output.rt.load_json(a.root/'functional/endpoints/lock.json')['arms']);output.scoring.score_global_response_rank(a.root/'functional/endpoints',a.index)
    elif a.mode=='collect':collect_endpoint_audit(a.root)
    else:audit_endpoint_scores(a.root)
