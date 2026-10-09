"""Reproduce a fixed optimizer prefix, without replacing the live scientific run."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.models.stage_pair_recovery import StagePairRecovery,aligned_pair_loss
from fastglycan.stage_pair_data import StagePairData
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.pair_candidate_fit import gradient_groups
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.reference_editor_multiref import editor_state_digest,multiref_update
from run_recycle_lora import LoRARuntime


def replay_stage_prefix(root,destination):
    begin=time.monotonic();destination.mkdir(exist_ok=False)
    lock=json.loads((root/'training_lock.json').read_text())
    for name,digest in lock['code'].items():assert sha256(root/'code'/name)==digest,name
    source=root/'runs/final/272003';ev=json.loads((source/'evaluation_0.json').read_text())
    path=source/ev['checkpoint'];assert sha256(path)==ev['sha256']
    original=[json.loads(x) for x in (source/'history.jsonl').read_text().splitlines()[:1420]]
    assert len(original)==1420
    rt=LoRARuntime(Path(lock['source']),str(destination/'work'));b=rt.base
    data=PairRecoveryData(lock['build_root'],lock['cache_manifest_sha256'])
    stage=StagePairData(lock['stage_root'],lock['stage_manifest_sha256'])
    net=StagePairRecovery(list(rt.model.pairformer_stack.blocks[-2:]),272003).cuda().train()
    checkpoint=torch.load(path,map_location='cpu',weights_only=False)
    net.load_state_dict(checkpoint['state_dict'])
    assert editor_state_digest(net)==lock['initial_hashes']['272003']
    opt=torch.optim.AdamW(net.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8)
    opt.load_state_dict(checkpoint['optimizer'])
    write_json(destination/'replay_lock.json',dict(source=str(source),source_checkpoint_sha256=sha256(path),
        original_history=original,code_sha256=sha256(Path(__file__)),updates=1421,seed=272003,
        original_training_lock_sha256=sha256(root/'training_lock.json'),scientific_replacement=False))
    schedule=dict(updates=8208,train_site_keys=lock['train_sites'])
    compared=[];forwards=0
    with (destination/'history.jsonl').open('x',buffering=1) as out:
        for index in range(1421):
            trace=index>=1419;opt.zero_grad(set_to_none=True)
            site,aas=multiref_update(schedule,b.sites,index);pi,pos=site['parent_index'],site['position_zero_based']
            losses=[]
            for aa in aas:
                if trace:print('PHASE',index+1,aa,'load',time.monotonic()-begin,flush=True)
                label=b.label(pi,pos,aa);base=data.base(label);target=data.target(label)
                boundary,warm,hint=stage.load(label,training=True)
                if trace:print('PHASE',index+1,aa,'forward',time.monotonic()-begin,flush=True)
                c,stages=net(base,boundary,rt.prefixes[pi][0][1],pos,b.aa.index(site['original_aa']),b.aa.index(aa))
                loss,_=aligned_pair_loss(stages,target,hint,lock['site_scale_squared'][site['site_key']],'final')
                assert torch.isfinite(loss)
                if trace:print('PHASE',index+1,aa,'backward',time.monotonic()-begin,flush=True)
                (loss/2).backward();losses.append(float(loss.detach()));forwards+=1
                if trace:print('PHASE',index+1,aa,'backward_returned',time.monotonic()-begin,flush=True)
                del c,stages,loss,target,base,boundary,warm,hint
            if index<4 or (index+1)%256==0:
                audit=gradient_groups(net);assert not audit['missing']
            if trace:print('PHASE',index+1,'clip',time.monotonic()-begin,flush=True)
            norm=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True)
            if trace:print('PHASE',index+1,'optimizer',time.monotonic()-begin,flush=True)
            opt.step();b.counts['updates']+=1
            row=dict(step=index+1,site=site['site_key'],aa=aas,loss=losses,gradient_norm=float(norm),clipped=bool(norm>1))
            if index<1420:
                old=original[index];assert all(row[k]==old[k] for k in ('step','site','aa'))
                expected=np.array(old['loss']+[old['gradient_norm']]);actual=np.array(losses+[float(norm)])
                delta=np.abs(actual-expected);relative=delta/np.maximum(np.abs(expected),1e-12)
                comparison=dict(step=index+1,exact=bool(np.array_equal(actual,expected)),
                                max_absolute=float(delta.max()),max_relative=float(relative.max()))
                compared.append(comparison);row['comparison']=comparison
            out.write(json.dumps(row)+'\n')
            if (index+1)%128==0:print('REPLAY_UPDATE',index+1,time.monotonic()-begin,flush=True)
            if index+1 in (1420,1421):
                cp=destination/f'{index+1}.pt';torch.save(dict(state_dict=net.state_dict(),optimizer=opt.state_dict(),
                    step=index+1,config=net.config),cp)
                print('REPLAY_CHECKPOINT',index+1,sha256(cp),flush=True)
    rt.finish();assert b.counts==dict(c4=0,input_embedder=0,recycle=0,s1=0,updates=1421)
    write_json(destination/'result.json',dict(complete=True,counts=b.counts,training_forwards=forwards,
        source_checkpoint_sha256=sha256(path),compared_updates=len(compared),
        exact_updates=sum(x['exact'] for x in compared),
        max_absolute=max(x['max_absolute'] for x in compared),max_relative=max(x['max_relative'] for x in compared),
        next_update_completed=True,scientific_replacement=False,seconds=time.monotonic()-begin))
    print('REPLAY_COMPLETE',time.monotonic()-begin,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--destination',type=Path,required=True)
    a=p.parse_args();replay_stage_prefix(a.root,a.destination)
