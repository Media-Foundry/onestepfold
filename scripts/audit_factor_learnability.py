"""Terminal replay and independent metric audit; never updates a parameter."""
import argparse,gzip,json
from pathlib import Path
import numpy as np
import torch
from scipy.stats import spearmanr
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.factor_student import FactorStudent
from fastglycan.scaling_metrics import lddt_observed


def audit_memorization(root):
    lock=json.loads((root/'lock.json').read_text());store=FactorTeacherStore(Path(lock['teachers']),training_only=True);torch.set_num_threads(1)
    assert sha256(Path(lock['teachers'])/'teacher_lock.json')==lock['teacher_lock_sha256']
    assert sha256(Path(lock['teachers'])/'teacher_manifest.json')==lock['teacher_manifest_sha256']
    checks=[]
    for path in sorted(root.glob('stage_*/report.json')):
        report=json.loads(path.read_text());assert report['complete'] and report['s1_calls']==report['c4_calls']==0
        checkpoint=path.parent/'final.pt';assert sha256(checkpoint)==report['checkpoint_sha256']
        saved=torch.load(checkpoint,map_location='cuda',weights_only=False)
        if report['arm']!='free_factors':
            net=FactorStudent(rank=lock['rank']).cuda().eval();net.load_state_dict(saved['state_dict'])
        for site in report['history'][-1]['sites']:
            pi,pos=site['parent_index'],site['position'];assert store.rows[pi]['role']=='train'
            wt=store.load(pi);wts,wtz=[x.cuda() for x in wt['conditioning'][1:]];aa=store.lock['aa'];wtid=aa.index(wt['sequence'][pos]);ids=[j for j in range(20) if j!=wtid]
            target=torch.stack([store.load(pi,pos,aa[j])['conditioning'][2].cuda()-wtz for j in ids])
            with torch.no_grad():
                if report['arm']=='free_factors':u,v=[saved['state_dict'][str(i)] for i in range(2)]
                else:u,v=net(wts,wtz,pos,wtid,ids)
                # Independently arrange batched matrix products (no production expand/NMSE).
                pred=(u.permute(0,2,1,3)@v.permute(0,2,3,1)).permute(0,2,3,1)/np.sqrt(lock['rank'])
                errors=(pred.double()-target.double()).square().mean((1,2,3))/target.double().square().mean((1,2,3)).clamp_min(1e-6)
            maximum=float(np.max(np.abs(errors.cpu().numpy()-np.array(site['nmse']))));assert maximum<1e-5,maximum
            target64=target.double();pred64=pred.double();mean=target64.mean(0,keepdim=True)
            centered=target64-mean;pred_centered=pred64-pred64.mean(0,keepdim=True)
            checks.append(dict(run=path.parent.name,parent_index=pi,position=pos,max_nmse_error=maximum,
                oracle_shared_mean_nmse=float(((target64-mean).square().mean((1,2,3))/target64.square().mean((1,2,3)).clamp_min(1e-6)).mean()),
                centered_response_relative_squared_error=float((pred_centered-centered).square().sum()/centered.square().sum()),
                predicted_centered_energy_ratio=float(pred_centered.square().sum()/centered.square().sum()),
                shared_mean_relative_squared_error=float((pred64.mean(0)-mean[0]).square().sum()/mean.square().sum()),
                nmse_range=[float(errors.min()),float(errors.max())]))
        assert [h['step'] for h in report['history']]==list(range(0,lock['updates']+1,64))
        assert report['exposures']==lock['updates']*19
    for path in root.glob('ladder_gate_*.json'):
        gate=json.loads(path.read_text());stage=gate['stage'];values=[json.loads((root/f'stage_{stage}_{i}/report.json').read_text()) for i in range(4)]
        expected=any(all(r['history'][-1]['mean_nmse']<=lock['advance_nmse'] for r in values if r['arm']==arm) for arm in ['canonical','reconstruction']) and stage<3
        assert gate['advance']==expected
        if not expected:assert not any(root.glob(f'stage_{stage+1}_*'))
    write_json(root/'memorization_audit.json',dict(complete=True,checkpoint_replays=checks,no_validation_training=True,no_decoder_training=True,gate_recomputed=True))


def audit_sparse_oracle(root):
    sparse=root/'sparse';lock=json.loads((sparse/'lock.json').read_text());prior=Path(lock['teachers']);teacher=json.loads((prior/'teacher_lock.json').read_text());oldlock=json.loads((prior/'evaluation/lock.json').read_text())
    owner={pi:wi for wi,ps in enumerate(oldlock['assignments']) for pi in ps}
    with gzip.open(sparse/'report.json.gz','rt') as f:report=json.load(f)
    manifest=[];ranking_count=lddt_count=mask_count=reference_count=0;max_lddt=0.;seen=set();transitions={arm:dict(fixed_r32_failures=[],new_failures_relative_r32=[]) for arm in lock['arms'][3:]}
    for site in report['sites']:
        pi,pos=site['parent_index'],site['position'];assert teacher['rows'][pi]['role']=='validation';wi=next(i for i,ps in enumerate(lock['assignments']) if pi in ps);out=sparse/f'worker_{wi}';wtid=lock['aa'].index(lock['rows'][pi]['sequence'][pos]);tasks={}
        for arm in lock['arms']:
            for seed in lock['seeds']:tasks[arm,seed]=np.array([next(x['task'] for x in site['outputs'] if x['arm']==arm and x['noise']==seed and x['aa']==aa) for aa in lock['aa']])
        for row in site['ranking']:
            ids=np.arange(20) if row['includes_wt'] else np.delete(np.arange(20),wtid);x=tasks[row['arm'],row['noise']][ids];y=tasks[row['reference'],row['noise']][ids]
            assert abs(float(spearmanr(x,y).statistic)-row['spearman'])<1e-12
            assert abs(float(y[np.argsort(x,kind='stable')[0]]-y.min())-row['top1_regret'])<1e-12;ranking_count+=1
        for j,aa in enumerate(lock['aa']):
            label=f'p{pi}_wt' if j==wtid else f'p{pi}_s{pos+1}_{aa}';path=out/f'{label}_coordinates.npz';co=np.load(path)['coordinates'];oldpath=prior/f'evaluation/worker_{owner[pi]}/{label}_coordinates.npz';original=np.load(oldpath)['coordinates']
            if path not in seen:
                if j==wtid:assert np.array_equal(co,original);reference_count+=1
                else:
                    assert sha256(oldpath)==lock['prior_coordinate_hashes'][str(oldpath)]
                    for new,old in [(0,0),(1,1),(2,3)]:assert np.array_equal(co[new],original[old]);reference_count+=1
                manifest.append(dict(path=str(path.relative_to(root)),sha256=sha256(path)));seen.add(path)
            if j==wtid:continue
            masks=dict(np.load(out/f'{label}_masks.npz'));length=len(lock['rows'][pi]['sequence']);idx=np.arange(length);rowcol=(idx[:,None]==pos)|(idx[None,:]==pos)
            assert np.array_equal(masks['rowcol'],rowcol)
            assert masks['top_row_budget'].sum()==rowcol.sum() and masks['top_contact_budget'].sum()==masks['contact'].sum();mask_count+=1
            if j==next(a for a in range(20) if a!=wtid):
                inv=dict(np.load(out/f'{label}_inventory.npz'))
                for k,arm in enumerate(lock['arms']):
                    value=lddt_observed(co[k,0],co[0,0],inv['residue_ids'])['score'];saved=next(x['fidelity']['all_atom_lddt'] for x in site['outputs'] if x['arm']==arm and x['noise']==lock['seeds'][0] and x['aa']==aa)
                    max_lddt=max(max_lddt,abs(value-saved));lddt_count+=1
            for noise in lock['seeds']:
                lookup={x['arm']:x for x in site['outputs'] if x['aa']==aa and x['noise']==noise};base=lookup['baseline']['geometry']['zero_severe_strict_checked_chirality'];r32=lookup['oracle_r32']['geometry']['zero_severe_strict_checked_chirality']
                for arm in transitions:
                    now=lookup[arm]['geometry']['zero_severe_strict_checked_chirality'];identity=dict(parent_index=pi,position=pos,aa=aa,noise=noise)
                    if base and not r32 and now:transitions[arm]['fixed_r32_failures'].append(identity)
                    if r32 and not now:transitions[arm]['new_failures_relative_r32'].append(dict(identity,baseline_pass=base))
    assert len(seen)==312 and ranking_count==16*6*2*2*2 and mask_count==304 and lddt_count==112 and reference_count==920 and max_lddt<1e-12
    write_json(root/'sparse_audit.json',dict(complete=True,coordinate_packets=len(seen),prior_array_replays=reference_count,ranking_checks=ranking_count,independent_lddt_checks=lddt_count,max_lddt_error=max_lddt,mask_budget_checks=mask_count,geometry_transitions=transitions))
    write_json(root/'coordinate_manifest.json',manifest)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['memory','sparse'],required=True);a=p.parse_args()
    if a.mode=='memory':audit_memorization(a.root)
    else:audit_sparse_oracle(a.root)
