#!/usr/bin/env python3
"""CPU-only shard preparation of GT-rebuilt, ESMC-backed scaling packets."""

import argparse
import json
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from biotite.structure.io import pdbx

from fastglycan.articulated_output import AA, ArticulatedOutput
from fastglycan.articulated_reference import bridge_rotations
from fastglycan.articulated_validation import numpy_project
from fastglycan.distance_supervision import build_distance_labels
from fastglycan.experimental_inputs import prepare_experimental_input
from fastglycan.frame_attribution import frame_partitions
from fastglycan.frame_supervision import build_frame_labels
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.teacher_pairing import feature_digest
from onestepfold.data.gt_materializer import ATOM37_INDEX
from onestepfold.data.teacher_pair_training import ESMCShardStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--worker", type=int, required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--input-root", type=Path,
                        help="Sequence/experimental metadata index; defaults to the original teacher index")
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--variants", type=Path, required=True)
    args = parser.parse_args()
    assert not torch.cuda.is_available()
    torch.set_num_threads(1)
    root, base = args.root, args.base
    started = time.monotonic()
    records = json.loads((root / "selection.json").read_text())
    report = json.loads((root / "selection_report.json").read_text())
    assert report["complete"] and report["selection_sha256"] == sha256(root / "selection.json")
    store = ESMCShardStore(base / "esmc_600m_final_v1")
    core = base / "stage1b/coordinate_refiner"
    graph = args.graph
    assert sha256(graph) == "fef99e421ab902dde026627fefe32138f006f49a3f9e3711d24a31b1ff87a73e"
    cif = pdbx.CIFFile.read(graph)
    components = {name: pdbx.get_component(cif, data_block=name) for name in AA.values()}
    accepted = json.loads(
        args.variants.read_text()
    )["variants"]
    outcomes = []
    for row in records[args.worker :: args.workers]:
        folder = root / "examples" / row["group_id"]
        if (folder / "prepared.json").exists():
            ready = json.loads((folder / "prepared.json").read_text())
            assert ready["complete"] and ready["selection"] == row
            for name, digest in ready["files_sha256"].items():
                assert sha256(folder / name) == digest
            assert "smooth_pair_count" in ready
            outcomes.append({"group_id": row["group_id"], "prepared_sha256": sha256(folder / "prepared.json")})
            continue
        record = SimpleNamespace(**(row | {"shard": row["input_shard"]}))
        features, labels, inventory, provenance = prepare_experimental_input(
            record,
            input_root=args.input_root or base / "stage1b/teacher_pairs_v3/input",
            stageb_root=base / "processed_stageb_v1",
            raw_root=base / "Dataset/raw/pdb_mmcif",
            folder=folder,
            store=store,
        )
        # Independent direct atom37 mask/name check; never impute missing coordinates.
        with np.load(folder / "gt.npz") as data:
            arrays = dict(data)
        ri = inventory["residue_id"].astype(int) - 1
        ai = np.array([ATOM37_INDEX[str(n)] for n in inventory["atom_name"]])
        mask = arrays["atom37_mask"][ri, ai] & arrays["residue_mask"][ri]
        assert np.array_equal(mask, labels["coordinate_mask"].numpy())
        assert np.array_equal(
            labels["coordinate"].numpy()[mask], arrays["atom37_positions"][ri[mask], ai[mask]]
        )
        assert np.all(labels["coordinate"].numpy()[~mask] == 0)
        cached = store.load(
            row["group_id"], sequence=row["sequence"], expected_length=len(row["sequence"])
        )
        idx = features["residue_index"].long() - 1
        assert torch.equal(features["esm_token_embedding"], cached[idx])
        assert features["ref_mask"].bool().all()
        variants = {}
        for residue in np.unique(inventory["residue_id"]):
            indices = np.flatnonzero(inventory["residue_id"] == residue)
            names = inventory["atom_name"][indices].tolist()
            kind = AA[row["sequence"][int(residue) - 1]]
            component = components[kind]
            by_name = {n: i for i, n in enumerate(component.atom_name)}
            mapping = {by_name[n]: i for i, n in enumerate(names)}
            assert all(
                component.element[by_name[n]] == e
                for n, e in zip(names, inventory["element"][indices], strict=True)
            )
            bonds = [
                [mapping[int(a)], mapping[int(b)], int(order)]
                for a, b, order in component.bonds.as_array()
                if a in mapping and b in mapping
            ]
            bridge_rotations(names, bonds)
            key = kind + ":" + ",".join(names)
            if key in accepted:
                assert bonds == accepted[key]["bonds"]
            variants[key] = {"residue": kind, "atom_names": names, "bonds": bonds}
        write_json(
            folder / "articulation_report.json",
            {"variants": variants, "graph_sha256": sha256(graph)},
        )
        ref = features["ref_pos"].numpy()
        adapter = ArticulatedOutput(
            ref, inventory["atom_name"], inventory["residue_id"], row["sequence"], variants
        ).double()
        x = torch.tensor(ref, dtype=torch.float64, requires_grad=True)
        y = adapter(x)["coordinate"]
        assert float((y.detach() - x.detach()).abs().max()) < 1e-5
        projected, _ = numpy_project(ref.astype(np.float64), adapter)
        assert float(np.max(np.abs(projected - y.detach().numpy()))) < 1e-8
        # Actual new atom inventories must preserve differentiability.
        weight = torch.sin(torch.arange(x.numel(), dtype=x.dtype)).reshape_as(x)
        direction = torch.cos(torch.arange(x.numel(), dtype=x.dtype)).reshape_as(x)
        grad = torch.autograd.grad((y * weight).sum(), x)[0]
        assert torch.isfinite(grad).all() and grad.norm() > 0
        with torch.no_grad():
            eps = 1e-5
            fd = (
                (
                    (
                        adapter(x + eps * direction)["coordinate"]
                        - adapter(x - eps * direction)["coordinate"]
                    )
                    * weight
                ).sum()
                / (2 * eps)
            ).item()
        vjp = (grad * direction).sum().item()
        assert abs(fd - vjp) <= 1e-4 * (1 + abs(vjp))
        frame = build_frame_labels(labels, inventory)
        same = frame_partitions(frame, inventory["residue_id"])["same_residue"]
        distances = build_distance_labels(labels, inventory)
        assert len(frame["frame_rows"]) and len(same["frame_rows"])
        assert distances["category"].bincount(minlength=4).min() > 0
        from fastglycan.smooth_lddt_supervision import build_smooth_lddt_labels
        smooth = build_smooth_lddt_labels(labels, inventory)
        torch.save({"frame": frame, "same": same, "distance": distances, "smooth": smooth}, folder / "supervision.pt")
        np.savez_compressed(folder / "labels.npz", **{k: v.numpy() for k, v in labels.items()})
        np.savez_compressed(folder / "reference.npz", reference=ref)
        files = {p.name: sha256(p) for p in sorted(folder.iterdir()) if p.is_file()}
        info = {
            "complete": True,
            "group_id": row["group_id"],
            "selection": row,
            "input_provenance": provenance,
            "files_sha256": files,
            "adapter_sha256": feature_digest(adapter.float().state_dict()),
            "new_variants": sorted(set(variants) - set(accepted)),
            "mask_independent_exact": True,
            "esmc_exact": True,
            "projection_independent_exact": True,
            "adapter_fd_error": abs(fd - vjp),
            "smooth_pair_count": len(smooth["pairs"]),
            "smooth_evaluable_atoms": int(smooth["evaluable_atoms"]),
            "distance_category_count": distances["category"].bincount(minlength=4).tolist(),
        }
        write_json(folder / "prepared.json", info)
        outcomes.append(
            {"group_id": row["group_id"], "prepared_sha256": sha256(folder / "prepared.json")}
        )
        write_json(
            root / f"progress_worker_{args.worker}.json",
            {"completed": len(outcomes), "group": row["group_id"]},
        )
        print(
            json.dumps({"worker": args.worker, "count": len(outcomes), "group": row["group_id"]}),
            flush=True,
        )
    write_json(
        root / f"worker_{args.worker}.json",
        {
            "complete": True,
            "examples": outcomes,
            "selection_sha256": sha256(root / "selection.json"),
            "seconds": time.monotonic() - started,
            "source_manifest_sha256": sha256(
                Path(__file__).resolve().parents[1] / "source_manifest.json"
            ),
        },
    )


if __name__ == "__main__":
    main()
