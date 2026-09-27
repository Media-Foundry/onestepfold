import torch
import pytest
from fastglycan.models import soft_sequence_chart as charts
from fastglycan.models.soft_esm import sequence_probabilities


def test_chemical_feature_path_and_topology_guard(monkeypatch):
    c=charts.SequenceChart.__new__(charts.SequenceChart)
    c.sequence='AC';c.native={};c.token_idx=torch.tensor([0,0,1])
    c.restype_bank=torch.cat([torch.eye(20),torch.zeros(20,12)],-1).double()
    c.bank={'ref_pos':torch.arange(3*20*3,dtype=torch.float64).reshape(3,20,3)}
    c.esm=c.alphabet=None
    monkeypatch.setattr(charts,'prepare_atom_pairs',lambda f:f)
    monkeypatch.setattr(charts,'soft_esm2',lambda m,a,p:p)
    q=(sequence_probabilities('AC',dtype=torch.float64)*4).requires_grad_()
    features=c.features(q.softmax(-1))
    g,=torch.autograd.grad(features['ref_pos'].sum(),q)
    assert g.isfinite().all() and (g.abs()>0).all()
    with pytest.raises(ValueError,match='argmax changed'):
        c.features(sequence_probabilities('AD',dtype=torch.float64))
