import pytest
import torch
from fastglycan.esm_interface_diagnostics import early_interface,early_features,nested_decomposition,EARLY_NAMES


def test_tied_profile_and_rebuilt_chemistry_preserve_complete_gradient():
    q=torch.tensor(.4,dtype=torch.double,requires_grad=True)
    features={k:q.square() for k in EARLY_NAMES};features['profile']=features['restype']
    b=early_interface(features)
    def pairs(f):return f | {'d_lm':f['ref_pos']*3}
    def objective(f):return f['esm_token_embedding']+2*f['restype']+5*f['profile']+f['d_lm']
    rebuilt=early_features({},b,pairs)
    assert rebuilt['restype'] is rebuilt['profile']
    direct,=torch.autograd.grad(objective(rebuilt),q,retain_graph=True)
    leaves={k:x.detach().requires_grad_(True) for k,x in b.items()}
    grads=torch.autograd.grad(objective(early_features({},leaves,pairs)),tuple(leaves.values()),allow_unused=True)
    grads=tuple(torch.zeros_like(x) if g is None else g for x,g in zip(leaves.values(),grads))
    chain,=torch.autograd.grad(tuple(b.values()),q,grad_outputs=grads)
    torch.testing.assert_close(direct,chain)
    assert direct==torch.tensor(8.8,dtype=torch.double)
    features['profile']=features['restype'].clone()
    with pytest.raises(ValueError):early_interface(features)


def test_nested_identity_preserves_opposing_deviations():
    r=nested_decomposition(1.,-2.,4.,3.)
    assert r['before_esm_output']==-3 and r['input_embedder_and_pairformer']==6
    assert r['diffusion']==-1 and r['identity_residual']==0
