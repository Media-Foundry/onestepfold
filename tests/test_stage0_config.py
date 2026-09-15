import tomllib
from pathlib import Path


def test_stage0_protocol_is_explicit() -> None:
    config_path = Path(__file__).parents[1] / "configs" / "protenix_stage0.toml"
    config = tomllib.loads(config_path.read_text())

    protocol = config["protocol"]
    assert protocol["model_name"] == "protenix_mini_esm_v0.5.0"
    assert protocol["protenix_package"] == "protenix==1.1.0"
    assert protocol["protenix_revision"] == "required-before-run"
    assert protocol["checkpoint_sha256"] == "required-before-run"
    assert protocol["use_msa"] is False
    assert protocol["use_template"] is False
    assert protocol["sample"] == 1
    assert protocol["variance_seeds"] == [101, 103, 107, 109, 113]

    assert protocol["max_length"] == 1024
    assert protocol["temporal_dev_groups"] == 1024
    assert protocol["variance_subset_groups"] == 128
    assert protocol["anchor"] == "c4_s5"
    assert protocol["component_timing_status"] == "requires-Protenix-internal-hooks"

    sweep = {(item["cycles"], item["steps"]) for item in config["sweep"]}
    assert sweep == {(cycles, steps) for cycles in (1, 2, 4) for steps in (1, 2, 5)}
    assert len(config["sweep"]) == 9
    assert config["evaluation"]["length_bins"][-1] == "769-1024"
