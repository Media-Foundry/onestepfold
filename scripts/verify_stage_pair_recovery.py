"""Read-only checkpoint re-forwards and independent NumPy residual arithmetic."""
import argparse,json,math,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.models.stage_pair_recovery import StagePairRecovery
from fastglycan.stage_pair_data import StagePairData
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.reference_editor_multiref import editor_state_digest
from run_recycle_lora import LoRARuntime


class NumpyMoments:
    def __init__(self):self.n=0;self.pp=0.;self.tt=0.;self.pt=0.;self.error=0.;self.sp=None;self.st=None
    def add(self,p,t):
        p=p.detach().cpu().numpy().astype(np.float64);t=t.detach().cpu().numpy().astype(np.float64)
        if self.sp is None:self.sp=np.zeros_like(p);self.st=np.zeros_like(t)
        self.sp+=p;self.st+=t;self.n+=1
        self.pp+=float(np.square(p).sum());self.tt+=float(np.square(t).sum())
        self.pt+=float((p*t).sum());self.error+=float(np.square(p-t).sum())
    def check(self,record):
        cp=float(np.square(self.sp).sum())/self.n;ct=float(np.square(self.st).sum())/self.n
        dot=float((self.sp*self.st).sum())/self.n;ce=float(np.square(self.sp-self.st).sum())/self.n
        for mode,pp,tt,pt,err in [('raw',self.pp,self.tt,self.pt,self.error),('common',cp,ct,dot,ce),
                                 ('centered',max(0.,self.pp-cp),max(0.,self.tt-ct),self.pt-dot,max(0.,self.error-ce))]:
            expected=dict(target_energy=tt/self.n,predicted_energy=pp/self.n,error_energy=err/self.n,
                          nmse=err/tt,energy_ratio=pp/tt,cosine=pt/math.sqrt(pp*tt) if min(pp,tt)>1e-24 else None)
            for key,value in expected.items():
                if value is None:assert record[mode][key] is None
                else:assert math.isclose(value,record[mode][key],rel_tol=2e-8,abs_tol=1e-7),(mode,key,value,record[mode][key])


def verify_stage_checkpoints(root,arm,seed):
    begin=time.monotonic();lock=json.loads((root/'training_lock.json').read_text())
    rt=LoRARuntime(Path(lock['source']),str(root/f'verify_work_{arm}_{seed}'));b=rt.base
    data=PairRecoveryData(lock['build_root'],lock['cache_manifest_sha256'])
    stage=StagePairData(lock['stage_root'],lock['stage_manifest_sha256'])
    net=StagePairRecovery(list(rt.model.pairformer_stack.blocks[-2:]),seed).cuda().eval().requires_grad_(False)
    folder=root/'runs'/arm/str(seed);checks=[];forwards=0
    with torch.no_grad():
        for step in lock['checkpoints']:
            ev=json.loads((folder/f'evaluation_{step}.json').read_text())
            assert sha256(folder/ev['checkpoint'])==ev['sha256']
            cp=torch.load(folder/ev['checkpoint'],map_location='cpu',weights_only=False)
            net.load_state_dict(cp['state_dict']);guard=editor_state_digest(net)
            for rec in ev['latent']:
                site=b.sites[rec['site']];pi,pos=site['parent_index'],site['position_zero_based'];old=b.aa.index(site['original_aa'])
                moments=NumpyMoments();hints=NumpyMoments();residual={}
                for aa in site['candidates']:
                    label=b.label(pi,pos,aa);base=data.base(label);target=data.target(label)
                    boundary,warm,th=stage.load(label,training=site['role_n15']=='train')
                    c,st=net(base,boundary,rt.prefixes[pi][0][1],pos,old,b.aa.index(aa));forwards+=1
                    assert c[0] is base[0] and c[1] is base[1]
                    if step==0:assert torch.equal(c[2],base[2]) and torch.equal(st[0],warm)
                    moments.add(c[2]-base[2],target-base[2]);residual[aa]=(c[2]-base[2]).cpu()
                    if th is not None:hints.add(st[0]-warm,th-warm)
                moments.check(rec['moments'])
                if hints.n:hints.check(rec['hint_moments'])
                else:assert rec['hint_moments'] is None
                if step==8208:
                    mismatch=NumpyMoments()
                    for i,aa in enumerate(site['candidates']):
                        base=data.base(b.label(pi,pos,aa));target=data.target(b.label(pi,pos,aa))
                        z=base[2]+residual[site['candidates'][(i+1)%19]].cuda()
                        mismatch.add(z-base[2],target-base[2])
                    mismatch.check(rec['mismatch'])
                checks.append(dict(step=step,site=rec['site'],hint_verified=bool(hints.n)))
            # Fixed candidate-order test, entirely prediction-side.
            site=b.sites[lock['train_sites'][0]];pi,pos=site['parent_index'],site['position_zero_based'];aa=site['candidates'][0]
            base=data.base(b.label(pi,pos,aa));boundary=stage.load(b.label(pi,pos,aa))[0]
            first=net(base,boundary,rt.prefixes[pi][0][1],pos,b.aa.index(site['original_aa']),b.aa.index(aa))[0][2].clone()
            other=site['candidates'][1];ob=data.base(b.label(pi,pos,other));oz=stage.load(b.label(pi,pos,other))[0]
            net(ob,oz,rt.prefixes[pi][0][1],pos,b.aa.index(site['original_aa']),b.aa.index(other))
            again=net(base,boundary,rt.prefixes[pi][0][1],pos,b.aa.index(site['original_aa']),b.aa.index(aa))[0][2]
            assert torch.equal(first,again);forwards+=3
            assert editor_state_digest(net)==guard
    rt.finish();assert b.counts==dict(c4=0,input_embedder=0,updates=0,recycle=0,s1=0)
    write_json(folder/'tensor_verification.json',dict(complete=True,checks=checks,feature_forwards=forwards,
        seconds=time.monotonic()-begin,counts=b.counts,verifier_sha256=sha256(Path(__file__)),
        method='independent checkpoint replay and NumPyFP64'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--arm',required=True);p.add_argument('--seed',type=int,required=True)
    a=p.parse_args();verify_stage_checkpoints(a.root,a.arm,a.seed)
