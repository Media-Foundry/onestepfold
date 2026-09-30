from pathlib import Path
import runpy
import numpy as np
import pytest


def test_alignment_does_not_hide_raw_replay_error():
    fn=runpy.run_path(str(Path(__file__).parents[1]/'scripts/probe_folding_backend_replay.py'))['replay_difference']
    y=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
    rotation=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
    r=fn(y@rotation+10,y,np.ones(4,dtype=bool))
    assert r['max_abs']>9 and r['atom_rms']>9 and r['ca_aligned_rmsd']<1e-12 and not r['exact']
    assert fn(y,y,np.ones(4,dtype=bool))['exact']
    with pytest.raises(ValueError):fn(y+np.nan,y,np.ones(4,dtype=bool))
