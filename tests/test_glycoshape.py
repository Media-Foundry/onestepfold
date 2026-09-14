import json
import zipfile
from pathlib import Path

from fastglycan.glycoshape import ensembles_from_archive, import_glycoshape


def test_archive_import_splits_models_and_normalizes_weights(tmp_path, monkeypatch):
    archive_path = tmp_path / "source.zip"
    metadata = {
        "archetype": {
            "cluster_levels": {
                "level_1": {"n_clusters": 2, "clusters": {"Cluster 0": 75, "Cluster 1": 25}}
            },
            "temperature": 300,
            "pressure": 1,
            "forcefield": "GLYCAM_06j",
            "package": "GROMACS",
        },
        "alpha": {"glytoucan": "GTEST", "iupac": "A"},
        "beta": {},
    }
    pdb = (
        "MODEL        1\n"
        "ATOM      1  C1  A   1       0.0     0.0     0.0\n"
        "ENDMDL\n"
        "MODEL        2\n"
        "ATOM      1  C1  A   1       1.0     1.0     1.0\n"
        "ENDMDL\n"
    )
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("data.json", json.dumps(metadata))
        archive.writestr("PDB/alpha.pdb", pdb)

    def fake_download(_url, destination: Path):
        destination.write_bytes(archive_path.read_bytes())

    monkeypatch.setattr("fastglycan.glycoshape._download", fake_download)
    manifest = import_glycoshape("GTEST", tmp_path / "out")
    models = manifest.models_for("alpha")
    assert len(models) == 2
    assert [model.weight for model in models] == [0.75, 0.25]
    assert Path(models[0].structure_path).exists()
    assert (tmp_path / "out" / "GTEST" / "manifest.json").exists()

    ensembles = ensembles_from_archive(manifest, lambda _stereo, _path: (-60.0, 110.0))
    assert len(ensembles) == 1
    assert ensembles[0].glycan_id == "GTEST:alpha"
    assert ensembles[0].scaffold_id == "GTEST:alpha"
