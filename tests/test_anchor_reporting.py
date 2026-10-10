"""The report must preserve old-noise decisions when teacher order changes."""
import pytest
from fastglycan.anchor_reporting import selection_detail_rows


def test_selection_keeps_old_choice_and_new_teacher_cost_distinct():
    def row(arm,tasks,selected,regret):
        return dict(site_key='site',arm=arm,tasks=tasks,old_selected=selected,
            old_select_new_regret=regret,role='held_protein',parent=0,pdb='toy')
    exact=row('exact',[[0.,2.,5.],[8.,1.,3.]],'A',7.)
    anchor=row('correct',[[4.,0.,2.],[0.,4.,3.]],'D',0.)
    control=row('correct',[[3.,2.,0.],[0.,1.,2.]],'L',2.)
    score=dict(step=128,sites=[exact,anchor],outputs=[
        dict(site_key='site',arm='exact',noise=noise,aa=aa)
        for noise in (230201,230211) for aa in ('A','D','L')])
    rows=selection_detail_rows(score,dict(sites=[control]),272001)
    mapped={r['method']:r for r in rows}
    assert mapped['anchor']['selected']=='D'
    assert mapped['anchor']['exact_old_regret']==2.
    assert mapped['anchor']['exact_new_regret']==0.
    assert mapped['anchor']['predicted_old_margin']==2.
    assert mapped['anchor']['exact_old_choice']=='A' and mapped['anchor']['exact_new_choice']=='D'
    assert mapped['control']['selected']=='L' and mapped['control']['exact_new_regret']==2.
    assert mapped['exact']['exact_new_regret']==7.
    anchor['old_selected']='A'
    with pytest.raises(AssertionError):selection_detail_rows(score,dict(sites=[control]),272001)
