import torch
from fastglycan.interface_decomposition import (decompose_response, analytic_embedding_tangent,
    dot64, detached_interface, INTERFACE_NAMES)


def test_complete_cut_accounts_for_direct_chemistry_and_upstream_path():
    q = torch.tensor(.4, dtype=torch.double, requires_grad=True)
    b = (q.square(), q.sin())  # conditioning and chemistry also depend on q
    leaves = tuple(x.detach().requires_grad_(True) for x in b)
    x = b[0].square() + 3*b[1]
    lam = torch.autograd.grad(leaves[0].square()+3*leaves[1], leaves)
    direct, = torch.autograd.grad(x, q, retain_graph=True)
    chain, = torch.autograd.grad(b, q, grad_outputs=lam)
    torch.testing.assert_close(direct, chain)
    h = .001
    bp = ((q+h).square(), (q+h).sin()); bm = ((q-h).square(), (q-h).sin())
    m = sum(l*(p-n)/(2*h) for l,p,n in zip(lam,bp,bm))
    d = (bp[0].square()+3*bp[1]-bm[0].square()-3*bm[1])/(2*h)
    r = decompose_response(float(direct),float(m.detach()),float(d.detach()))
    assert abs(r['identity_residual']) < 1e-15
    assert abs(float((chain - lam[0]*2*q).detach())) > 1  # omitting chemistry is detectable


def test_embedding_tangent_has_independent_forward_mode_and_fd_reference():
    torch.manual_seed(2)
    q=torch.randn(4,20,dtype=torch.double); v=torch.randn_like(q)
    w=torch.randn(20,13,dtype=torch.double); probe=torch.randn(4,13,dtype=torch.double)
    tangent=analytic_embedding_tangent(q,v,w)
    _,jvp=torch.func.jvp(lambda z:z.softmax(-1)@w,(q,),(v,))
    leaf=q.clone().requires_grad_(True)
    g,=torch.autograd.grad(dot64(leaf.softmax(-1)@w,probe),leaf)
    torch.testing.assert_close(jvp,tangent)
    torch.testing.assert_close(dot64(jvp,probe),dot64(g,v))
    fd=((q+1e-5*v).softmax(-1)@w-(q-1e-5*v).softmax(-1)@w)/2e-5
    torch.testing.assert_close(fd,tangent,atol=1e-9,rtol=1e-7)


def test_detached_cut_preserves_packed_storage_without_upstream_grad():
    flat=torch.randn(len(INTERFACE_NAMES)*3,requires_grad=True)
    b=dict(zip(INTERFACE_NAMES,flat.split(3)))
    leaves=detached_interface(b)
    for name in INTERFACE_NAMES:
        assert leaves[name].data_ptr()==b[name].data_ptr()
        assert leaves[name].is_leaf and leaves[name].requires_grad
