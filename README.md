# OneStepFold

This repository is now focused on a strict, open, MSA-off protein folding
experiment with a multi-chain-aware catalog and a monomer-first training view:

```text
sequence -> one Pairformer cycle -> one all-atom structure-module evaluation
```

The active OneStepFold conditioner is frozen ESMC-600M with cached per-residue
embeddings. The folding core targets `N_cycle=1`, `N_step=1`, and `N_sample=1`.
The official `protenix_mini_esm_v0.5.0` path remains a compatibility baseline;
it is not treated as an ESMC checkpoint.

The proposed research method is a randomly initialized ESMC-conditioned folding
core trained with conditional Clean-Structure MeanFlow, compared against a
matched Protenix initialization and a consistency-distillation baseline.
Existing glycan import code remains in `src/fastglycan` as a preserved
historical prototype; it is no longer the primary research target.

The first data milestone is the structure-first GT v1 catalog. The staged
SIFTS-linked PDB entry universe is scanned with Gemmi into entry/entity/chain/
assembly metadata before any coordinates are materialized. See
`docs/gt_protocol_v1.md`, `schemas/gt_schema_v1.json`, and
`reports/raw_snapshot_acceptance.md` for the frozen contract and current data
status.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
python -m fastglycan audit data/examples/ensembles.jsonl  # legacy smoke test
```

The package is intentionally dependency-light while the Protenix runtime is
kept as an external experiment dependency. See
`docs/protein_direction.md`, `configs/protenix_stage0.toml`, and
`configs/esmc_stage0.toml` for the first matrix runs.

To run Stage A in the data environment:

```bash
PYTHONPATH=src python scripts/scan_mmcif_catalog.py \
  --raw-dir /hpc2hdd/home/shuang886/Folding/Dataset/raw/pdb_mmcif \
  --sifts-csv /hpc2hdd/home/shuang886/Folding/Dataset/raw/sifts/2026-09-08/pdb_chain_uniprot.csv.gz \
  --output /hpc2hdd/home/shuang886/Folding/Dataset/catalog_v1/entries.jsonl.gz \
  --errors /hpc2hdd/home/shuang886/Folding/Dataset/catalog_v1/errors.jsonl
```

Stage A does not perform SI grouping, split generation, ESMC embedding, or
coordinate materialization. The frozen monomer eligibility policy is documented
in `docs/monomer_quality_policy_v1.md`. Stage B quality v1 and generated split
views are recorded in `reports/stageb_full_acceptance.md` and
`docs/sequence_split_v1.md`.

The exact-identity and near-homology audits use Biopython
`Bio.Align.PairwiseAligner` in global mode. See `docs/sequence_split_v1.md` for
the generated train, temporal-test, leakage-excluded, and low-homology views.

## Layout

- `src/fastglycan/`: preserved glycan data contracts and importer from the
  previous direction.
- `configs/`: protein Stage 0 experiment configurations and legacy templates.
- `docs/protein_direction.md`: current model, training, and evaluation contract.
- `docs/glycoshape_import.md`: archived glycan data protocol.
- `.agents/memory/`: persistent project context and decision log for future work.

## Current evaluation rules

1. MSA-off, monomer-first training/evaluation, one paired seed, and one output
   sample are the default protocol for the first comparison; the catalog and GT
   schema remain multi-chain-aware for the future multimer view.
2. Report structure-core latency separately from ESM and end-to-end latency.
3. Report `N_cycle`, structure NFE, seed variance, peak VRAM, and sequence-length
   bins with every quality number.
4. Never call the Clean-Structure MeanFlow objective valid without an explicit
   geometry/path and JVP correctness test.

The Protenix Mini-ESM checkpoint is retained as a reference baseline. The
active ESMC path uses a versioned ESMC embedding cache and a learned input
adapter; ESMC and the folding core must not be conflated in latency or model
parameter counts.
