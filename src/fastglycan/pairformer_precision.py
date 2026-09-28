"""Extended-state recycle cuts and isolated precision references."""
from contextlib import contextmanager
import copy
import torch
import torch.nn.functional as F
from .esm_interface_diagnostics import EARLY_NAMES,early_features
from .interface_decomposition import make_interface,dot64


def cast_tree(value,dtype,device=None):
    if isinstance(value,torch.Tensor):return value.to(device=device,dtype=dtype if value.is_floating_point() else value.dtype)
    if isinstance(value,dict):return {k:cast_tree(v,dtype,device) for k,v in value.items()}
    if isinstance(value,list):return [cast_tree(v,dtype,device) for v in value]
    if isinstance(value,tuple):return tuple(cast_tree(v,dtype,device) for v in value)
    return value


class PairformerStages(torch.nn.Module):
    """Same eval arithmetic as full_recycle_pairformer, with carried initializers."""
    def __init__(self,model,fixed):
        super().__init__();self.model=model;self.fixed=fixed;self.reads=set()
    def features(self,state):
        owner=self
        class Reads(dict):
            def __getitem__(self,key):owner.reads.add(key);return super().__getitem__(key)
        return Reads(early_features(self.fixed,{k:state[k] for k in EARLY_NAMES}))
    def initialize(self,c):
        m=self.model;f=self.features(c)
        si=m.input_embedder(f,inplace_safe=False,chunk_size=None)
        sc=m.linear_no_bias_sinit(si)
        zc=m.linear_no_bias_zinit1(sc)[...,None,:]+m.linear_no_bias_zinit2(sc)[...,None,:,:]
        zc=zc+m.relative_position_encoding(f['relp'])
        zc=zc+m.linear_no_bias_token_bond(f['token_bonds'].unsqueeze(-1))
        if 'constraint_feature' in f:
            constraint=m.constraint_embedder(f['constraint_feature'])
            if constraint is not None:zc=zc+constraint
        return dict(s=torch.zeros_like(sc),z=torch.zeros_like(zc),s_init=sc,z_init=zc,s_inputs=si,**c)
    def recycle(self,state):
        m=self.model;f=self.features(state)
        z=state['z_init']+m.linear_no_bias_z_cycle(m.layernorm_z_cycle(state['z']))
        if m.template_embedder.n_blocks>0:
            z=z+m.template_embedder(f,z,triangle_multiplicative=m.configs.triangle_multiplicative,triangle_attention=m.configs.triangle_attention,inplace_safe=False,chunk_size=None)
        z=m.msa_module(f,z,state['s_inputs'],pair_mask=None,triangle_multiplicative=m.configs.triangle_multiplicative,triangle_attention=m.configs.triangle_attention,inplace_safe=False,chunk_size=None)
        s=state['s_init']+m.linear_no_bias_s(m.layernorm_s(state['s']))
        s,z=m.pairformer_stack(s,z,pair_mask=None,triangle_multiplicative=m.configs.triangle_multiplicative,triangle_attention=m.configs.triangle_attention,inplace_safe=False,chunk_size=None)
        return state|dict(s=s,z=z)
    def step(self,index,state):return self.initialize(state) if index==0 else self.recycle(state)
    def trace(self,c):
        states=[c]
        for index in range(5):states.append(self.step(index,states[-1]))
        return states
    def final(self,state):return make_interface((state['s_inputs'],state['s'],state['z']),state)


def pullback(function,state,cotangent):
    x={k:v.detach().requires_grad_(True) for k,v in state.items()}
    y=function(x);active=[k for k in y if y[k].requires_grad]
    gs=torch.autograd.grad(tuple(y[k] for k in active),tuple(x.values()),grad_outputs=tuple(cotangent[k] for k in active),allow_unused=True)
    return {k:(torch.zeros_like(v) if g is None else g).detach() for (k,v),g in zip(x.items(),gs)}, {k:v.detach() for k,v in y.items()}


def tree_dot(a,b):return sum(dot64(a[k],b[k]) for k in a)


def reference_copy(native,dtype):
    result=copy.deepcopy(native).to(dtype=dtype).eval().requires_grad_(False)
    result.fixed=cast_tree(native.fixed,dtype)
    changed=[]
    for name,m in result.named_modules():
        if hasattr(m,'precision') and m.precision is not None:
            changed.append(dict(module=name,precision=str(m.precision)));m.precision=dtype
        if hasattr(m,'blocks_per_ckpt'):m.blocks_per_ckpt=None
    for name,p in native.named_parameters():assert torch.equal(p.double(),dict(result.named_parameters())[name].double()),name
    return result,changed


@contextmanager
def reference_attention(records=None):
    import protenix.model.modules.primitives as primitives
    native=primitives._attention
    def attention(q,k,v,attn_bias=None,use_efficient_implementation=True,inplace_safe=False):
        if q.dtype!=torch.float64:
            y=native(q,k,v,attn_bias,use_efficient_implementation,inplace_safe)
        elif use_efficient_implementation:
            y=F.scaled_dot_product_attention(q,k,v,attn_mask=attn_bias,scale=1.0)
        else:
            logits=q@k.transpose(-1,-2)
            if attn_bias is not None:logits=logits+attn_bias
            y=F.softmax(logits,dim=-1,dtype=torch.float64)@v
        if records is not None:records.append(dict(q=str(q.dtype),output=str(y.dtype),efficient=use_efficient_implementation))
        return y
    primitives._attention=attention
    try:yield
    finally:primitives._attention=native
