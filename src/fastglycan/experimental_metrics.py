"""Strict sequence/atom mapping to masked experimental coordinates."""

from __future__ import annotations

import numpy as np

from fastglycan.all_atom_metrics import compare_coordinates
from onestepfold.data.gt_materializer import (
    ATOM37_INDEX,
    ATOM37_NAMES,
    BACKBONE_NAMES,
    CANONICAL_ATOMS,
)


def validate_experimental_record(arrays, metadata, sequence, sample_id):
    length = len(sequence)
    if metadata["schema_version"] != "gt_schema_v1" or metadata["sample_id"] != sample_id:
        raise ValueError("GT schema or sample mismatch")
    if metadata["atom_vocabulary"] != "atom37_heavy_v1" or len(metadata["chains"]) != 1:
        raise ValueError("expected one atom37 protein chain")
    chain = metadata["chains"][0]
    if chain["sequence"] != sequence or chain["sequence_length"] != length:
        raise ValueError("experimental sequence mismatch")
    if metadata["model_id"] != 1 or metadata["experimental"]["model_count"] != 1:
        raise ValueError("experimental model contract mismatch")
    methods = {"X-RAY DIFFRACTION", "ELECTRON MICROSCOPY", "NEUTRON DIFFRACTION"}
    if not set(metadata["experimental"]["methods"]).intersection(methods):
        raise ValueError("unsupported experimental method")
    if metadata["provenance"]["protocol_version"] != "gt_protocol_v1":
        raise ValueError("experimental protocol mismatch")
    if len(chain["residues"]) != length:
        raise ValueError("residue metadata length mismatch")
    if not np.array_equal(arrays["residue_index"], np.arange(1, length + 1)):
        raise ValueError("GT label indices must be one-based and contiguous")
    if np.any(arrays["chain_index"] != 0) or arrays["chain_index"].shape != (length,):
        raise ValueError("GT chain indices mismatch")
    alphabet = "ACDEFGHIKLMNPQRSTVWY"
    if not np.array_equal(arrays["aatype"], [alphabet.index(a) for a in sequence]):
        raise ValueError("GT residue identities mismatch")
    positions, mask = arrays["atom37_positions"], arrays["atom37_mask"]
    if positions.shape != (length, 37, 3) or mask.shape != (length, 37):
        raise ValueError("GT atom array shapes mismatch")
    if mask.dtype != np.bool_ or arrays["residue_mask"].dtype != np.bool_:
        raise ValueError("GT masks must be boolean")
    if not np.array_equal(arrays["residue_mask"], mask.any(axis=1)):
        raise ValueError("inconsistent observed residue mask")
    if not np.isfinite(positions[mask]).all():
        raise ValueError("nonfinite observed GT coordinates")
    if "imputed_mask" in arrays and np.any(arrays["imputed_mask"]):
        raise ValueError("imputed coordinates are not experimental labels")
    for index, residue in enumerate(chain["residues"]):
        if residue["label_seq_id"] != index + 1 or residue["aatype"] != sequence[index]:
            raise ValueError("GT residue metadata identity mismatch")
        allowed = CANONICAL_ATOMS[sequence[index]] | ({"OXT"} if index == length - 1 else set())
        if residue["is_modified_residue"]:
            allowed = allowed.intersection(BACKBONE_NAMES)
        observed = {ATOM37_NAMES[i] for i in np.flatnonzero(mask[index])}
        if not observed.issubset(allowed):
            raise ValueError("invalid or modified-sidechain experimental label")


def prediction_atom37(prediction, sequence):
    length = len(sequence)
    coordinates = np.asarray(prediction["coordinate"])
    names, residues, elements = (
        np.asarray(prediction[key]) for key in ("atom_name", "residue_id", "element")
    )
    if coordinates.shape != (len(names), 3) or any(
        x.shape != names.shape for x in (residues, elements)
    ):
        raise ValueError("prediction atom arrays mismatch")
    if not np.isfinite(coordinates).all():
        raise ValueError("nonfinite prediction coordinates")
    if not np.issubdtype(residues.dtype, np.integer):
        raise ValueError("residue IDs must be integers")
    positions, mask = np.zeros((length, 37, 3), np.float32), np.zeros((length, 37), bool)
    for point, name, residue, element in zip(coordinates, names, residues, elements, strict=True):
        if not 1 <= residue <= length:
            raise ValueError("prediction residue out of range")
        allowed = CANONICAL_ATOMS[sequence[residue - 1]] | ({"OXT"} if residue == length else set())
        if name not in allowed or name not in ATOM37_INDEX or element != name[0]:
            raise ValueError("invalid prediction atom identity")
        slot = (int(residue) - 1, ATOM37_INDEX[name])
        if mask[slot]:
            raise ValueError("duplicate prediction atom key")
        positions[slot], mask[slot] = point, True
    return positions, mask


def compare_experimental(prediction, arrays, sequence, *, expected_prediction_mask=None):
    positions, predicted_mask = prediction_atom37(prediction, sequence)
    if expected_prediction_mask is not None and not np.array_equal(
        predicted_mask, expected_prediction_mask
    ):
        raise ValueError("prediction inventories differ across conditions")
    observed = arrays["atom37_mask"] & arrays["residue_mask"][:, None]
    common = observed & predicted_mask
    ca_mask = np.nonzero(common)[1] == ATOM37_INDEX["CA"]
    ca_count, atom_count = int(ca_mask.sum()), int(common.sum())
    if ca_count < 3:
        raise ValueError("fewer than three observed common CA atoms")
    metrics = compare_coordinates(positions[common], arrays["atom37_positions"][common], ca_mask)
    return {
        **metrics,
        "common_atom_count": atom_count,
        "common_ca_count": ca_count,
        "common_ca_pair_count": ca_count * (ca_count - 1) // 2,
        "observed_gt_atom_count": int(observed.sum()),
        "predicted_gt_coverage": atom_count / int(observed.sum()),
        "missing_gt_residue_count": int((~arrays["residue_mask"]).sum()),
    }
