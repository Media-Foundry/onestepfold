"""Discarded native dry updates and timing; no model/quality selection."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.models.pair_recovery import PairRecovery
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.reference_editor_multiref import editor_state_digest
from fastglycan.paired_teacher_protocol import sha256,write_json
from run_recycle_lora import LoRARuntime
from run_reference_editor import state_hash


def preflight_pair_recovery(root):
    cfg=json.loads((root/'setup.json').read_text());rt=LoRARuntime(Path(cfg['source']),str(root/'preflight_work'));b=rt.base
    data=PairRecoveryData(cfg['build_root'],cfg['cache_manifest_sha256']);keys=cfg['train_sites'];site=b.sites['p3_s37']
    report=dict(complete=False,models={},runtime=b.runtime,counts=b.counts);guards={p:state_hash(v[0]) for p,v in rt.prefixes.items()}
    for seed in (272001,272003):
        common=None
        for arm in ('pretrained','random'):
            net=PairRecovery(list(rt.model.pairformer_stack.blocks[-2:]),arm,seed).cuda();initial=editor_state_digest(net)
            h=state_hash(tuple(v for n,v in net.state_dict().items() if not n.startswith('blocks.')))
            if common is not None:assert h==common
            common=h
            for i,block in enumerate(net.blocks):
                for n,p in block.named_parameters():
                    source=rt.model.pairformer_stack.blocks[i+14].get_parameter(n)
                    assert p.data_ptr()!=source.data_ptr()
                    if arm=='pretrained':assert torch.equal(p,source)
            item=b.item(3,36,site['candidates'][0]);base=data.base(item['label']);ref=rt.prefixes[3][0][1]
            with torch.no_grad():
                c=net(base,ref,36,b.aa.index('T'),b.aa.index(site['candidates'][0]))
                assert all(torch.equal(x,y) for x,y in zip(c,base))
                rec=rt.preflight['baseline'][item['label']];path=Path(rt.lock['native_root'])/rec['path'];assert sha256(path)==rec['sha256']
                expected=np.load(path)['coordinates']
                for ni in (0,1):assert np.array_equal(b.decode(item,c,ni).cpu().numpy(),expected[ni])
                assert net(base,ref,36,0,0) is base
            opt=torch.optim.AdamW(net.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8);steps=[]
            torch.cuda.synchronize();start=time.perf_counter()
            for step in range(4):
                opt.zero_grad(set_to_none=True);ss=b.sites[keys[step%3]];pi,pos=ss['parent_index'],ss['position_zero_based']
                losses=[]
                for aa in ss['candidates'][:2]:
                    label=b.label(pi,pos,aa);base=data.base(label);target=data.target(label)
                    c=net(base,rt.prefixes[pi][0][1],pos,b.aa.index(ss['original_aa']),b.aa.index(aa))
                    loss=(c[2]-target).square().mean()/cfg['site_scale_squared'][ss['site_key']];(loss/2).backward();losses.append(float(loss.detach()))
                norms={n:None if p.grad is None else float(p.grad.norm()) for n,p in net.named_parameters()}
                assert all(v is not None and np.isfinite(v) for v in norms.values())
                assert norms['out.weight']>0
                if step>0:
                    assert sum(v for n,v in norms.items() if n.startswith('blocks.'))>0
                    assert sum(v for n,v in norms.items() if n.startswith('node.'))>0
                gn=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True);opt.step()
                steps.append(dict(step=step,losses=losses,gradient_norm=float(gn),norms=norms))
            torch.cuda.synchronize();dry_seconds=time.perf_counter()-start
            with torch.no_grad():
                base=data.base(item['label']);a=net(base,ref,36,b.aa.index('T'),b.aa.index(site['candidates'][0]))
                net(base,ref,36,b.aa.index('T'),b.aa.index(site['candidates'][1]));again=net(base,ref,36,b.aa.index('T'),b.aa.index(site['candidates'][0]))
                assert torch.equal(a[2],again[2]);assert a[0] is base[0] and a[1] is base[1]
                times=[]
                for rep in range(4):
                    torch.cuda.synchronize();t=time.perf_counter()
                    for j in range(10):net(base,ref,36,b.aa.index('T'),b.aa.index(site['candidates'][0]))
                    torch.cuda.synchronize();times.append((time.perf_counter()-t)/10)
            assert all(p.grad is None for p in rt.model.parameters())
            fresh=PairRecovery(list(rt.model.pairformer_stack.blocks[-2:]),arm,seed)
            assert editor_state_digest(fresh)==initial
            del fresh
            report['models'][f'{arm}_{seed}']=dict(initial_sha256=initial,common_sha256=h,parameters=sum(p.numel() for p in net.parameters()),
                dry_steps=steps,discarded_updates=4,dry_seconds=dry_seconds,resident_recovery_seconds=times[1:])
            del net,opt,c,loss,a,again
    with torch.no_grad():
        item=b.item(3,36,site['candidates'][0]);base=data.base(item['label']);timing={}
        for kind in ('native_last','s1'):
            times=[]
            for rep in range(4):
                torch.cuda.synchronize();t=time.perf_counter()
                for j in range(10):
                    if kind=='native_last':rt.conditioning(None,site,site['candidates'][0])
                    else:b.decode(item,base,0)
                torch.cuda.synchronize();times.append((time.perf_counter()-t)/10)
            timing[kind]=times[1:]
    assert guards=={p:state_hash(v[0]) for p,v in rt.prefixes.items()};rt.finish()
    report.update(complete=True,timing=timing,counts=b.counts,peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        setup_sha256=sha256(root/'setup.json'),main_training_updates=0)
    write_json(root/'preflight.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);preflight_pair_recovery(p.parse_args().root)
