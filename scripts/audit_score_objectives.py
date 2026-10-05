"""Independent locked-data, fresh-init, budget and selection audit."""
import argparse,json,math
from pathlib import Path
import numpy as np
import torch
from scipy.stats import spearmanr
from fastglycan.paired_teacher_protocol import sha256,write_json
from run_task_readout import make_task_model


def audit_score_objectives(root):
    torch.set_num_threads(1);load=lambda p:json.loads(p.read_text());lock=load(root/'lock.json');prior=Path(lock['prior'])
    assert load(root/'report.json')['complete']
    for group in ['code_hashes','asset_hashes']:
        for p,h in lock[group].items():assert sha256(Path(p))==h
    train=load(root/'train.json')['cases'];old=load(prior/'train_n32.json')['cases'];assert train==old
    assert len(train)==128 and all(c['role']=='train' and len(c['target_delta'])==2 for c in train)
    energies=[]
    for c in train:
        y=np.delete(np.mean(c['target_delta'],axis=0),c['wt']);energies.append(float(y@y/19-y.mean()**2))
    ordered=sorted(energies);offset=127*.25;floor=max(ordered[math.floor(offset)]*(1-offset%1)+ordered[math.ceil(offset)]*(offset%1),1e-12)
    raw=1/np.maximum(energies,floor);w=raw/raw.mean();assert np.allclose(w,[r['weight'] for r in lock['weights']['sites']],rtol=1e-11,atol=1e-12)
    assert abs(floor-lock['weights']['floor'])<1e-13
    states={};checks=0;losschecks=0;clipchecks=0;reference_deltas={}
    for j in lock['jobs']:
        run=root/'runs'/j['id'];rr=load(run/'report.json');assert rr['complete'];assert rr['context_exposures']==[1024]*128
        cp=run/'initial.pt';assert sha256(cp)==rr['initial_sha256'];pkt=torch.load(cp,map_location='cpu',weights_only=False)
        torch.manual_seed(j['seed']);net=make_task_model(j['architecture']);assert all(torch.equal(v,pkt['state_dict'][k]) for k,v in net.state_dict().items())
        key=(j['architecture'],j['seed'])
        if key in states:assert all(torch.equal(v,states[key][k]) for k,v in pkt['state_dict'].items())
        else:states[key]=pkt['state_dict']
        oldinit=torch.load(prior/'runs'/j['prior_job']/'initial.pt',map_location='cpu',weights_only=False)
        assert all(torch.equal(v,oldinit['state_dict'][k]) for k,v in pkt['state_dict'].items())
        assert [h['step'] for h in rr['history']]==[0,32768,65536,131072]
        for snap in rr['history']:
            for i,v in enumerate(snap['sites']):
                c=train[i];assert (v['parent_index'],v['position'])==(c['parent_index'],c['position'])
                ids=[a for a in range(20) if a!=c['wt']];p=np.array(v['predicted_delta'])[ids]/j['scale'];y=np.mean(c['target_delta'],axis=0)[ids]/j['scale'];d=p-y
                mse=float(d@d/19);center=float(mse-d.mean()**2);base=mse if j['arm']=='A' else center
                loss=base*(w[i] if j['arm']=='C' else 1.)
                assert abs(loss-v['objective'])<2e-5*max(1,abs(loss)),(j['id'],snap['step'],i,loss,v['objective'])
                assert abs(mse-v['normalized_mse'])<2e-5*max(1,mse);losschecks+=1
            if snap['step']:
                p=Path(snap['checkpoint']);assert sha256(p)==snap['sha256'];cp=torch.load(p,map_location='cpu',weights_only=False)
                assert cp['exposures']==[snap['step']//128]*128 and {int(x['step']) for x in cp['optimizer']['state'].values()}=={snap['step']};checks+=1
        assert len(rr['gradient_windows'])==4
        for window in rr['gradient_windows']:
            assert window['counts']==[256]*128
            sums=np.array(window['sums']);assert np.isfinite(sums).all()
            ki={x:i for i,x in enumerate(window['keys'])}
            assert np.all(sums[:,ki['weighted_post_norm']]<=256+1e-7)
            assert np.all(sums[:,ki['both_clipped']]<=256)
        for t in rr['trace']:
            weight=w[t['site']] if j['arm']=='C' else 1.;gn=t['weighted_norm'];un=gn/weight
            assert abs(un-t['unweighted_norm'])<1e-8*max(1,un)
            assert abs(gn*min(1,1/(gn+1e-6))-t['weighted_post_norm'])<1e-10;clipchecks+=1
        if j['arm']=='A':
            prior_run=load(prior/'runs'/j['prior_job']/'report.json')
            x=np.array([x['predicted_delta'] for x in rr['history'][-1]['sites']]);y=np.array([x['predicted_delta'] for x in prior_run['history'][-1]['sites']])
            reference_deltas[j['id']]=float(np.max(abs(x-y))) # descriptive, no old run substituted
    labels=load(prior/'evaluation_labels.json')['cases'];by={(c['parent_index'],c['position']):c for c in labels}
    results=load(root/'report.json')['results'];assert len(results)==1920;selections=0
    for r in results:
        c=by[r['parent_index'],r['position']];ids=[a for a in range(20) if a!=c['wt']];x=np.array(r['predicted_delta'])[ids];y=np.array(c['target_delta'])[:,ids];choice=int(np.argmin(x))
        for name,ns in [('old',[0,1]),('new',[2,3]),('all',[0,1,2,3])]:
            target=y[ns].mean(0);a=r['selection']['aggregate'][name];rho=float(spearmanr(target,x).statistic) if np.ptp(x) and np.ptp(target) else None
            assert (rho is None and a['spearman'] is None) or abs(rho-a['spearman'])<1e-12
            assert abs(target[choice]-target.min()-a['top1_regret'])<1e-12;selections+=1
        new=y[2:].mean(0);assert abs(new[choice]-new.min()-r['selection']['cross_noise']['regret_to_new_best'])<1e-12
        assert r['selected_teacher_geometry']==[g[ids[choice]] for g in c['teacher_geometry']]
    write_json(root/'independent_audit.json',dict(complete=True,train_sites=128,initializations=12,paired_initial_groups=4,checkpoints=checks,
                                               loss_checks=losschecks,clipping_trace_checks=clipchecks,selection_checks=selections,geometry_checks=len(results)*4,
                                               fresh_A_vs_historical_terminal_max_abs=reference_deltas,c4_calls=0,s1_calls=0,optimizer_updates=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);audit_score_objectives(p.parse_args().root)
