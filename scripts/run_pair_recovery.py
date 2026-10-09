"""Fixed paired-initialization training of a post-recycle pair-only restorer."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.models.pair_recovery import PairRecovery
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.reference_editor_multiref import multiref_update,editor_state_digest
from fastglycan.response_moments import ResponseMoments
from fastglycan.paired_teacher_protocol import sha256,write_json
from run_recycle_lora import LoRARuntime
from run_reference_editor import state_hash


def evaluate_pair_recovery(net,opt,rt,data,folder,step,lock):
    start=time.monotonic();net.eval();b=rt.base;records=[];latent=[]
    with torch.no_grad():
        for site in b.plan['sites']:
            pi,pos=site['parent_index'],site['position_zero_based'];old=b.aa.index(site['original_aa'])
            moments=ResponseMoments();correct={};residual={}
            for aa in site['candidates']:
                item=b.item(pi,pos,aa);base=data.base(item['label']);target=data.target(item['label'])
                c=net(base,rt.prefixes[pi][0][1],pos,old,b.aa.index(aa))
                assert c[0] is base[0] and c[1] is base[1]
                moments.add(c[2]-base[2],target-base[2]);correct[aa]=c[2].cpu();residual[aa]=(c[2]-base[2]).cpu()
                xyz=np.stack([b.decode(item,c,n).cpu().numpy() for n in (0,1)]);assert np.isfinite(xyz).all()
                p=folder/'coordinates'/f'{step}_correct_{item["label"]}.npz';np.savez_compressed(p,coordinates=xyz)
                records.append(dict(path=str(p.relative_to(folder)),sha256=sha256(p),label=item['label'],arm='correct'))
            if step==lock['updates']:
                for i,aa in enumerate(site['candidates']):
                    item=b.item(pi,pos,aa);base=data.base(item['label']);donor=site['candidates'][(i+1)%19]
                    c=(base[0],base[1],base[2]+residual[donor].cuda())
                    xyz=np.stack([b.decode(item,c,n).cpu().numpy() for n in (0,1)]);assert np.isfinite(xyz).all()
                    p=folder/'coordinates'/f'{step}_mismatched_{item["label"]}.npz';np.savez_compressed(p,coordinates=xyz)
                    records.append(dict(path=str(p.relative_to(folder)),sha256=sha256(p),label=item['label'],arm='mismatched',donor=donor))
            latent.append(dict(site=site['site_key'],pdb=site['pdb_id'],parent=pi,role=site['role_n15'],moments=moments.result()))
            print('RECOVERY_EVAL_SITE',net.config['initialization'],net.config['seed'],step,site['site_key'],flush=True)
    cp=folder/'checkpoints'/f'{step}.pt'
    torch.save(dict(state_dict=net.state_dict(),optimizer=opt.state_dict(),step=step,config=net.config,lock_sha256=sha256(folder.parents[2]/'training_lock.json')),cp)
    write_json(folder/f'evaluation_{step}.json',dict(complete=True,step=step,predictions=records,latent=latent,
        checkpoint=str(cp.relative_to(folder)),sha256=sha256(cp),seconds=time.monotonic()-start))
    net.train()


def train_pair_recovery(args):
    lock=json.loads((args.root/'training_lock.json').read_text())
    for p,h in lock['code'].items():assert sha256(args.root/'code'/p)==h,p
    assert sha256(args.root/'protocol.md')==lock['protocol_sha256']
    rt=LoRARuntime(Path(lock['source']),str(args.root/f'work_{args.arm}_{args.seed}'));b=rt.base
    data=PairRecoveryData(lock['build_root'],lock['cache_manifest_sha256'])
    net=PairRecovery(list(rt.model.pairformer_stack.blocks[-2:]),args.arm,args.seed).cuda()
    pre=json.loads((args.root/'preflight.json').read_text());assert pre['complete']
    expected=pre['models'][f'{args.arm}_{args.seed}'];assert editor_state_digest(net)==expected['initial_sha256']
    opt=torch.optim.AdamW(net.parameters(),lr=lock['lr'],weight_decay=1e-4,eps=1e-8)
    out=args.root/'runs'/args.arm/str(args.seed);(out/'checkpoints').mkdir(parents=True);(out/'coordinates').mkdir()
    keys=sorted([s['site_key'] for s in b.plan['sites'] if s['role_n15']=='train'],key=lambda k:(b.sites[k]['parent_index'],b.sites[k]['position_zero_based']))
    assert keys==lock['train_sites'] and len(keys)==27
    schedule=dict(updates=lock['updates'],train_site_keys=keys);exposure={k:{a:0 for a in b.sites[k]['candidates']} for k in keys}
    guard={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()};start=time.monotonic()
    report=dict(complete=False,arm=args.arm,seed=args.seed,initial_sha256=expected['initial_sha256'],parameters=sum(p.numel() for p in net.parameters()),counts=b.counts,runtime=b.runtime)
    with (out/'history.jsonl').open('w',buffering=1) as history:
        for step in range(lock['updates']):
            net.train();opt.zero_grad(set_to_none=True);site,aas=multiref_update(schedule,b.sites,step)
            pi,pos=site['parent_index'],site['position_zero_based'];old=b.aa.index(site['original_aa']);losses=[];energies=[]
            for aa in aas:
                label=b.label(pi,pos,aa);base=data.base(label);target=data.target(label)
                c=net(base,rt.prefixes[pi][0][1],pos,old,b.aa.index(aa))
                loss=(c[2]-target).square().mean()/lock['site_scale_squared'][site['site_key']];assert torch.isfinite(loss)
                (loss/2).backward();losses.append(float(loss.detach()))
                energies.append(float((c[2].detach()-base[2]).square().mean()));exposure[site['site_key']][aa]+=1
                del c,loss,target,base
            norm=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True)
            opt.step();b.counts['updates']+=1
            history.write(json.dumps(dict(step=step+1,site=site['site_key'],aa=aas,loss=losses,predicted_residual_energy=energies,gradient_norm=float(norm),clipped=bool(norm>1)))+'\n')
            if (step+1)%128==0:
                report.update(step=step+1,seconds=time.monotonic()-start);write_json(out/'report.json',report)
                print('RECOVERY_TRAIN',args.arm,args.seed,step+1,report['seconds'],flush=True)
            if step+1 in lock['checkpoints']:
                evaluate_pair_recovery(net,opt,rt,data,out,step+1,lock)
                write_json(out/f'exposure_{step+1}.json',exposure)
    assert all(v==32 for row in exposure.values() for v in row.values())
    assert guard=={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    rt.finish();assert b.counts['recycle']==0 and b.counts['updates']==8208 and b.counts['s1']==5472
    report.update(complete=True,step=lock['updates'],seconds=time.monotonic()-start,exposure=exposure,
        history_sha256=sha256(out/'history.jsonl'),peak_allocated_bytes=torch.cuda.max_memory_allocated(),lock_sha256=sha256(args.root/'training_lock.json'))
    write_json(out/'report.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--arm',choices=['pretrained','random'],required=True);p.add_argument('--seed',type=int,required=True)
    train_pair_recovery(p.parse_args())
