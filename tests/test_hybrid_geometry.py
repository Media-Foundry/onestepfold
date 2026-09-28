from types import SimpleNamespace
import numpy as np
import torch
from fastglycan.hybrid_geometry import GeometryTopology,hard_accept
from fastglycan.hybrid_proposals import mutation_proposals,identity_noise


def atoms_fixture():
    class Atoms(SimpleNamespace):
        def __len__(self):return len(self.atom_name)
    return Atoms(atom_name=np.array(['CA','N','C','CB','CA']),res_id=np.array([1,1,1,1,2]),
        chain_id=np.array(['A']*5),element=np.array(['C','N','C','C','C']),
        bonds=SimpleNamespace(as_array=lambda:np.array([[0,1,1],[0,2,1],[0,3,1]])))


def test_geometry_loss_derivative_and_graph_exclusions():
    atoms=atoms_fixture();ref=np.array([[0,0,0],[1.4,0,0],[0,1.5,0],[0,0,1.5],[5,5,5]],dtype=float)
    topology=GeometryTopology(atoms,ref)
    assert set(map(tuple,topology.pairs.tolist()))=={(0,4),(1,4),(2,4),(3,4)}
    x=torch.tensor(ref,dtype=torch.float64,requires_grad=True)
    def loss(x):return sum(topology.terms(x)[0].values())
    assert torch.autograd.gradcheck(loss,(x,),eps=1e-6,atol=1e-5)
    mirrored=x.detach().clone();mirrored[:,2]*=-1
    assert topology.terms(mirrored)[1]['chirality_fraction']==0


def test_bad_geometry_cannot_be_bought_by_task_gain():
    g=dict(atom_count=100,bond_rmse=.1,peptide_mae=.05,chirality_fraction=1.,severe_pairs=0,
           severe_pairs_per_atom=0.,max_penetration=.5)
    assert hard_accept(-.2,-.1,g,g)['accepted']
    bad=g|dict(severe_pairs=100,severe_pairs_per_atom=1.,max_penetration=3.)
    assert not hard_accept(-100.,-.1,bad,g)['accepted']


def test_equal_budget_single_substitution_and_identity_noise():
    proposals=mutation_proposals('AC',torch.arange(40).reshape(2,20).float(),budget=8)
    for arm in proposals.values():
        assert len(arm)==len({v['sequence'] for v in arm})==8
        assert all(sum(a!=b for a,b in zip('AC',v['sequence']))==1 for v in arm)
    a=atoms_fixture();noise=identity_noise(a,211)
    b=atoms_fixture();order=[4,0,1,2,3]
    for name in ('chain_id','res_id','atom_name'):setattr(b,name,getattr(b,name)[order])
    torch.testing.assert_close(identity_noise(b,211),noise[:,order],rtol=0,atol=0)
