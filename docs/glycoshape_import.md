# GlycoShape import protocol

The supported source is the public GlycoShape download API:

```text
GET https://glycoshape.org/api/available
GET https://glycoshape.org/api/glycan/<identifier>
GET https://glycoshape.org/api/download/<identifier>
```

The download endpoint returns a ZIP containing `data.json`, `PDB/alpha.pdb`,
`PDB/beta.pdb`, and an SVG preview. The PDB files are multi-model files. The
`data.json` archive metadata contains `archetype.cluster_levels` and the
cluster percentages; `level_1` is normally the five-model representative
ensemble, but the importer checks the model count and refuses to silently
misalign weights.

Import a raw archive with:

```python
from fastglycan.glycoshape import import_glycoshape

manifest = import_glycoshape("G00028MO", "data/raw/glycoshape")
```

This creates an immutable-once-reviewed raw directory containing the original
ZIP, `data.json`, one PDB per representative model, and `manifest.json`. Alpha
and beta reducing-end variants are kept as separate ensembles; they must not be
merged as if they were one chemical graph. In practice, the requested entry ID
can be a motif/lookup ID while `data.json` gives different structure-specific
GlyTouCan IDs for the alpha and beta records. The importer therefore uses
`<structure_glytoucan_id>:<stereo>` as `glycan_id` and
`<requested_id>:<stereo>` as the scaffold grouping key, while retaining both
IDs in metadata.

The ZIP does not provide torsion vectors for each extracted model. Convert the
manifest into the project's `GlycanEnsemble` contract only after supplying an
explicit extractor:

```python
from fastglycan.glycoshape import ensembles_from_archive

def extract_torsions(stereo, pdb_path):
    # Recommended: glycontact.process.get_glycosidic_torsions(sequence, pdb_path)
    # and a fixed, documented column ordering.
    raise NotImplementedError

ensembles = ensembles_from_archive(manifest, extract_torsions)
```

The current implementation deliberately does not invent torsions from a PDB
filename or model index. Install the optional `glycoshape` extra to use
GlyContact for angle extraction, then record the exact torsion ordering in the
manifest/configuration.

## Caveats from the live API

- The archive may contain a different current cluster count than a separately
  cached GlycoShape/GlyContact mirror. The archive's own `data.json` and PDB
  model count are treated as the pair that must agree.
- GlycoShape exposes representative cluster weights, not independent frames.
  Keep the source weight and do not use representative structures as equally
  weighted samples.
- The API metadata declares temperature, pressure, force field, package, and
  salt. These are preserved as provenance; they are not evidence that the
  generated model is universally calibrated.
