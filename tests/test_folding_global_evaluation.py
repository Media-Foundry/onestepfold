import copy
import json
import runpy
from pathlib import Path
import numpy as np
import pytest
from fastglycan.folding_global_evaluation import make_global_distance_evaluation_lock,REFERENCE_MODELS
from fastglycan.evaluation_reuse import expected_evaluation_calls,evaluation_prediction_source
from fastglycan.structure_extent import structure_extent_diagnostics


def test_six_model_reuse_and_budget_are_explicit():
    rows=[dict(group_id=str(i),role='train' if i<423 else 'validation') for i in range(455)]
    prior=dict(models=REFERENCE_MODELS,rows=rows,cohorts=dict(original_train128=[str(i) for i in range(128)],added_train295=[str(i) for i in range(128,423)],observed_validation32=[str(i) for i in range(423,455)]),
               train_seeds=[1,2],validation_seeds=[3,4],assignments=[rows[i::8] for i in range(8)],cache='/cache')
    original=copy.deepcopy(prior)
    kwargs=dict(train='/train',control='/control',reference_evaluation='/old',checkpoint=dict(path='/new.pt',sha256='x'),training_lock_sha256='lock',selected_names=['weight'],hashes={},input_hashes={},protocol_sha256='p')
    lock=make_global_distance_evaluation_lock(prior,**kwargs)
    assert prior==original and lock['planned_outputs']==5460 and lock['planned_probe_nfe']==32
    assert expected_evaluation_calls(lock,rows)==dict(native=0,global_distance=910)
    assert sum(expected_evaluation_calls(lock,shard)['global_distance'] for shard in lock['assignments'])==910
    for model in REFERENCE_MODELS:assert evaluation_prediction_source(lock,rows[-1],model,3)==Path(f'/old/examples/454/{model}_seed3.npy')
    assert evaluation_prediction_source(lock,rows[-1],'global_distance',3) is None
    assert lock['contrasts'][:2]==[['global_distance','coordinate_zero'],['global_distance','expanded']]
    bad=copy.deepcopy(prior);bad['models']=bad['models'][:-1]
    with pytest.raises(ValueError):make_global_distance_evaluation_lock(bad,**kwargs)
    bad=copy.deepcopy(prior);bad['validation_seeds']=[3,3]
    with pytest.raises(ValueError):make_global_distance_evaluation_lock(bad,**kwargs)


def test_extent_uses_declared_primary_pair_and_preserves_old_default(tmp_path):
    api=runpy.run_path(str(Path(__file__).parents[1]/'scripts/analyze_folding_structure_extent.py'))
    run=api['summarize_structure_extent'];rng=np.random.default_rng(10);y=rng.normal(size=(32,3))*10
    models=['expanded','coordinate_zero','global_distance'];records=[]
    for i,m in enumerate(models):
        for seed in [1,2]:
            d=structure_extent_diagnostics(y*(1+.1*i),y,np.arange(1,33))
            records.append(dict(model=m,seed=seed,rmsd_replay_error=0,**d))
    results=[dict(group_id='a',pdb_id='test',complete=True,records=records)]
    class Pool:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def map(self,*args):return results
    run.__globals__['ProcessPoolExecutor']=Pool
    source=tmp_path/'source';source.mkdir()
    lock=dict(rows=[dict(group_id='a')],models=models,cohorts={'train':['a']},bootstrap=dict(seed=3,replicates=10),contrasts=[['global_distance','coordinate_zero'],['coordinate_zero','expanded']])
    (source/'lock.json').write_text(json.dumps(lock))
    for name,extra,candidate,reference in [('new',dict(diagnostic_candidate='global_distance',diagnostic_reference='coordinate_zero'),'global_distance','coordinate_zero'),('old',{},'coordinate_zero','expanded')]:
        root=tmp_path/name;root.mkdir();(root/'manifest.json').write_text(json.dumps(dict(evaluation_root=str(source),hashes={},**extra)))
        run(root,1);report=json.loads((root/'report.json').read_text());pair=report['paired'][0]
        assert report['diagnostic_candidate']==candidate and report['diagnostic_reference']==reference
        expected={m:next(r for r in records if r['model']==m)['ca_rmsd'] for m in models}
        assert pair['candidate']['ca_rmsd']==expected[candidate] and pair['reference']['ca_rmsd']==expected[reference]
