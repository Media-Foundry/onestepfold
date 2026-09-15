import pytest

from onestepfold.data.esmc_cache import (
    ESMCFeatureSpec,
    select_feature_layers,
    sequence_sha256,
    strip_special_tokens,
)


def test_cache_spec_requires_pinned_revisions():
    with pytest.raises(ValueError):
        ESMCFeatureSpec("biohub/ESMC-600M", "main", "abc", "final", 1152, 36)


def test_sequence_digest_and_bos_eos_alignment():
    import numpy as np

    assert len(sequence_sha256("ACDE")) == 64
    hidden = np.zeros((6, 4), dtype=np.float32)
    assert strip_special_tokens(hidden, 4).shape == (4, 4)
    with pytest.raises(ValueError):
        strip_special_tokens(hidden[:-1], 4)


def test_select_layers_supports_stacked_hidden_states():
    import numpy as np

    hidden = np.zeros((37, 2, 5, 8), dtype=np.float32)
    assert select_feature_layers(hidden, "final")["final"].shape == (2, 5, 8)
    assert sorted(select_feature_layers(hidden, "layers_12_24_36")) == [
        "layer_12",
        "layer_24",
        "layer_36",
    ]
    assert len(select_feature_layers(hidden, "all")) == 37


def test_select_layers_supports_legacy_tuple_without_embedding():
    import numpy as np

    hidden = tuple(np.zeros((2, 5, 8), dtype=np.float32) for _ in range(36))
    selected = select_feature_layers(hidden, "layers_12_24_36")
    assert selected["layer_12"] is hidden[11]
