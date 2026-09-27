import numpy as np
import pytest
import torch

from fastglycan.scaling_metrics import lddt_observed
from fastglycan.smooth_lddt_supervision import build_smooth_lddt_labels, smooth_lddt_loss


def example():
    # Unequal neighborhood degrees distinguish atom means from pair means;
    # the last atom is missing and the penultimate atom has no neighbors.
    coordinate = torch.tensor(
        [[0, 0, 0], [1, 0, 0], [2, 1, 0], [14, 0, 0], [16, 0, 0], [80, 0, 0], [np.nan] * 3],
        dtype=torch.float64,
    )
    labels = {"coordinate": coordinate, "coordinate_mask": torch.tensor([True] * 6 + [False])}
    inventory = {
        "residue_id": np.array([1, 1, 2, 3, 4, 5, 6]),
        "atom_name": np.array(["N", "CA", "CA", "CA", "CA", "CA", "CA"]),
    }
    return labels, inventory


def independent_scores(prediction, target, mask, residues):
    """Dense NumPy reference reconstructed from coordinates, not sparse labels."""
    atom_smooth, atom_hard = [], []
    x, y = np.asarray(prediction), np.asarray(target)
    for i in np.flatnonzero(mask):
        smooth, hard = [], []
        for j in np.flatnonzero(mask):
            reference = np.linalg.norm(y[i] - y[j])
            if residues[i] == residues[j] or reference >= 15.0:
                continue
            error = abs(np.linalg.norm(x[i] - x[j]) - reference)
            logits = (np.array([0.5, 1.0, 2.0, 4.0]) - error) / 0.1
            # Stable NumPy sigmoid, independent of torch and label weights.
            smooth.append(np.exp(-np.logaddexp(0.0, -logits)).mean())
            hard.append((error < np.array([0.5, 1.0, 2.0, 4.0])).mean())
        if smooth:
            atom_smooth.append(np.mean(smooth))
            atom_hard.append(np.mean(hard))
    return (np.mean(atom_smooth), np.mean(atom_hard)) if atom_smooth else (np.nan, np.nan)


def test_neighborhood_atom_reduction_and_existing_metric_agree():
    labels, inventory = example()
    sup = build_smooth_lddt_labels(labels, inventory)
    pairs = sup["pairs"].numpy()
    assert [0, 1] not in pairs.tolist()  # Same-residue pair.
    assert [1, 4] not in pairs.tolist()  # Exactly 15 A is excluded.
    assert not np.isin(pairs, [5, 6]).any()
    assert sup["evaluable_atoms"].item() == 5
    assert np.isclose(sup["pair_weight"].sum().item(), 1.0)
    x = labels["coordinate"].clone()
    x[0] += torch.tensor([1.7, -0.3, 0.2])
    smooth, hard = independent_scores(
        x.numpy(), labels["coordinate"].numpy(), labels["coordinate_mask"].numpy(),
        inventory["residue_id"],
    )
    assert smooth_lddt_loss(x, sup).item() == pytest.approx(1 - smooth, abs=1e-12)
    valid = labels["coordinate_mask"].numpy()
    metric = lddt_observed(
        x.numpy()[valid], labels["coordinate"].numpy()[valid], inventory["residue_id"][valid]
    )
    assert metric["score"] == pytest.approx(hard, abs=1e-12)
    assert metric["evaluable_atoms"] == 5 and metric["atoms_without_neighbors"] == 1
    errors = np.abs(
        np.linalg.norm(x.numpy()[pairs[:, 0]] - x.numpy()[pairs[:, 1]], axis=1)
        - sup["target_distance"].numpy()
    )
    pair_average = np.exp(
        -np.logaddexp(0, -(np.array([0.5, 1, 2, 4]) - errors[:, None]) / 0.1)
    ).mean()
    assert abs(smooth - pair_average) > 1e-3


def test_mask_isolation_rigid_invariance_and_finite_difference():
    labels, inventory = example()
    sup = build_smooth_lddt_labels(labels, inventory)
    x = labels["coordinate"].clone()
    x[0] += torch.tensor([0.7, -0.2, 0.1])
    x[2] += torch.tensor([-0.4, 0.3, 0.2])
    x.requires_grad_(True)
    loss = smooth_lddt_loss(x, sup)
    (gradient,) = torch.autograd.grad(loss, x)
    assert torch.isfinite(loss) and torch.isfinite(gradient).all()
    assert gradient.norm() > 0 and gradient[5:].count_nonzero() == 0
    direction = gradient / gradient.norm()
    h = 1e-6
    numerical = (
        smooth_lddt_loss(x + h * direction, sup) - smooth_lddt_loss(x - h * direction, sup)
    ) / (2 * h)
    assert numerical.item() == pytest.approx(
        (direction * gradient).sum().item(), rel=1e-6, abs=1e-9
    )
    rotation = x.new_tensor([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
    assert smooth_lddt_loss(x @ rotation + 23.0, sup).item() == pytest.approx(
        loss.item(), abs=1e-12
    )
    labels["coordinate"][-1] = torch.tensor([np.inf, -np.inf, np.nan])
    relabeled = build_smooth_lddt_labels(labels, inventory)
    assert all(torch.equal(value, relabeled[key]) for key, value in sup.items())


def test_perfect_near_bad_and_saturation():
    labels = {
        "coordinate": torch.tensor([[0, 0, 0], [2, 0, 0]], dtype=torch.float64),
        "coordinate_mask": torch.ones(2, dtype=torch.bool),
    }
    inventory = {"residue_id": np.array([1, 2]), "atom_name": np.array(["CA", "CA"])}
    sup = build_smooth_lddt_labels(labels, inventory)
    losses = []
    for distance in (2.0, 2.75, 200.0):
        x = torch.tensor([[0, 0, 0], [distance, 0, 0]], dtype=torch.float64, requires_grad=True)
        loss = smooth_lddt_loss(x, sup)
        (gradient,) = torch.autograd.grad(loss, x)
        assert torch.isfinite(gradient).all()
        losses.append(loss.item())
        if distance == 2.75:
            assert gradient.norm() > 0
        if distance == 200.0:
            assert gradient.abs().max() < 1e-10
    assert 0 < losses[0] < 0.002 and losses[0] < losses[1] < losses[2] <= 1
    collapsed = torch.zeros((2, 3), dtype=torch.float64, requires_grad=True)
    (gradient,) = torch.autograd.grad(smooth_lddt_loss(collapsed, sup), collapsed)
    assert torch.isfinite(gradient).all()


@pytest.mark.parametrize("mask", [[True, True], [False, False]])
def test_empty_neighborhood_is_differentiable_zero(mask):
    labels = {
        "coordinate": torch.tensor([[0, 0, 0], [30, 0, 0]], dtype=torch.float64),
        "coordinate_mask": torch.tensor(mask),
    }
    inventory = {"residue_id": np.array([1, 2]), "atom_name": np.array(["CA", "CA"])}
    sup = build_smooth_lddt_labels(labels, inventory)
    assert sup["pairs"].shape == (0, 2) and sup["evaluable_atoms"] == 0
    x = torch.full((2, 3), np.nan, dtype=torch.float64, requires_grad=True)
    loss = smooth_lddt_loss(x, sup)
    (gradient,) = torch.autograd.grad(loss, x)
    assert loss.item() == 0 and torch.equal(gradient, torch.zeros_like(gradient))


def test_reject_invalid_observed_coordinates_and_atom_identity():
    labels, inventory = example()
    labels["coordinate"][0, 0] = np.nan
    with pytest.raises(ValueError, match="nonfinite observed"):
        build_smooth_lddt_labels(labels, inventory)
    labels, inventory = example()
    inventory["atom_name"][1] = "N"
    with pytest.raises(ValueError, match="duplicate"):
        build_smooth_lddt_labels(labels, inventory)


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_deterministic_execution_and_float32_autocast(device):
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA unavailable")
    labels, inventory = example()
    sup = build_smooth_lddt_labels(labels, inventory)
    previous = torch.are_deterministic_algorithms_enabled()
    try:
        torch.use_deterministic_algorithms(True)
        values, gradients = [], []
        for _ in range(2):
            x = labels["coordinate"].to(device=device, dtype=torch.float32).clone()
            x[0] += 0.75
            x.requires_grad_(True)
            with torch.autocast(device_type=device, dtype=torch.bfloat16):
                loss = smooth_lddt_loss(x, sup)
            (gradient,) = torch.autograd.grad(loss, x)
            assert loss.dtype == torch.float32 and torch.isfinite(gradient).all()
            values.append(loss.detach())
            gradients.append(gradient)
        assert torch.equal(values[0], values[1]) and torch.equal(gradients[0], gradients[1])
    finally:
        torch.use_deterministic_algorithms(previous)
