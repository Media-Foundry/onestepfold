from fastglycan.mutation_utility import utility_decision


def test_absolute_failure_is_not_hidden_by_utility():
    bad=dict(atom_count=100,bond_rmse=.3,peptide_mae=.2,chirality_fraction=1.,
             severe_pairs=0,severe_pairs_per_atom=0.,max_penetration=2.1)
    d=utility_decision(-.2,-.1,bad,bad)
    assert d['task_and_nonregression'] and not d['full']['accepted']
    worse=dict(bad,max_penetration=2.2)
    assert not utility_decision(-.2,-.1,worse,bad)['task_and_nonregression']
    assert not utility_decision(-.1,-.1,bad,bad)['task_and_nonregression']
