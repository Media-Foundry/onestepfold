import torch
from torch import nn
from fastglycan.models.soft_esm import soft_esm2, sequence_probabilities, hard_sequence, AMINO_ACIDS

class Alphabet:
    cls_idx=20
    eos_idx=21
    def get_idx(self, aa): return AMINO_ACIDS.index(aa)

class Layer(nn.Module):
    def forward(self, x, **kwargs): return x + .1*x.mean(0,keepdim=True).tanh(), None

class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed_tokens=nn.Embedding(22,8)
        self.layers=nn.ModuleList([Layer(),Layer()])
        self.emb_layer_norm_after=nn.LayerNorm(8)
        self.embed_scale=1
        self.token_dropout=True


def test_soft_esm_onehot_and_logits_gradient():
    torch.manual_seed(9)
    m=Model().double().eval().requires_grad_(False)
    p=sequence_probabilities('ACDF',dtype=torch.float64)
    out=soft_esm2(m,Alphabet(),p)
    x=m.embed_tokens(torch.tensor([20,0,1,2,4,21]))[:,None]*.88
    for layer in m.layers: x=layer(x)[0]
    expected=m.emb_layer_norm_after(x)[1:-1,0]
    torch.testing.assert_close(out,expected,rtol=0,atol=0)
    q=(p*2).requires_grad_()
    value=soft_esm2(m,Alphabet(),q.softmax(-1)).square().sum()
    g,=torch.autograd.grad(value,q)
    assert g.isfinite().all() and g.norm()>0
    assert hard_sequence(p)=='ACDF'


def test_checkpointed_esm_matches_uncheckpointed_input_gradient():
    torch.manual_seed(12)
    m=Model().double().eval().requires_grad_(False)
    gradients=[]
    for ckpt in (False, True):
        q=(sequence_probabilities('ACDF',dtype=torch.float64)*3).requires_grad_()
        out=soft_esm2(m,Alphabet(),q.softmax(-1),checkpoint_layers=ckpt)
        loss=out[...,0].square().sum()
        gradients.append(torch.autograd.grad(loss,q)[0])
    torch.testing.assert_close(*gradients,rtol=0,atol=0)
