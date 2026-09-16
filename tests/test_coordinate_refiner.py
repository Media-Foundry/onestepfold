import torch

from onestepfold.models import CoordinateRefinerConfig, GlobalCoordinateRefiner


def _rotation_z(angle: float) -> torch.Tensor:
    c, s = torch.cos(torch.tensor(angle)), torch.sin(torch.tensor(angle))
    return torch.stack(
        (
            torch.stack((c, -s, c.new_tensor(0.0))),
            torch.stack((s, c, c.new_tensor(0.0))),
            torch.stack((c.new_tensor(0.0), c.new_tensor(0.0), c.new_tensor(1.0))),
        )
    )


def test_refiner_is_rigid_transform_consistent():
    torch.manual_seed(7)
    model = GlobalCoordinateRefiner(
        CoordinateRefinerConfig(input_dim=12, hidden_dim=32, num_layers=1, num_heads=4)
    ).eval()
    features = torch.randn(1, 5, 12)
    backbone = torch.randn(1, 5, 4, 3)
    backbone[..., 1, :] = backbone[..., 0, :] + torch.tensor([0.0, 0.0, 1.5])
    backbone[..., 2, :] = backbone[..., 1, :] + torch.tensor([1.5, 0.0, 0.0])
    backbone[..., 3, :] = backbone[..., 1, :] + torch.tensor([0.0, 1.0, 0.0])
    mask = torch.ones(1, 5, dtype=torch.bool)
    base = model(features, backbone, mask)
    rotation = _rotation_z(0.7)
    translation = torch.tensor([3.0, -2.0, 1.0])
    transformed_backbone = torch.einsum("ij,blaj->blai", rotation, backbone) + translation
    transformed = model(features, transformed_backbone, mask)
    expected_delta = torch.einsum("ij,blj->bli", rotation, base["delta_ca"])
    assert torch.allclose(transformed["delta_ca"], expected_delta, atol=1e-5)
    expected_ca = torch.einsum("ij,blj->bli", rotation, base["corrected_ca"]) + translation
    assert torch.allclose(transformed["corrected_ca"], expected_ca, atol=1e-5)


def test_refiner_masks_padded_and_invalid_frames():
    model = GlobalCoordinateRefiner(
        CoordinateRefinerConfig(input_dim=4, hidden_dim=16, num_layers=0, num_heads=4)
    ).eval()
    features = torch.zeros(1, 2, 4)
    backbone = torch.zeros(1, 2, 4, 3)
    backbone[0, 0, 1] = torch.tensor([0.0, 0.0, 1.0])
    backbone[0, 0, 2] = torch.tensor([1.0, 0.0, 1.0])
    output = model(features, backbone, torch.tensor([[True, False]]))
    assert output["delta_ca"][0, 1].abs().sum() == 0
    assert output["frame_valid"].tolist() == [[True, False]]
