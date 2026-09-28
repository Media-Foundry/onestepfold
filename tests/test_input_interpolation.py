from types import SimpleNamespace
import numpy as np
import torch
from fastglycan.input_interpolation import probability_interpolation,source_intervention,aligned_rmsd,audit_reference_caches
from fastglycan.models.soft_sequence_chart import REFERENCE_FEATURES


def test_explicit_probability_path_matches_previous_initialization():
    hard=torch.eye(20,dtype=torch.float64)[:3];alpha=19/(np.exp(4)+19)
    torch.testing.assert_close(probability_interpolation(hard,alpha),(4*hard).softmax(-1))
    assert torch.equal(probability_interpolation(hard,0),hard)
    torch.testing.assert_close(probability_interpolation(hard,.1).sum(-1),torch.ones(3,dtype=torch.float64))


def test_source_interventions_preserve_unselected_fields_and_drop_pair_cache():
    native={k:torch.tensor([1.]) for k in REFERENCE_FEATURES}
    native.update(restype=torch.tensor([1.]),profile=torch.tensor([2.]),deletion_mean=torch.tensor([3.]),d_lm='stale',v_lm='stale',pad_info='stale')
    soft={k:torch.tensor([9.]) for k in REFERENCE_FEATURES}
    for sources in ('E','R','C','ERC'):
        f=source_intervention(native,soft,torch.tensor([8.]),torch.tensor([4.]),torch.tensor([7.]),sources)
        assert f['esm_token_embedding'].item()==(7 if 'E' in sources else 4)
        assert f['ref_pos'].item()==(9 if 'C' in sources else 1)
        assert f['profile'].item()==(8 if 'R' in sources else 2)
        assert f['deletion_mean'].item()==3 and 'd_lm' not in f
    assert native['d_lm']=='stale'


def test_alignment_removes_rigid_motion():
    x=np.random.default_rng(5).normal(size=(20,3));r=np.array([[0.,-1,0],[1,0,0],[0,0,1]])
    assert aligned_rmsd(x,x@r+3)<1e-12


def test_cache_audit_rejects_stale_input_and_restores_methods():
    import pytest
    class Encoder:
        def prepare_cache(self,ref_pos,ref_charge,ref_mask,ref_element,ref_atom_name_chars,d_lm,v_lm):return 'ok'
    a,b=Encoder(),Encoder();model=SimpleNamespace(input_embedder=SimpleNamespace(atom_attention_encoder=a),diffusion_module=SimpleNamespace(atom_attention_encoder=b))
    fields={name:torch.tensor([1.]) for name in (*REFERENCE_FEATURES,'d_lm','v_lm')}
    with audit_reference_caches(model,fields) as records:
        a.prepare_cache(**fields);b.prepare_cache(**fields)
    assert len(records)==2
    with pytest.raises(RuntimeError,match='stale reference'):
        with audit_reference_caches(model,fields):a.prepare_cache(**(fields|{'ref_pos':torch.tensor([0.])}))
    assert a.prepare_cache(**fields)=='ok'
