import hashlib
import pytest
from fastglycan.folding_esm_bridge import select_folding_bridge_train, load_folding_bridge_pair


def test_fit_membership_never_admits_validation_or_duplicate_roles():
    rows=[dict(group_id=hashlib.sha256(s.encode()).hexdigest(),sequence=s,role=role)
          for s,role in [('ACD','train'),('VVI','validation'),('GG','train')]]
    pairs=[dict(group_id=r['group_id'],length=len(r['sequence']),role=r['role']) for r in rows]
    selected=select_folding_bridge_train(pairs,rows,expected_train=2)
    assert [r['group_id'] for r in selected]==sorted(r['group_id'] for r in rows if r['role']=='train')
    with pytest.raises(ValueError,match='Validation'):
        load_folding_bridge_pair(pairs[1],'/nonexistent','unused')
    with pytest.raises(ValueError,match='Duplicate'):
        select_folding_bridge_train(pairs+[pairs[0]],rows,expected_train=2)
    with pytest.raises(ValueError,match='role'):
        select_folding_bridge_train([{**p,'role':'train'} for p in pairs],rows,expected_train=2)
    with pytest.raises(ValueError,match='denominator'):
        select_folding_bridge_train(pairs,rows,expected_train=3)
    with pytest.raises(ValueError,match='sequence'):
        select_folding_bridge_train([{**p,'length':99} for p in pairs],rows,expected_train=2)
