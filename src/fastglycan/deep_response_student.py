"""Deep Validation v2 models: controlled capacity, edge content, output and inputs."""
import copy
import math
import torch
from torch import nn
from fastglycan.factor_student import FactorStudent, FactorNodeBlock, expand_pair_factors


class PairContentBlock(nn.Module):
    """Quadratic edge-value messages, compensated FF width (not triangle updates)."""
    def __init__(self, base, channels=128):
        super().__init__();self.heads=base.heads;self.width=base.width
        self.norm=copy.deepcopy(base.norm);self.qkv=copy.deepcopy(base.qkv);self.output=copy.deepcopy(base.output)
        self.edge=nn.Sequential(nn.LayerNorm(channels),nn.Linear(channels,self.width,bias=False))
        cost=channels*self.width+2*channels
        hidden=4*self.width-round(cost/(2*self.width+1))
        self.ff=nn.Sequential(copy.deepcopy(base.ff[0]),nn.Linear(self.width,hidden),nn.GELU(),nn.Linear(hidden,self.width))
        with torch.no_grad():
            self.ff[1].weight.copy_(base.ff[1].weight[:hidden]);self.ff[1].bias.copy_(base.ff[1].bias[:hidden])
            self.ff[3].weight.copy_(base.ff[3].weight[:,:hidden]);self.ff[3].bias.copy_(base.ff[3].bias)

    def forward(self,h,pair_bias,wt_z):
        batch,length,width=h.shape;heads=self.heads;dh=width//heads
        q,k,v=self.qkv(self.norm(h)).reshape(batch,length,3,heads,dh).permute(2,0,3,1,4).unbind(0)
        alpha=torch.softmax((q@k.transpose(-1,-2))/math.sqrt(dh)+pair_bias[None],dim=-1)
        edge=self.edge(wt_z).reshape(length,length,heads,dh)
        message=torch.einsum('ahjk,jkhd->ahjd',alpha,edge)
        message=alpha@v+torch.sigmoid(q)*message
        h=h+self.output(message.transpose(1,2).reshape(batch,length,width))
        return h+self.ff(h)


class DeepResponseStudent(FactorStudent):
    """No target s/z ever enter. Optional s_inputs is an explicitly oracle input."""
    def __init__(self,size='small',content=False,output='factor',input_mode='none',length=84,
                 single_channels=384,pair_channels=128,rank=32,input_channels=449):
        if size not in ('small','large') or output not in ('factor','dense') or input_mode not in ('none','wt','site','full'):
            raise ValueError('unsupported diagnostic configuration')
        width=128 if size=='small' else 256
        super().__init__(single_channels,pair_channels,rank,width)
        if size=='large':self.blocks.extend(FactorNodeBlock(width,4) for _ in range(2))
        if content:self.blocks=nn.ModuleList(PairContentBlock(block,pair_channels) for block in self.blocks)
        self.content=content;self.output_mode=output;self.input_mode=input_mode;self.length=length
        if input_mode!='none':self.input_projection=nn.Sequential(nn.LayerNorm(input_channels),nn.Linear(input_channels,width))
        if output=='dense':
            del self.u,self.v
            self.dense=nn.Linear(width,length*pair_channels);nn.init.zeros_(self.dense.weight);nn.init.zeros_(self.dense.bias)

    def node_response(self,wt_s,wt_z,position,wt_aa,candidate_aa,wt_inputs=None,target_inputs=None):
        aa=torch.as_tensor(candidate_aa,device=wt_s.device,dtype=torch.long).reshape(-1)
        if wt_s.ndim!=2 or wt_z.shape[:2]!=(len(wt_s),len(wt_s)):raise ValueError('invalid WT shape')
        if not 0<=position<len(wt_s) or not 0<=wt_aa<20 or torch.any((aa<0)|(aa>=20)):raise ValueError('invalid query')
        p=torch.arange(len(wt_s),device=wt_s.device);offset=(p-position).clamp(-32,32)+32
        s=self.single(wt_s);context=s+s[position]+self.site_pair(torch.cat([wt_z[position],wt_z[:,position]],-1))+self.global_pair(torch.cat([wt_z.mean(0),wt_z.mean(1)],-1))+self.offset(offset)
        h=context[None]+(self.query(aa)-self.query.weight[wt_aa])[:,None]
        if self.input_mode!='none':
            if wt_inputs is None:raise ValueError('explicit WT s_inputs required')
            extra=wt_inputs[None].expand(len(aa),-1,-1)
            if self.input_mode in ('site','full'):
                if target_inputs is None or target_inputs.shape!=extra.shape:raise ValueError('oracle s_inputs required')
                if self.input_mode=='full':extra=target_inputs
                else:extra=extra.clone();extra[:,position]=target_inputs[:,position]
            h=h+self.input_projection(extra)
        h=self.mix(h);bias=self.bias(wt_z).permute(2,0,1)
        for block in self.blocks:h=block(h,bias,wt_z) if self.content else block(h,bias)
        return h,aa

    def factors(self,*args,**kwargs):
        if self.output_mode!='factor':raise ValueError('dense diagnostic has no factors')
        h,aa=self.node_response(*args,**kwargs);shape=(*h.shape[:2],self.pair_channels,self.rank)
        wt_aa=args[3] if len(args)>3 else kwargs['wt_aa']
        return self.u(h).reshape(shape),self.v(h).reshape(shape)*(aa!=wt_aa)[:,None,None,None]

    def forward(self,wt_s,wt_z,position,wt_aa,candidate_aa,wt_inputs=None,target_inputs=None):
        args=(wt_s,wt_z,position,wt_aa,candidate_aa,wt_inputs,target_inputs)
        if self.output_mode=='factor':return expand_pair_factors(*self.factors(*args))
        if len(wt_s)!=self.length:raise ValueError('fixed-length dense diagnostic cannot transfer length')
        h,aa=self.node_response(*args)
        return self.dense(h).reshape(len(aa),self.length,self.length,self.pair_channels)*(aa!=wt_aa)[:,None,None,None]


def response_diagnostics(prediction,target):
    p=prediction.detach().double();t=target.detach().double();axes=(1,2,3)
    pc=p-p.mean(0,keepdim=True);tc=t-t.mean(0,keepdim=True)
    nmse=(p-t).square().mean(axes)/t.square().mean(axes).clamp_min(1e-6)
    return dict(nmse=nmse.tolist(),mean_nmse=float(nmse.mean()),
                energy_ratio=float(p.square().sum()/t.square().sum().clamp_min(1e-30)),
                centered_nmse=float((pc-tc).square().sum()/tc.square().sum().clamp_min(1e-30)),
                centered_energy_ratio=float(pc.square().sum()/tc.square().sum().clamp_min(1e-30)))


def fit_gate(records,threshold=.10):
    return len(records)==2 and all(r['mean_nmse']<=threshold for r in records)


def transfer_gate(records,threshold=.80):
    return len(records)==2 and all(r['mean_nmse']<threshold and r['centered_nmse']<threshold for r in records)
