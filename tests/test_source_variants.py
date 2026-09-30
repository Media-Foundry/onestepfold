import pytest
from fastglycan.source_variants import canonical_hsp_index, select_isolated_variants


def test_blast_identifier_case_preserves_exact_namespace_and_index():
    assert canonical_hsp_index('R17781','r',21694)==canonical_hsp_index('r17781','r',21694)==17781
    assert canonical_hsp_index('p9','p',113)==9
    for identifier,prefix,size in [('r9','p',113),('r21694','r',21694),('r-1','r',21694),
        ('r017781','r',21694),('lcl|r17781','r',21694),('rNaN','r',21694)]:
        with pytest.raises(ValueError):canonical_hsp_index(identifier,prefix,size)


def test_source_reservation_respects_order_and_all_conflict_types():
    rows=[dict(group_id=g,pdb_id=p,accessions=[a]) for g,p,a in
        [('a','1AAA','A'),('b','1aaa','B'),('c','2bbb','A'),('d','3ccc','D'),('e','4ddd','E')]]
    selected,rejected=select_isolated_variants(rows,{('d','a')})
    assert [r['group_id'] for r in selected]==['a','e']
    assert [r['group_id'] for r in rejected]==['b','c','d']
    assert all(r['conflicts']==['a'] for r in rejected)
    changed,_=select_isolated_variants([rows[3],rows[0]],{('a','d')})
    assert [r['group_id'] for r in changed]==['d']
    with pytest.raises(ValueError,match='one qualifying'):select_isolated_variants(rows+[rows[0]],set())
