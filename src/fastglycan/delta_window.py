"""Native mid-depth operand observation and disjoint contraction timing."""
import numpy as np
from fastglycan.delta_propagation import delta_statistics

WINDOW_DEPTHS=(8,12,16,24,32,40,48)


def window_statistics(reference,candidate,position):
    result=delta_statistics(reference,candidate,position,spectral=False)
    if not result['comparable']:raise ValueError('unaligned window tensors')
    delta=candidate.astype(np.float64)-reference.astype(np.float64)
    if delta.ndim!=3 or delta.shape[0]!=delta.shape[1]:return result
    rows=[]
    for channel in range(delta.shape[-1]):
        d=delta[:,:,channel]
        s=np.linalg.svd(d,compute_uv=False);energy=s*s;total=float(energy.sum())
        cumulative=np.cumsum(energy)/total if total else np.ones(len(s))
        row=dict(channel=channel,energy=total,zero_delta=total==0)
        for q in (90,95,99):row[f'r{q}']=int(np.searchsorted(cumulative,q/100)+1) if total else 0
        for r in (2,4,8,16,24,32,48,64):
            row[f'energy_r{r}']=float(cumulative[min(r,len(s))-1]) if total else None
        outside=d.copy();outside[position,:]=0;outside[:,position]=0
        row['outside_energy_fraction']=float(np.square(outside).sum()/total) if total else 0
        rows.append(row)
    result['channels']=rows
    return result


class DeltaWindowObserver:
    """Observe actual A/B and block states at locked depths; preserve native math."""
    def __init__(self,model):
        self.model=model;self.handles=[];self.originals=[];self.values={};self.cycle=0

    def selected(self,depth):
        return (self.cycle==1 and depth in WINDOW_DEPTHS) or (self.cycle in (2,3,4) and depth==1)

    def save(self,name,tensor):
        if name in self.values:raise RuntimeError('duplicate observation '+name)
        self.values[name]=tensor.detach().float().cpu().numpy().copy()

    def __enter__(self):
        def pre_msa(m,args,kwargs):
            self.cycle+=1
            if self.cycle in (2,3,4):self.save(f'c{self.cycle}.msa_input',args[1] if len(args)>1 else kwargs['z'])
        def post_msa(m,args,out):
            if self.cycle in (2,3,4):self.save(f'c{self.cycle}.msa_output',out)
        self.handles.extend([self.model.msa_module.register_forward_pre_hook(pre_msa,with_kwargs=True),
                             self.model.msa_module.register_forward_hook(post_msa)])
        for index,block in enumerate(self.model.pairformer_stack.blocks):
            depth=index+1
            if depth not in (*WINDOW_DEPTHS,1):continue
            def pre_block(m,args,kwargs,d=depth):
                if self.selected(d):self.save(f'c{self.cycle}.b{d}.input',args[1] if len(args)>1 else kwargs['z'])
            def post_block(m,args,out,d=depth):
                if self.selected(d):self.save(f'c{self.cycle}.b{d}.output',out[1])
            self.handles.extend([block.register_forward_pre_hook(pre_block,with_kwargs=True),block.register_forward_hook(post_block)])
            for direction in ('out','in'):
                mod=getattr(block,'tri_mul_'+direction);original=mod._combine_projections
                if '_combine_projections' in mod.__dict__:raise RuntimeError('preexisting operand override')
                self.originals.append(mod)
                def combine(a,b,*args,_original=original,_d=depth,_direction=direction,**kwargs):
                    if self.selected(_d):
                        self.save(f'c{self.cycle}.b{_d}.{_direction}.A',a)
                        self.save(f'c{self.cycle}.b{_d}.{_direction}.B',b)
                    return _original(a,b,*args,**kwargs)
                mod._combine_projections=combine
        return self

    def __exit__(self,*args):
        for h in self.handles:h.remove()
        for m in self.originals:del m.__dict__['_combine_projections']


class ContractionTimer:
    """Separate whole-TriMul and contraction events. Never sum these nested levels."""
    def __init__(self,model):
        self.model=model;self.handles=[];self.originals=[];self.events=[];self.pending={};self.cycle=0

    def __enter__(self):
        import torch
        def start_cycle(m,a):self.cycle+=1
        self.handles.append(self.model.pairformer_stack.register_forward_pre_hook(start_cycle))
        for index,block in enumerate(self.model.pairformer_stack.blocks):
            for direction in ('out','in'):
                tag=f'b{index+1}.{direction}';mod=getattr(block,'tri_mul_'+direction)
                def pre(m,a,t=tag):
                    event=torch.cuda.Event(enable_timing=True);event.record();self.pending[t]=event
                def post(m,a,out,t=tag):
                    event=torch.cuda.Event(enable_timing=True);event.record()
                    self.events.append((self.cycle,t,'trimul',self.pending.pop(t),event))
                self.handles.extend([mod.register_forward_pre_hook(pre),mod.register_forward_hook(post)])
                original=mod._combine_projections
                if '_combine_projections' in mod.__dict__:raise RuntimeError('preexisting timing override')
                self.originals.append(mod)
                def combine(a,b,*args,_orig=original,_tag=tag,**kwargs):
                    start=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
                    start.record();out=_orig(a,b,*args,**kwargs);end.record()
                    self.events.append((self.cycle,_tag,'contraction',start,end))
                    return out
                mod._combine_projections=combine
        return self

    def rows(self):
        return [dict(cycle=c,module=t,kind=k,ms=a.elapsed_time(b)) for c,t,k,a,b in self.events]

    def __exit__(self,*args):
        for h in self.handles:h.remove()
        for m in self.originals:del m.__dict__['_combine_projections']
