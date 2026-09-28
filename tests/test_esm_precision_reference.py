import torch
from fastglycan.esm_precision_reference import Segment,precision_copy,FloatingDtypeAudit,precision_decomposition


def test_precision_decomposition_preserves_sign_and_numerator():
    r=precision_decomposition(4.,1.,2.,1.5,.1)
    assert r['forward_difference']==2 and r['reference_remainder']==.5 and r['ad_difference']==.5
    assert r['identity_residual']==0 and abs(r['numerator_native_gap']-.6)<1e-15


def test_reference_lifts_identical_norm_parameters_and_checks_intermediate_dtype():
    torch.manual_seed(1)
    native=Segment(norm=torch.nn.LayerNorm(4,eps=1e-5)).eval().requires_grad_(False)
    ref,replaced=precision_copy(native,torch.float64)
    assert not replaced and ref.norm.eps==native.norm.eps
    assert torch.equal(ref.norm.weight,native.norm.weight.double())
    x=torch.randn(2,4,dtype=torch.double)
    audit=FloatingDtypeAudit()
    with audit:y=ref(x)
    assert not audit.non_double and audit.counts['torch.float64']>0
    mu=torch.randn_like(x);v=torch.randn_like(x);q=x.requires_grad_(True)
    g,=torch.autograd.grad((ref(q)*mu).sum(),q)
    _,jvp=torch.func.jvp(ref,(x.detach(),),(v,))
    torch.testing.assert_close((jvp*mu).sum(),(g*v).sum())
    h=1e-5;fd=((ref(x+h*v)-ref(x-h*v))*mu).sum()/(2*h)
    torch.testing.assert_close(fd,(g*v).sum(),rtol=1e-6,atol=1e-8)


def test_dtype_audit_detects_hidden_float_cast():
    audit=FloatingDtypeAudit()
    with audit:torch.ones(2,dtype=torch.double).float().double()
    assert audit.non_double and audit.counts['torch.float32']>0


def test_reference_rope_uses_fixed_native_values_and_never_regenerates():
    class Cached(torch.nn.Module):
        def __init__(self):
            super().__init__();self.register_buffer('inv_freq',torch.tensor([.3]))
            self._seq_len_cached=3;self._cos_cached=torch.tensor([[[.12],[.23],[.34]]]);self._sin_cached=self._cos_cached*.7
        def _update_cos_sin_tables(self,x,seq_dimension=1):
            raise AssertionError('reference must not regenerate positional tables')
        def forward(self,x):
            c,s=self._update_cos_sin_tables(x)
            return x*c+s
    native=Cached();ref,_=precision_copy(native,torch.double)
    x=torch.ones(1,3,1,dtype=torch.double)
    assert torch.equal(ref(x),native._cos_cached.double()+native._sin_cached.double())
    assert native._cos_cached.dtype==torch.float32
    assert ref._cos_cached.dtype==torch.float64
