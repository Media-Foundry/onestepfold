import numpy as np
import pytest
from fastglycan.context_coverage import aa_table_projection, repeated_source_inventory, select_repeated_contexts


def case(wt, y, parent):
    return dict(wt=wt,target_delta=[y,y,y,y],parent_index=parent,position=0)


def test_aa_table_floor_and_singletons():
    r=aa_table_projection([case(0,[0,1,2],1),case(0,[0,-1,-2],2),case(1,[3,0,4],3)],'ACD')
    assert r['source_counts']=={'A':2,'C':1}
    assert r['singleton_contexts']==1
    assert r['irreducible_global_normalized_mse']==pytest.approx(10/35)
    assert r['singleton_energy_fraction']==pytest.approx(25/35)
    assert r['sites'][2]['table_error_energy']==0
    assert r['pythagorean_error']<1e-12


def test_zero_label_energy_is_not_perfect_fit_evidence():
    r=aa_table_projection([case(0,[0,0,0],1)],'ACD')
    assert r['irreducible_global_normalized_mse'] is None


def test_inventory_keeps_held_train_archive_out():
    rows=[dict(source_aa='A',eligible_train=True,common_holdout=h,parent_index=i,component=str(i)) for i,h in enumerate([False,True])]
    r=repeated_source_inventory(rows,'A')[0]
    assert r['available_train_components']==1 and r['held_components']==1


def test_nested_selection_no_label_input_and_group_isolation():
    rows=[]
    for length in [90,125,160]:
        for j in range(20):
            rows.append(dict(sequence='A'*length,group_id=f'{length}-{j}',component=f'{length}-{j}',eligible_positions={a:[i,i+4] for i,a in enumerate('ADLT')}))
    result=select_repeated_contexts(rows)
    assert [len(result['nested_train_tiers'][str(n)]) for n in [8,16,32]]==[8,16,32]
    assert sum(r['role']=='confirmation_candidate' for r in result['rows'])==8
    assert len({r['component'] for r in result['rows']})==40
    assert result==select_repeated_contexts(list(reversed(rows)))
    with pytest.raises(ValueError):select_repeated_contexts(rows[:5])
