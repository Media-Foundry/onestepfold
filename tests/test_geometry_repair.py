import numpy as np
import pytest
from fastglycan.geometry_repair import identity_indices, preservation, force_diagnostics


def test_force_diagnostics_distinguish_vector_and_component_thresholds():
    result = force_diagnostics([[12., 0., 0.], [0., 12., 0.]])
    assert result['force_rms_vector'] == 12.
    assert result['force_rms_component'] == pytest.approx(12/np.sqrt(3))
    assert not result['force_vector_rms_le_10']
    assert result['force_component_rms_le_10']
    assert 'force_tolerance_met' not in result
    with pytest.raises(ValueError):
        force_diagnostics([[np.nan, 0., 0.]])


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
