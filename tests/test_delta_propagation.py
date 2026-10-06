import numpy as np
from fastglycan.delta_propagation import delta_statistics


def test_additive_initialization_rank_and_dense_support():
    rng=np.random.default_rng(3)
    u=rng.normal(size=(40,8)).astype(np.float32)
    v=rng.normal(size=(40,8)).astype(np.float32)
    z=u[:,None,:]+v[None,:,:]
    stats=delta_statistics(np.zeros_like(z),z,4)
    assert stats['changed_pairs_outside_mutation_row_column']==39**2
    assert all(r['energy_r2']>1-1e-12 for r in stats['spectra'])
    assert all(r['r99']<=2 for r in stats['spectra'])


def test_sparse_support_zero_and_signed_zero():
    z=np.zeros((20,20,8),np.float32)
    assert all(r['r95']==0 for r in delta_statistics(z,z,2)['spectra'])
    y=z.copy();y[2,:,:]=1;y[:,2,:]=1
    stats=delta_statistics(z,y,2)
    assert stats['changed_pairs_outside_mutation_row_column']==0
    assert stats['unchanged_pairs']==19**2
    y=z.copy();y[0,0,0]=-0.0
    stats=delta_statistics(z,y,2,spectral=False)
    assert stats['nonzero_fraction']==0 and stats['bitwise_equal_fraction']<1
