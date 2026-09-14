import pytest

from fastglycan.types import Conformer, GlycanEdit, GlycanEnsemble, SimulationCondition


def make_ensemble() -> GlycanEnsemble:
    return GlycanEnsemble(
        glycan_id="g1",
        sequence="Galb1-4Glc",
        scaffold_id="s1",
        source="test",
        condition=SimulationCondition(300.0),
        conformers=(
            Conformer("a", (-60.0, 110.0), 0.75, effective_samples=100),
            Conformer("b", (80.0, -40.0), 0.25, effective_samples=40),
        ),
    )


def test_weighted_ensemble_contract() -> None:
    ensemble = make_ensemble()
    assert ensemble.effective_sample_size == 140
    assert ensemble.as_dict()["glycan_id"] == "g1"


def test_invalid_weights_are_rejected() -> None:
    with pytest.raises(ValueError, match="sum to 1"):
        GlycanEnsemble(
            glycan_id="g1",
            sequence="x",
            scaffold_id="s1",
            source="test",
            condition=SimulationCondition(300.0),
            conformers=(Conformer("a", (0.0,), 0.5),),
        )


def test_topology_change_requires_mapping() -> None:
    with pytest.raises(ValueError, match="atom mapping"):
        GlycanEdit("e", "a", "b", "3", "Gal", "Glc", topology_preserved=False)

