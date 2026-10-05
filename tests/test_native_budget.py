import pytest
from fastglycan.native_budget import budget_parents,budget_order


def test_all_three_budgets_balanced_no_result_selection():
    orders=[budget_order(i) for i in range(6)]
    assert len(set(orders))==6 and all(set(x)=={1,2,4} for x in orders)
    assert all(sum(x[position]==cycle for x in orders)==2 for position in range(3) for cycle in [1,2,4])
    rows=[dict(role='confirmation_candidate',pdb_id=str(i)) for i in range(8)]+[dict(role='train',pdb_id='2V66')]
    assert budget_parents(rows)==list(range(9))
    with pytest.raises(ValueError):budget_parents(rows[:-1])


def test_screen_task_matches_frozen_torch_huber_definition():
    import numpy as np
    import torch
    from fastglycan.native_budget import screen_native
    from fastglycan.backbone_sequence_task import backbone_target_loss
    ref=np.array([[4*r+d,0.,0.] for r in range(4) for d in [-1.,0.,1.]])
    x=ref.copy();x[10,0]+=2
    bonds=np.array([[i,i+1,1] for i in range(11)])
    inv=dict(atom_names=np.tile(['N','CA','C'],4),residue_ids=np.repeat(np.arange(1,5),3),reference=ref,bonds=bonds)
    labels=dict(excluded=np.array([],int),radii=np.repeat(1.7,12),centres=np.empty((0,4),int),volumes=np.array([]))
    pairs=torch.tensor([[0,3]]);dist=torch.tensor([12.],dtype=torch.float64);ca=[1,4,7,10]
    got=screen_native(x,inv,labels,pairs,dist)
    expected=float(backbone_target_loss(torch.tensor(x),ca,pairs,dist))
    assert got['task']==expected==1.5
    assert np.isfinite(got['geometry']['bond_rmse_reference'])
