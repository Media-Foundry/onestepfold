"""Import GlycoShape ZIP archives into the project's explicit data contract.

The public download contains weighted representative structures, not a ready
training tensor. This module keeps the raw archive/metadata and separates PDB
model extraction from optional torsion calculation through GlyContact.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .types import Conformer, GlycanEnsemble, SimulationCondition

DOWNLOAD_URL = "https://glycoshape.org/api/download/{glytoucan_id}"


@dataclass(frozen=True, slots=True)
class GlycoShapeModel:
    """One extracted representative PDB model and its population weight."""

    stereo: str
    model_index: int
    weight: float
    structure_path: str


@dataclass(frozen=True, slots=True)
class GlycoShapeArchive:
    """Manifest for one downloaded GlycoShape archive."""

    glytoucan_id: str
    archive_path: str
    metadata_path: str
    source_metadata: dict[str, Any]
    models: tuple[GlycoShapeModel, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def models_for(self, stereo: str) -> tuple[GlycoShapeModel, ...]:
        return tuple(model for model in self.models if model.stereo == stereo)


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "fast-joint-glycan/0.1"})
    with urllib.request.urlopen(request) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _cluster_weights(metadata: dict[str, Any], n_models: int, level: str) -> list[float]:
    archetype = metadata.get("archetype", {})
    levels = archetype.get("cluster_levels", {})
    selected = levels.get(level, {})
    clusters = selected.get("clusters", {})
    weights = [
        float(value)
        for _, value in sorted(clusters.items(), key=lambda item: int(item[0].split()[-1]))
    ]
    if len(weights) != n_models:
        matching = [
            value
            for value in levels.values()
            if int(value.get("n_clusters", -1)) == n_models
        ]
        if len(matching) != 1:
            raise ValueError(
                f"cluster level {level!r} has {len(weights)} clusters but the PDB has "
                f"{n_models} models; specify a level with an exact model count"
            )
        weights = [
            float(value)
            for _, value in sorted(
                matching[0].get("clusters", {}).items(),
                key=lambda item: int(item[0].split()[-1]),
            )
        ]
    total = sum(weights)
    if total <= 0:
        raise ValueError("GlycoShape cluster weights must have a positive sum")
    return [weight / total for weight in weights]


def _split_models(
    source: Path, destination: Path, stereo: str, weights: Sequence[float]
) -> list[GlycoShapeModel]:
    text = source.read_text(encoding="utf-8")
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.splitlines(keepends=True):
        if line.startswith("MODEL"):
            if current is not None:
                raise ValueError(f"nested MODEL records in {source}")
            current = []
        elif line.startswith("ENDMDL"):
            if current is None:
                raise ValueError(f"ENDMDL without MODEL in {source}")
            blocks.append(current)
            current = None
        elif current is not None:
            current.append(line)
    if current is not None:
        raise ValueError(f"unterminated MODEL record in {source}")
    if not blocks:
        blocks = [[line for line in text.splitlines(keepends=True) if not line.startswith("END")]]
    if len(blocks) != len(weights):
        raise ValueError(
            f"{source.name}: found {len(blocks)} models but received {len(weights)} weights"
        )

    destination.mkdir(parents=True, exist_ok=True)
    models: list[GlycoShapeModel] = []
    for index, (block, weight) in enumerate(zip(blocks, weights, strict=True), start=1):
        model_path = destination / f"{stereo}_model_{index:03d}.pdb"
        model_path.write_text("".join(block) + "END\n", encoding="utf-8")
        models.append(
            GlycoShapeModel(
                stereo=stereo,
                model_index=index,
                weight=weight,
                structure_path=str(model_path),
            )
        )
    return models


def import_glycoshape(
    glytoucan_id: str,
    output_dir: str | Path,
    *,
    cluster_level: str = "level_1",
    overwrite: bool = False,
) -> GlycoShapeArchive:
    """Download and unpack one GlycoShape archive without calculating torsions."""

    if not glytoucan_id:
        raise ValueError("glytoucan_id cannot be empty")
    root = Path(output_dir) / glytoucan_id
    archive_path = root / f"{glytoucan_id}.zip"
    metadata_path = root / "data.json"
    if root.exists() and not overwrite:
        raise FileExistsError(f"destination already exists: {root}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    _download(DOWNLOAD_URL.format(glytoucan_id=glytoucan_id), archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(root)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    models: list[GlycoShapeModel] = []
    for stereo in ("alpha", "beta"):
        pdb_path = root / "PDB" / f"{stereo}.pdb"
        if not pdb_path.exists():
            continue
        model_count = sum(
            line.startswith("MODEL")
            for line in pdb_path.read_text(encoding="utf-8").splitlines()
        )
        weights = _cluster_weights(metadata, model_count, cluster_level)
        models.extend(_split_models(pdb_path, root / "models", stereo, weights))
    manifest = GlycoShapeArchive(
        glytoucan_id=glytoucan_id,
        archive_path=str(archive_path),
        metadata_path=str(metadata_path),
        source_metadata=metadata,
        models=tuple(models),
    )
    (root / "manifest.json").write_text(
        json.dumps(manifest.as_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )
    return manifest


TorsionExtractor = Callable[[str, Path], Sequence[float]]


def ensembles_from_archive(
    manifest: GlycoShapeArchive,
    torsion_extractor: TorsionExtractor,
) -> list[GlycanEnsemble]:
    """Build alpha/beta ensembles after an explicit torsion extraction step."""

    archetype = manifest.source_metadata.get("archetype", {})
    condition = SimulationCondition(
        temperature_k=float(archetype.get("temperature", 300.0)),
        pressure_bar=float(archetype["pressure"]) if archetype.get("pressure") else None,
        solvent="explicit_water",
        force_field=str(archetype.get("forcefield", "unspecified")),
        protocol=f"GlycoShape GAP {archetype.get('package', 'unknown')}",
    )
    ensembles: list[GlycanEnsemble] = []
    for stereo in ("alpha", "beta"):
        metadata = manifest.source_metadata.get(stereo, {})
        models = manifest.models_for(stereo)
        if not models or not metadata.get("glytoucan"):
            continue
        conformers = tuple(
            Conformer(
                conformer_id=f"{stereo}_{model.model_index:03d}",
                torsions_deg=tuple(
                    float(value)
                    for value in torsion_extractor(stereo, Path(model.structure_path))
                ),
                weight=model.weight,
                structure_path=model.structure_path,
                metadata={"model_index": model.model_index, "stereo": stereo},
            )
            for model in models
        )
        sequence = str(metadata.get("iupac") or metadata.get("glycam") or metadata["glytoucan"])
        wurcs = str(metadata.get("wurcs", sequence))
        topology_hash = hashlib.sha256(wurcs.encode("utf-8")).hexdigest()[:16]
        ensembles.append(
            GlycanEnsemble(
                glycan_id=f"{metadata['glytoucan']}:{stereo}",
                sequence=sequence,
                scaffold_id=f"{manifest.glytoucan_id}:{stereo}",
                conformers=conformers,
                condition=condition,
                source="GlycoShape",
                topology_hash=topology_hash,
                metadata={
                    "glycoshape_id": manifest.glytoucan_id,
                    "structure_glytoucan_id": metadata["glytoucan"],
                    "stereo": stereo,
                },
            )
        )
    return ensembles
