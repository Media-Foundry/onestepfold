import torch
from fastglycan.composite_derivatives import dictionary_jvp,consistency


def test_true_tangent_composition_keeps_carried_path_and_matches_vjp():
    q=torch.tensor([.2,.6],dtype=torch.double)
    v=torch.tensor([1.,-.3],dtype=torch.double)
    def first(x):return dict(s=x['q'].square(),b=x['q'].sin())
    def cycle(x):return dict(s=torch.tanh(x['s'])+x['b'],b=x['b'])
    point,tangent=dictionary_jvp(first,{'q':q},{'q':v})
    for _ in range(4):point,tangent=dictionary_jvp(cycle,point,tangent)
    leaf=q.detach().requires_grad_(True);reference=first({'q':leaf})
    for _ in range(4):reference=cycle(reference)
    g,=torch.autograd.grad(reference['s'].sum(),leaf)
    torch.testing.assert_close(tangent['s'].sum(),(g*v).sum())
    assert consistency(float(tangent['s'].sum()),float((g*v).sum()))['passed']
