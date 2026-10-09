"""Fixed native-aligned pair fitting, with explicit optional stage14 supervision."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from fastglycan.models.stage_pair_recovery import StagePairRecovery, aligned_pair_loss
from fastglycan.stage_pair_data import StagePairData
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.pair_candidate_fit import gradient_groups
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.reference_editor_multiref import editor_state_digest,multiref_update
from fastglycan.response_moments import ResponseMoments
from run_recycle_lora import LoRARuntime
from run_reference_editor import state_hash


def run_stage_recovery(root,arm,seed):
    begin=time.monotonic();lock=json.loads((root/'training_lock.json').read_text())
    for name,digest in lock['code'].items():assert sha256(root/'code'/name)==digest,name
    assert sha256(root/'protocol.md')==lock['protocol_sha256']
    rt=LoRARuntime(Path(lock['source']),str(root/f'work_{arm}_{seed}'));b=rt.base
    data=PairRecoveryData(lock['build_root'],lock['cache_manifest_sha256'])
    stage_data=StagePairData(lock['stage_root'],lock['stage_manifest_sha256'])
    net=StagePairRecovery(list(rt.model.pairformer_stack.blocks[-2:]),seed).cuda()
    initial=editor_state_digest(net);assert initial==lock['initial_hashes'][str(seed)]
    initial_params={n:p.detach().cpu().clone() for n,p in net.named_parameters()}
    opt=torch.optim.AdamW(net.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8)
    folder=root/'runs'/arm/str(seed);(folder/'checkpoints').mkdir(parents=True);(folder/'coordinates').mkdir()
    train_keys=lock['train_sites'];eval_keys=lock['eval_sites']
    assert set(train_keys)<=set(s['site_key'] for s in b.plan['sites'] if s['role_n15']=='train')
    schedule=dict(updates=8208,train_site_keys=train_keys)
    exposure={k:dict.fromkeys(b.sites[k]['candidates'],0) for k in train_keys}
    guard={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    report=dict(complete=False,arm=arm,seed=seed,initial_sha256=initial,parameters=sum(p.numel() for p in net.parameters()),
                counts=b.counts,runtime=b.runtime,gradient_audits=[],training_forwards=0,evaluation_forwards=0)

    def evaluate(step):
        start=time.monotonic();net.eval();rows=[];latent=[]
        with torch.no_grad():
            for key in eval_keys:
                site=b.sites[key];pi,pos=site['parent_index'],site['position_zero_based'];old=b.aa.index(site['original_aa'])
                moments=ResponseMoments();hints=ResponseMoments();mismatch=ResponseMoments();residual={}
                for aa in site['candidates']:
                    item=b.item(pi,pos,aa);label=item['label'];base=data.base(label);target=data.target(label)
                    # Held hints are never generated. TRAIN hint use here is evaluation only.
                    boundary,warm,teacher_hint=stage_data.load(label,training=site['role_n15']=='train')
                    c,stages=net(base,boundary,rt.prefixes[pi][0][1],pos,old,b.aa.index(aa));report['evaluation_forwards']+=1
                    assert c[0] is base[0] and c[1] is base[1]
                    if step==0:assert torch.equal(c[2],base[2]) and torch.equal(stages[0],warm)
                    moments.add(c[2]-base[2],target-base[2])
                    if teacher_hint is not None:hints.add(stages[0]-warm,teacher_hint-warm)
                    residual[aa]=(c[2]-base[2]).cpu()
                    xyz=np.stack([b.decode(item,c,ni).cpu().numpy() for ni in (0,1)]);assert np.isfinite(xyz).all()
                    if step==0:
                        rec=rt.preflight['baseline'][label];path=Path(rt.lock['native_root'])/rec['path']
                        assert sha256(path)==rec['sha256'] and np.array_equal(xyz,np.load(path)['coordinates'])
                    path=folder/'coordinates'/f'{step}_correct_{label}.npz';np.savez_compressed(path,coordinates=xyz)
                    rows.append(dict(path=str(path.relative_to(folder)),sha256=sha256(path),label=label,arm='correct'))
                if step==8208:
                    for i,aa in enumerate(site['candidates']):
                        donor=site['candidates'][(i+1)%19];item=b.item(pi,pos,aa);base=data.base(item['label'])
                        c=(base[0],base[1],base[2]+residual[donor].cuda())
                        mismatch.add(c[2]-base[2],data.target(item['label'])-base[2])
                        xyz=np.stack([b.decode(item,c,ni).cpu().numpy() for ni in (0,1)]);assert np.isfinite(xyz).all()
                        path=folder/'coordinates'/f'{step}_mismatched_{item["label"]}.npz';np.savez_compressed(path,coordinates=xyz)
                        rows.append(dict(path=str(path.relative_to(folder)),sha256=sha256(path),label=item['label'],arm='mismatched',donor=donor))
                latent.append(dict(site=key,pdb=site['pdb_id'],parent=pi,role=site['role_n15'],moments=moments.result(),
                                   hint_moments=hints.result() if hints.n else None,mismatch=mismatch.result() if mismatch.n else None))
                print('ALIGNED_EVAL',lock['cohort'],arm,seed,step,key,flush=True)
        cp=folder/'checkpoints'/f'{step}.pt';torch.save(dict(state_dict=net.state_dict(),optimizer=opt.state_dict(),step=step,
            config=net.config,lock_sha256=sha256(root/'training_lock.json')),cp)
        movement={}
        for n,p in net.named_parameters():
            group='.'.join(n.split('.')[:2]) if n.startswith('blocks.') else n.split('.')[0]
            movement[group]=movement.get(group,0.)+float((p.detach().cpu().double()-initial_params[n].double()).square().sum())
        write_json(folder/f'evaluation_{step}.json',dict(complete=True,step=step,latent=latent,predictions=rows,
            exposure=exposure,checkpoint=str(cp.relative_to(folder)),sha256=sha256(cp),
            parameter_movement_squared=movement,seconds=time.monotonic()-start))
        net.train()

    evaluate(0)
    with (folder/'history.jsonl').open('x',buffering=1) as history:
        for step in range(8208):
            opt.zero_grad(set_to_none=True);site,aas=multiref_update(schedule,b.sites,step)
            pi,pos=site['parent_index'],site['position_zero_based'];old=b.aa.index(site['original_aa']);losses=[];parts=[]
            for aa in aas:
                label=b.label(pi,pos,aa);base=data.base(label);target=data.target(label)
                boundary,warm,teacher_hint=stage_data.load(label,training=True)
                c,stages=net(base,boundary,rt.prefixes[pi][0][1],pos,old,b.aa.index(aa))
                loss,part=aligned_pair_loss(stages,target,teacher_hint,lock['site_scale_squared'][site['site_key']],arm)
                assert torch.isfinite(loss);(loss/2).backward()
                losses.append(float(loss.detach()));parts.append({k:float(v) for k,v in part.items()})
                exposure[site['site_key']][aa]+=1;report['training_forwards']+=1
                del c,stages,loss,target,base,boundary,warm,teacher_hint
            if step<4 or (step+1)%256==0:
                audit=gradient_groups(net);assert not audit['missing']
                assert all(np.isfinite(v) for v in audit['norms'].values())
                assert audit['norms']['blocks.0']>0 and audit['norms']['blocks.1']>0
                report['gradient_audits'].append(dict(step=step+1,**audit))
            norm=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True);opt.step();b.counts['updates']+=1
            history.write(json.dumps(dict(step=step+1,site=site['site_key'],aa=aas,loss=losses,loss_parts=parts,
                                          gradient_norm=float(norm),clipped=bool(norm>1)))+'\n')
            if (step+1)%128==0:
                report.update(step=step+1,seconds=time.monotonic()-begin);write_json(folder/'report.json',report)
                print('ALIGNED_TRAIN',lock['cohort'],arm,seed,step+1,report['seconds'],flush=True)
            if step+1 in lock['checkpoints']:evaluate(step+1)
    assert all(n==lock['exposures'] for row in exposure.values() for n in row.values())
    assert guard=={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    assert all(p.grad is None for p in rt.model.parameters());rt.finish()
    expected=38*len(eval_keys)*(len(lock['checkpoints'])+1)
    assert b.counts==dict(s1=expected,updates=8208,recycle=0,c4=0,input_embedder=0)
    assert report['training_forwards']==16416
    report.update(complete=True,step=8208,exposure=exposure,seconds=time.monotonic()-begin,
                  final_sha256=editor_state_digest(net),history_sha256=sha256(folder/'history.jsonl'),
                  peak_allocated_bytes=torch.cuda.max_memory_allocated(),lock_sha256=sha256(root/'training_lock.json'))
    write_json(folder/'report.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--arm',choices=['final','hint'],required=True);p.add_argument('--seed',type=int,required=True)
    a=p.parse_args();run_stage_recovery(a.root,a.arm,a.seed)
