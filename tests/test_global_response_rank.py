import numpy as np
import torch
import pytest
from fastglycan.global_response_rank import GlobalResponseBasis,GLOBAL_VARIANTS,GLOBAL_RANKS


def test_global_weighted_svd_and_controls():
    torch.manual_seed(881);wt_s=torch.randn(4,3);wt_z=torch.randn(4,4,2)*20
    s=wt_s+torch.randn(19,4,3);z=wt_z+torch.randn(19,4,4,2)*30
    before=(s.clone(),z.clone());b=GlobalResponseBasis(wt_s,wt_z,s,z)
    for variant in GLOBAL_VARIANTS:
        for k in [0,3,5,18]:
            actual=[torch.stack([b.reconstruct(i,variant,k)[j] for i in range(19)]).numpy().reshape(19,-1) for j in [0,1]]
            arrays=[s.double().reshape(19,-1).numpy(),z.double().reshape(19,-1).numpy()]
            if variant in ['raw','balanced']:
                scale=[1.,1.] if variant=='raw' else [np.sqrt(b.energies[key]) for key in ['s','z']]
                joined=np.concatenate([(a-a.mean(0))/sc for a,sc in zip(arrays,scale)],1);u,sig,v=np.linalg.svd(joined,full_matrices=False);recon=(u[:,:k]*sig[:k])@v[:k]
                pieces=np.split(recon,[arrays[0].shape[1]],1)
                expected=[p*sc+a.mean(0) for p,sc,a in zip(pieces,scale,arrays)]
            else:
                expected=[]
                for j,a in enumerate(arrays):
                    if (variant=='s_only' and j==1) or (variant=='z_only' and j==0):expected.append(a);continue
                    u,sig,v=np.linalg.svd(a-a.mean(0),full_matrices=False);expected.append(a.mean(0)+(u[:,:k]*sig[:k])@v[:k])
            for x,y in zip(actual,expected):np.testing.assert_allclose(x,y,atol=1e-5,rtol=1e-6)
    assert torch.equal(s,before[0]) and torch.equal(z,before[1])
    for variant in ['balanced','separate_both']:
        assert all(torch.equal(a,bv) for a,bv in zip(b.reconstruct(0,'raw',0),b.reconstruct(0,variant,0)))


def test_zero_block_and_full_rank():
    torch.manual_seed(21);wt=torch.randn(3,2);s=wt.repeat(19,1,1);z=torch.randn(19,3,3,2);basis=GlobalResponseBasis(wt,torch.zeros(3,3,2),s,z)
    assert basis.energies['s']==0 and basis.spectra['s']['cumulative_energy'] is None
    for variant in GLOBAL_VARIANTS:
        out=basis.reconstruct(3,variant,18);torch.testing.assert_close(out[0],s[3]);torch.testing.assert_close(out[1],z[3])
    with pytest.raises(ValueError):basis.reconstruct(0,'raw',19)
