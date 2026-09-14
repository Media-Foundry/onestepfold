from pathlib import Path

from fastglycan.audit import audit_ensembles
from fastglycan.io import load_ensembles
from fastglycan.models import WeightedEmpiricalModel


def test_example_loads_and_audits() -> None:
    path = Path("data/examples/ensembles.jsonl")
    ensembles = load_ensembles(path)
    report = audit_ensembles(ensembles)
    assert report.ok
    assert report.conformer_count == 2


def test_empirical_model_respects_weights() -> None:
    ensemble = load_ensembles("data/examples/ensembles.jsonl")
    model = WeightedEmpiricalModel(ensemble)
    samples = model.sample("example_parent", 1000, seed=7)
    assert len(samples) == 1000
    assert model.log_prob("example_parent", (-65.0, 110.0)) < 0

