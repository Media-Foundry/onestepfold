import torch
from fastglycan.sequence_gate_metrics import directional_finite_differences


def test_gate_checks_true_logit_derivative_and_rejects_detach():
    torch.manual_seed(8)
    q=torch.randn(3,20,dtype=torch.float64)
    weights=torch.arange(20,dtype=q.dtype)
    def f(x): return (x.softmax(-1)*weights).sum()
    _,good=directional_finite_differences(f,q,directions=2)
    assert good['passed']
    def broken(x): return f(x)+f(x.detach())
    _,bad=directional_finite_differences(broken,q,directions=2)
    assert not bad['passed']


def test_atom_geometry_detects_mirror_with_identical_bond_lengths():
    import numpy as np
    from types import SimpleNamespace
    from fastglycan.sequence_gate_metrics import atom_geometry
    positions=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
    atoms=SimpleNamespace(res_id=np.ones(4,dtype=int),atom_name=np.array(['CA','N','C','CB']),
                          bonds=SimpleNamespace(as_array=lambda:np.array([[0,1,1],[0,2,1],[0,3,1]])))
    correct=atom_geometry(positions,atoms,positions)
    mirrored=positions.copy();mirrored[:,2]*=-1
    wrong=atom_geometry(mirrored,atoms,positions)
    assert correct['bond_rmse']==wrong['bond_rmse']==0
    assert correct['chirality_fraction']==1 and wrong['chirality_fraction']==0
