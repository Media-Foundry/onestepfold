"""Audited local ESM precision reference; never mutates the production model."""
from contextlib import contextmanager
import copy
import types
import torch
import torch.nn.functional as F
from torch.utils._python_dispatch import TorchDispatchMode
from torch.utils._pytree import tree_flatten


class Segment(torch.nn.Module):
    def __init__(self,layers=(),norm=None):
        super().__init__();self.layers=torch.nn.ModuleList(layers);self.norm=norm
    def forward(self,x):
        for layer in self.layers:
            x=layer(x,self_attn_padding_mask=None,need_head_weights=False)[0]
        return self.norm(x) if self.norm is not None else x


def _fixed_rope(self,x,seq_dimension=1):
    if x.shape[seq_dimension] != self._seq_len_cached:
        raise ValueError('frozen RoPE reference sequence changed')
    if self._cos_cached.dtype!=x.dtype or self._cos_cached.device!=x.device:
        raise ValueError('frozen RoPE dtype/device mismatch')
    return self._cos_cached,self._sin_cached


def precision_copy(native,dtype):
    ref=copy.deepcopy(native).to(dtype=dtype).eval().requires_grad_(False)
    replacements=[]
    # Explicitly lift the actual already-generated native positional tables.
    original=dict(native.named_modules())
    for name,module in ref.named_modules():
        if hasattr(module,'_cos_cached'):
            prior=original[name]
            if prior._cos_cached is None:raise ValueError('native RoPE cache not populated')
            module._cos_cached=prior._cos_cached.detach().clone().to(dtype)
            module._sin_cached=prior._sin_cached.detach().clone().to(dtype)
            module._seq_len_cached=prior._seq_len_cached
            module._update_cos_sin_tables=types.MethodType(_fixed_rope,module)
    # Support fused LayerNorm only with explicit, recorded reference replacement.
    for name,module in list(ref.named_modules()):
        if name and 'LayerNorm' in type(module).__name__ and not isinstance(module,torch.nn.LayerNorm):
            shape=tuple(module.weight.shape);eps=module.eps
            new=torch.nn.LayerNorm(shape,eps=eps,elementwise_affine=True,device=module.weight.device,dtype=dtype)
            new.load_state_dict(module.state_dict());new.eval().requires_grad_(False)
            parent_name,_,child=name.rpartition('.');parent=ref.get_submodule(parent_name) if parent_name else ref
            setattr(parent,child,new);replacements.append(dict(name=name,old_class=type(module).__module__+'.'+type(module).__name__,eps=eps,shape=shape))
    for name,parameter in native.named_parameters():
        assert torch.equal(parameter.detach().double(),dict(ref.named_parameters())[name].detach().double()),name
    return ref,replacements


@contextmanager
def reference_softmax(records=None):
    import esm.multihead_attention as attention
    native=attention.utils_softmax
    def softmax(x,dim,onnx_trace=False):
        dtype=torch.float64 if x.dtype==torch.float64 else torch.float32
        y=F.softmax(x,dim=dim,dtype=dtype)
        if records is not None:records.append((str(x.dtype),str(y.dtype)))
        return y
    attention.utils_softmax=softmax
    try:yield
    finally:attention.utils_softmax=native


class FloatingDtypeAudit(TorchDispatchMode):
    """Record all floating tensor output dtypes, including intermediate operators."""
    def __init__(self):super().__init__();self.counts={};self.non_double=[]
    def __torch_dispatch__(self,func,types,args=(),kwargs=None):
        out=func(*args,**(kwargs or {}))
        for t in tree_flatten(out)[0]:
            if isinstance(t,torch.Tensor) and t.is_floating_point():
                key=str(t.dtype);self.counts[key]=self.counts.get(key,0)+1
                if t.dtype!=torch.float64:self.non_double.append(str(func))
        return out


def precision_decomposition(s32,a32,s64,a64,h):
    forward=s32-s64;remainder=s64-a64;ad=a64-a32
    return dict(S32=s32,A32=a32,S64=s64,A64=a64,
                forward_difference=forward,reference_remainder=remainder,ad_difference=ad,
                native_gap=s32-a32,identity_residual=(s32-a32)-(forward+remainder+ad),
                numerator_native_gap=2*h*(s32-a32),numerator_forward_difference=2*h*forward,
                numerator_reference_remainder=2*h*remainder,numerator_ad_difference=2*h*ad)
