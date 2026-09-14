import tomllib
from pathlib import Path


def test_esmc_conditioner_contract_is_explicit() -> None:
    config_path = Path(__file__).parents[1] / "configs" / "esmc_stage0.toml"
    config = tomllib.loads(config_path.read_text())

    protocol = config["protocol"]
    assert protocol["sequence_conditioner"] == "esmc_600m"
    assert protocol["conditioner_frozen"] is True
    assert protocol["use_msa"] is False

    ablations = {item["name"]: item for item in config["conditioner"]}
    assert {"esmc_300m", "esmc_600m", "esmc_6b", "esm3_sm_open"} <= ablations.keys()
    assert ablations["esm3_sm_open"]["allow_structure_track"] is False
