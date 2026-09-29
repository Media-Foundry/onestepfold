import numpy as np
from fastglycan.independent_geometry_summary import protein_quality,geometry_transitions,atom_lddt,penetration_distribution,QUALITY
from fastglycan.scaling_metrics import lddt_observed


def test_quality_uses_triplet_means_not_best_seed_or_pooled_rows():
    rows=[]
    for g,values in [('a',[.1,.1,1.]),('b',[.6,.6,.6])]:
        for s,v in zip((300007,300017,300023),values):rows.append(dict(group_id=g,seed=s,quality={m:{k:(.5 if m=='raw' else v) for k in QUALITY} for m in ['raw','mean','tail']}))
    proteins,summary=protein_quality(rows,['a','b'])
    assert np.isclose(proteins[0]['quality']['tail']['all_atom_lddt'],.4)
    assert np.isclose(summary['absolute']['tail']['all_atom_lddt']['mean'],.5)
    _,missing=protein_quality(rows[:-1],['a','b'])
    assert missing['paired']['tail']['all_atom_lddt']['missing']==1
    assert missing['paired']['tail']['all_atom_lddt']['bootstrap95'] is None


def test_unknown_geometry_is_not_an_observed_failure_or_success():
    rows=[dict(group_id='a',raw_joint_pass=True,tail_joint_pass=True),dict(group_id='a',raw_joint_pass=True,tail_joint_pass=False),dict(group_id='a',raw_joint_pass=False,tail_joint_pass=True),dict(group_id='b',raw_joint_pass=False)]
    stats=geometry_transitions(rows)['tail']
    assert stats['raw_pass_retained']==stats['raw_pass_regressed']==stats['raw_fail_repaired']==1
    assert stats['repaired_unknown']==stats['comparison_unknown']==1
    assert stats['all3_proteins_pass']==0 and stats['raw_fail_repair_rate']==.5


def test_local_lddt_reduces_to_frozen_metric_with_unobserved_neighbors():
    y=np.array([[0,0,0],[2,0,0],[3,1,0],[5,0,1],[100,0,0]],float);x=y.copy();x[2]+=.7;res=np.array([1,1,2,3,4])
    scores=atom_lddt(x,y,res)
    assert np.isnan(scores[-1])
    assert np.isclose(np.nanmean(scores),lddt_observed(x,y,res)['score'])


def test_all_pair_population_is_not_only_worst_collisions():
    x=np.array([[0,0,0],[.5,0,0],[10,0,0]],float);pairs=np.array([[0,1],[0,2],[1,2]])
    out=penetration_distribution(x,pairs,np.array([1.7]*3))
    assert out['permitted_pairs']==3 and out['positive_depth_pairs']==1 and out['zero_depth_pairs']==2
    assert out['severe_distance_below1']==1 and sum(out['positive_histogram_counts'])==1
