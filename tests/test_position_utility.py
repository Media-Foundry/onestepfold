import numpy as np
import pytest
import torch
from fastglycan.position_utility import position_mutation_proposals
from fastglycan.models.soft_esm import AMINO_ACIDS


def test_position_selection_enumerates_all_replacements_not_global_top_scores():
    seq='ACY';g=torch.zeros(3,20);g[1,AMINO_ACIDS.index('K')]=-10
    result=position_mutation_proposals(seq,g,seed=12)
    assert result['positions']['gradient']==1
    selected=result['arms']['gradient']
    assert len(selected)==19 and {r['to_aa'] for r in selected}==set(AMINO_ACIDS)-{'C'}
    assert all(sum(a!=b for a,b in zip(seq,r['sequence']))==1 for r in selected)
    assert next(r for r in selected if r['to_aa']=='A')['sequence']=='AAY'
    # Position scores are invariant under adding a constant to each probability-gradient row.
    other=position_mutation_proposals(seq,g+torch.tensor([1.,5.,-7.])[:,None],seed=12)
    assert result==other


def test_random_overlap_is_retained_and_computation_deduplicated():
    result=position_mutation_proposals('A',torch.zeros(1,20),seed=3)
    assert result['positions']==dict(gradient=0,random=0)
    assert result['arms']['gradient']==result['arms']['random']
    assert len(result['sequences'])==20


def test_probability_gradient_validation_and_tie_rule():
    assert position_mutation_proposals('AC',torch.zeros(2,20),seed=4)['positions']['gradient']==0
    with pytest.raises(ValueError):position_mutation_proposals('AC',torch.zeros(2,19),seed=4)
    with pytest.raises(ValueError):position_mutation_proposals('AC',np.full((2,20),np.nan),seed=4)


def test_pullback_detects_wrong_variable_gradient_without_dividing_probabilities():
    from fastglycan.position_utility import audit_probability_pullback
    q=torch.tensor([[0.,-9.,-9.]]).requires_grad_(True);p=q.softmax(-1)
    gp=torch.tensor([[1234.,-23.,.4]]);gq,=torch.autograd.grad((p*gp).sum(),q)
    report=audit_probability_pullback(q,p,gp,gq)
    assert report['local_softmax_vjp_exact']
    bad=audit_probability_pullback(q,p,gp,gq+0.01)
    assert not bad['local_softmax_vjp_exact']


def test_full_checked_stereo_detects_thr_flip_when_ca_check_still_passes():
    from types import SimpleNamespace
    from fastglycan.position_utility import mutation_chemistry
    class Atoms(SimpleNamespace):
        def __len__(self):return len(self.atom_name)
    names=['N','CA','C','O','CB','OG1','CG2','N','CA','C','O','CB']
    bonds=np.array([[0,1],[1,2],[2,3],[1,4],[4,5],[4,6],[2,7],[7,8],[8,9],[9,10],[8,11]])
    atoms=Atoms(atom_name=np.array(names),res_id=np.array([1]*7+[2]*5),chain_id=np.array(['A']*12),
                element=np.array([n[0] for n in names]),res_name=np.array(['THR']*7+['ALA']*5),
                bonds=SimpleNamespace(as_array=lambda:bonds))
    ref=np.array([[-1,.7,0],[0,0,0],[1,.7,0],[1.7,1.7,0],[0,0,1],[1,0,1],[0,1,1],
                  [2,.7,0],[3,0,0],[4,.7,0],[4.7,1.7,0],[3,0,1]],dtype=float)
    calibration=dict(not_acceptance_thresholds=True,calibration_proteins=0,
                     windows={kind:dict(supported=False,edges=0,windows={}) for kind in ['Pro','other']})
    before=mutation_chemistry(atoms,ref,'TA',ref,calibration)
    altered=ref.copy();altered[5,0]=-1
    after=mutation_chemistry(atoms,ref,'TA',altered,calibration)
    assert before['strict_checked_chirality'] and before['side_wrong']==0
    assert after['ca_wrong']==0 and after['legacy_geometry']['chirality_fraction']==1
    assert after['side_wrong']==1 and not after['strict_checked_chirality']
    assert 'all_atom_lddt' not in after  # No experimental truth invented for the mutant.
