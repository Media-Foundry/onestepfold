import numpy as np
from fastglycan.collision_audit import graph_neighbors,graph_distance,verify_exclusions


def test_exclusion_boundaries_and_disconnected_atoms():
    bonds=np.array([[0,1],[1,2],[2,3],[3,4]])
    neighbors=graph_neighbors(6,bonds)
    assert graph_distance(neighbors,0,3)==3
    assert graph_distance(neighbors,0,4)==4
    assert graph_distance(neighbors,0,5) is None
    pairs=np.array([[0,4],[0,5],[1,5],[2,5],[3,5],[4,5]])
    assert verify_exclusions(6,bonds,pairs)['exact']
    assert verify_exclusions(6,bonds,np.vstack([pairs,[0,3]]))['unexpected_included']==1


def test_collision_identity_distance_and_graph_separation():
    from types import SimpleNamespace
    import torch
    from fastglycan.collision_audit import collision_records
    top=SimpleNamespace(pairs=torch.tensor([[0,1],[0,2],[1,2]]),
                        radii=torch.tensor([1.7,1.7,1.55]),bonds=torch.empty((0,2),dtype=torch.long))
    rows=collision_records([[20.,0,0],[0,0,0],[.4,0,0]],top,
                           np.array(['CA','CE','N']),np.array([38,171,191]),np.array(['A']*3),'A'*194)
    assert len(rows)==1 and rows[0]['is_maximum'] and rows[0]['severe']
    assert rows[0]['a']['residue']==171 and rows[0]['b']['residue']==191
    assert rows[0]['graph_distance'] is None
    assert abs(rows[0]['distance_to_res38_ca_min']-19.6)<1e-10
