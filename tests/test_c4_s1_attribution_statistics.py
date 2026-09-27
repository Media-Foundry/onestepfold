"""Check paired thresholds and target/seed grouping used in the reports."""
import importlib.util
from pathlib import Path
import sys
import numpy as np

scripts=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(scripts))
spec=importlib.util.spec_from_file_location('score_c4_attribution',scripts/'score_c4_s1_attribution.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_equal_settings_have_zero_difference_and_no_failures():
    s=module.summarize(np.zeros((5,4)))
    assert s['mean']==0 and s['mean_ci95']==[0,0]
    assert s['crossed_mean_ci95_sensitivity']==[0,0]
    assert s['persistence']['-0.05']['k_counts']=={'0':5,'1':0,'2':0,'3':0,'4':0}

def test_persistence_is_per_target_and_strict_threshold():
    d=np.array([[-.06]*4,[-.06,-.06,0,0],[-.05]*4,[.2]*4])
    s=module.summarize(d)
    assert s['n_targets']==4 and s['n_seeds']==4
    assert s['persistence']['-0.05']['k_counts']=={'0':2,'1':0,'2':1,'3':0,'4':1}
    assert s['persistence']['-0.05']['fraction']==6/16
    assert s['persistence']['-0.05']['persistent_3or4']==1
    assert s['persistence']['-0.1']['fraction']==0
    assert np.isclose(s['mean'],d.mean())
