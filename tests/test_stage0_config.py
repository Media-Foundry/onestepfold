import tomllib
from pathlib import Path


def test_stage0_protocol_is_explicit() -> None:
    config_path = Path(__file__).parents[1] / "configs" / "protenix_stage0.toml"
    config = tomllib.loads(config_path.read_text())

    protocol = config["protocol"]
    assert protocol["model_name"] == "protenix_mini_esm_v0.5.0"
    assert protocol["use_msa"] is False
    assert protocol["use_template"] is False
    assert protocol["sample"] == 1
    assert protocol["variance_seeds"] == [101, 103, 107, 109, 113]

    sweep = [(item["cycles"], item["steps"]) for item in config["sweep"]]
    assert sweep == [(4, 5), (4, 2), (4, 1), (2, 2), (1, 2), (1, 1)]
