import numpy as np
import pytest
from fastglycan.geometry_repair import identity_indices, preservation


def test_identity_mapping_reorders_auxiliary_atoms_and_rejects_loss():
    old = [('A', 1, 'N'), ('A', 1, 'CA')]
    assert identity_indices(old, [old[1], ('A', 1, 'H'), old[0]]).tolist() == [2, 0]
    with pytest.raises(ValueError):
        identity_indices(old, [old[0]])
    with pytest.raises(ValueError):
        identity_indices(old, old + [old[0]])


def test_preservation_does_not_hide_translation_or_local_deformation():
    raw = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
    translated = preservation(raw, raw + [2., 0, 0], np.arange(4))
    assert translated['ca_aligned_rms'] < 1e-12
    assert translated['ca_rms'] == 2
    assert not translated['accepted']
    changed = raw.copy(); changed[1, 0] += .2
    assert preservation(raw, changed, np.arange(4))['ca_distance_rms'] > 0
    assert preservation(raw, raw, np.arange(4))['accepted']
