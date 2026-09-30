import copy
import pytest
from fastglycan.folding_evaluation import summarize_folding_cohorts


def test_folding_cohorts():
    lock=dict(rows=[dict(group_id=g,role=role,sequence='AAA') for g,role in [('old','train'),('new','train'),('v','validation')]],
        cohorts={'original':['old'],'added':['new'],'validation':['v']},models=['base','candidate'],
        train_seeds=[1,2],validation_seeds=[3,4],contrasts=[['candidate','base']],bootstrap=dict(seed=1,replicates=100))
    records=[]
    for row in lock['rows']:
        for i,s in enumerate(lock['train_seeds'] if row['role']=='train' else lock['validation_seeds']):
            for m in lock['models']:
                # Candidate helps only one noise. Neither best-of nor joint chemistry may hide the other.
                value=.5 if m=='base' else [.7,.1][i]
                records.append(dict(group_id=row['group_id'],seed=s,model=m,all_atom_lddt=value,ca_lddt=value,
                    geometry=dict(severe_pairs=int(m=='candidate' and i==1),strict_checked_chirality=True)))
    result=summarize_folding_cohorts(records,lock)
    for c in result['summary'].values():
        assert c['proteins']==1
        assert c['contrasts'][0]['quality']['all_atom_lddt']['mean']==pytest.approx(-.1)
        assert c['contrasts'][0]['quality']['all_atom_lddt']['below_minus_005']==1
        assert c['models']['candidate']['zero_and_strict_both_noises']==0
        assert c['contrasts'][0]['introduced_severe_on_zero_instances']==1
    with pytest.raises(ValueError,match='missing'):summarize_folding_cohorts(records[:-1],lock)
    with pytest.raises(ValueError,match='duplicate'):summarize_folding_cohorts(records+[records[0]],lock)
    bad=copy.deepcopy(lock);bad['cohorts']['added']=['old']
    with pytest.raises(ValueError,match='partition'):summarize_folding_cohorts(records,bad)
