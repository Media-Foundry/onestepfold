import numpy as np
import torch
from fastglycan.functional_response_rank import (reconstruct_local_responses, local_conditioning_intervention,
    pack_conditioning, ranking_fidelity, prepare_fidelity_pairs, fidelity_lddt, response_structure_metrics)
from fastglycan.scaling_metrics import lddt_observed


def test_centered_reconstruction_and_wt():
    rng=np.random.default_rng(7);l=5;p=2
    endpoints=dict(s_site=rng.normal(size=(20,7)).astype('float32'),z_row=rng.normal(size=(20,l,3)).astype('float32'),z_col=rng.normal(size=(20,l,3)).astype('float32'))
    endpoints['z_col'][:,p]=endpoints['z_row'][:,p]
    out, info=reconstruct_local_responses(endpoints,4,[0,3,5,18])
    ids=np.delete(np.arange(20),4)
    flat=np.concatenate([endpoints[k].reshape(20,-1).astype(float) for k in ['s_site','z_row','z_col']],1)
    mean=flat[ids].mean(0);center=flat[ids]-mean
    _,_,vt=np.linalg.svd(center,full_matrices=False)
    for k in out:
        actual=np.concatenate([out[k][key].reshape(20,-1) for key in ['s_site','z_row','z_col']],1)
        np.testing.assert_allclose(actual[ids],mean+center@vt[:k].T@vt[:k],atol=2e-7,rtol=1e-6)
        for key in endpoints:assert np.array_equal(out[k][key][4],endpoints[key][4])
    for key in endpoints:np.testing.assert_allclose(out[18][key],endpoints[key],atol=1e-6)


def test_only_declared_slices_change_and_sham():
    torch.manual_seed(2);c=(torch.randn(5,7),torch.randn(5,9),torch.randn(5,5,3));p=2
    slices=dict(s_site=c[1][p].numpy(),z_row=c[2][p].numpy(),z_col=c[2][:,p].numpy())
    sham=pack_conditioning(local_conditioning_intervention(c,slices,p))
    assert all(torch.equal(a,b) for a,b in zip(c,sham))
    changed={k:v+1 for k,v in slices.items()};out=local_conditioning_intervention(c,changed,p)
    assert torch.equal(out[0],c[0])
    mask=torch.ones(5,5,dtype=torch.bool);mask[p]=False;mask[:,p]=False
    assert torch.equal(out[2][mask],c[2][mask])
    assert torch.equal(out[1][torch.arange(5)!=p],c[1][torch.arange(5)!=p])


def test_ranking_and_fidelity_reference():
    a=np.arange(20,dtype=float);same=ranking_fidelity(a,a);rev=ranking_fidelity(a,-a)
    assert same['top1_regret']==0 and same['top5_recall']==1
    assert rev['spearman'] < -.999 and rev['top1_regret']==19
    assert ranking_fidelity(a*0,a*0)['spearman'] is None
    rng=np.random.default_rng(31);y=rng.normal(size=(50,3))*4;x=y+rng.normal(size=y.shape)*.2;res=np.arange(50)//5
    assert abs(fidelity_lddt(x,prepare_fidelity_pairs(y,res))-lddt_observed(x,y,res)['score'])<1e-12
    ca=np.arange(0,50,5);cache=(prepare_fidelity_pairs(y,res),prepare_fidelity_pairs(y[ca],res[ca]))
    m=response_structure_metrics(y+8,y,ca,np.ones(10,dtype=bool),cache)
    assert m['ca_aligned_rmsd']<1e-12 and m['all_atom_lddt']==1
