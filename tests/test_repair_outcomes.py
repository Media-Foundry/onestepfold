import numpy as np
from fastglycan.repair_outcomes import chirality_transitions


def test_chirality_accounting_separates_new_corrected_and_persistent():
    tetra = np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
    raw = np.concatenate([tetra, tetra+[3,0,0], tetra+[6,0,0]])
    raw[[7,11],2] *= -1
    repaired = raw.copy()
    repaired[[3,7],2] *= -1
    r = chirality_transitions(raw, repaired, np.arange(12).reshape(3,4),
                              np.ones(3), np.repeat([1,2,3],4), ['A']*12, 'ALA')
    assert r['raw_wrong'] == r['repaired_wrong'] == 2
    assert [x['kind'] for x in r['rows']] == ['new_flip','corrected','persistent']
    assert [x['residue'] for x in r['rows']] == [1,2,3]
