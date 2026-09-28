from types import SimpleNamespace
import numpy as np
from fastglycan.geometry_audit import independent_allowed_pairs,pair_attribution


class Atoms(SimpleNamespace):
    def __len__(self):return len(self.atom_name)


def test_path_exclusion_keeps_four_bond_pairs_and_disconnected_atoms():
    a=Atoms(atom_name=np.array(['C']*6),bonds=SimpleNamespace(
        as_array=lambda:np.array([[0,1,1],[1,2,1],[2,3,1],[3,4,1]])))
    pairs=set(map(tuple,independent_allowed_pairs(a)))
    assert pairs=={(0,4),(0,5),(1,5),(2,5),(3,5),(4,5)}


def test_unobserved_clash_is_retained_in_all_atom_audit_only():
    a=Atoms(atom_name=np.array(['CA']*3),element=np.array(['C']*3),
            res_id=np.array([1,20,40]),res_name=np.array(['ALA']*3),chain_id=np.array(['A']*3))
    x=np.array([[0,0,0],[.2,0,0],[5,0,0]])
    report=pair_attribution(a,x,np.array([[0,1],[0,2],[1,2]]),observed=[False,True,True],reference=x)
    assert report['all_atoms']['severe_pairs']==1
    assert report['observed_atoms']['severe_pairs']==0
    assert report['severe_touching_unobserved']==1
    assert report['top_pairs'][0]['both_observed'] is False
    assert 'experimental_distance' not in report['top_pairs'][0]


def test_missing_bond_endpoint_does_not_enter_experimental_error():
    import torch
    from fastglycan.geometry_audit import observed_bond_geometry
    topology=SimpleNamespace(bonds=torch.tensor([[0,1],[1,2]]),
       ideal=torch.tensor([1.,1.]),peptide=torch.tensor([False,True]),
       centres=torch.empty((0,4),dtype=torch.long),volumes=torch.empty(0))
    # First coordinate is a missing zero-fill, not an observed atom at the origin.
    x=np.array([[0.,0,0],[10.,0,0],[11.,0,0]])
    result=observed_bond_geometry(x,topology,[False,True,True])
    assert result['observed_bonds']==1 and result['bond_rmse']==0
    assert result['observed_peptides']==1 and result['peptide_mae']==0
    assert result['chirality_fraction'] is None
