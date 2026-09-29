import torch
from fastglycan.anchored_tail import tail_penalty


def test_streamed_worst_pairs_equal_dense_value_and_gradient():
    torch.manual_seed(21)
    x=torch.randn(25,3,dtype=torch.float64,requires_grad=True)
    pairs=torch.triu_indices(len(x),len(x),offset=1).T
    radii=torch.full((len(x),),1.7,dtype=x.dtype)
    depth=radii[pairs[:,0]]+radii[pairs[:,1]]-(x[pairs[:,0]]-x[pairs[:,1]]).norm(dim=-1)
    dense=(torch.relu(depth.topk(16).values-1.9)/.1).square().mean()
    streamed=tail_penalty(x,pairs,radii,chunk_size=13)
    torch.testing.assert_close(streamed,dense)
    torch.testing.assert_close(torch.autograd.grad(streamed,x)[0],torch.autograd.grad(dense,x)[0])
    assert torch.autograd.gradcheck(lambda z:tail_penalty(z,pairs,radii,chunk_size=13),(x,))


def test_empty_pairs_and_satisfied_pairs_have_zero_penalty():
    x=torch.tensor([[0.,0.,0.],[10.,0.,0.]],dtype=torch.float64,requires_grad=True)
    radii=torch.ones(2,dtype=x.dtype)*1.7
    for pairs in [torch.empty((0,2),dtype=torch.long),torch.tensor([[0,1]])]:
        loss=tail_penalty(x,pairs,radii)
        assert loss==0
        assert torch.equal(torch.autograd.grad(loss,x)[0],torch.zeros_like(x))
