from types import SimpleNamespace

import numpy as np
import torch

from fastglycan.diffusion_pilot_metrics import prepare_pilot_scoring, score_diffusion_pilot
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.connection_audit import TOLERANCES
from fastglycan.scaling_metrics import lddt_observed


def test_pilot_scoring_masks_and_full_inventory():
    rng=np.random.default_rng(30);reference=rng.normal(size=(15,3))
    names=np.tile(['N','CA','C','O','CB'],3);residues=np.repeat(np.arange(1,4),5)
    reference+=np.repeat(np.arange(3)*3,5)[:,None]
    bonds=np.array([(5*i+a,5*i+b,1) for i in range(3) for a,b in [(0,1),(1,2),(2,3),(1,4)]]+[(2,5,1),(7,10,1)])
    atom_type=type('Atoms',(SimpleNamespace,),{'__len__':lambda self:len(self.atom_name)})
    atoms=atom_type(atom_name=names,res_id=residues,chain_id=np.array(['A']*15),
        element=np.array([n[0] for n in names]),bonds=SimpleNamespace(as_array=lambda:bonds))
    # A missing GT sidechain still exists in the predicted chemical graph.
    mask=np.ones(15,dtype=bool);mask[14]=False
    mapping=dict(coordinates=reference.copy(),mask=mask,reference=reference,
        atom_names=names,residue_ids=residues,chain_ids=atoms.chain_id)
    x=reference.copy();x[14]=x[0]+np.array([.1,0,0])
    calibration=dict(not_acceptance_thresholds=True,calibration_proteins=32,windows={
        k:dict(supported=True,edges=100,windows={t:{q:dict(equal_protein=1.) for q in ['q95','q99']} for t in TOLERANCES})
        for k in ['Pro','other']})
    result=score_diffusion_pilot(x,prepare_pilot_scoring(mapping,bonds,'AAA'),calibration)
    topology=GeometryTopology(atoms,reference)
    _,dense=topology.terms(torch.tensor(x))
    geometry=result['geometry']
    for old,new in [('severe_pairs','severe_pairs'),('max_penetration','max_penetration'),
                    ('bond_rmse','legacy_reference_bond_rmse'),('peptide_mae','legacy_reference_peptide_mae')]:
        np.testing.assert_allclose(dense[old],geometry[new],rtol=1e-12,atol=1e-12)
    assert geometry['severe_pairs']>0
    assert result['all_atom_lddt']==lddt_observed(x[mask],reference[mask],residues[mask])['score']
    poisoned=dict(mapping,coordinates=reference.copy());poisoned['coordinates'][~mask]=np.nan
    repeated=score_diffusion_pilot(x,prepare_pilot_scoring(poisoned,bonds,'AAA'),calibration)
    assert result==repeated
