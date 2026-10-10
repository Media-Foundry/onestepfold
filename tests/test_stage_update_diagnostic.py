import copy
import torch
from fastglycan.stage_update_diagnostic import StageUpdateProbe


def fixture():
    torch.manual_seed(21)
    model = torch.nn.Sequential(torch.nn.Linear(3, 4), torch.nn.Tanh(), torch.nn.Linear(4, 2))
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4, eps=1e-8)
    x = torch.randn(5, 3)
    for _ in range(3):
        optimizer.zero_grad(); model(x).square().mean().backward(); optimizer.step()
    optimizer.zero_grad(); (7 * model(x).square().sum()).backward()
    return model, optimizer, x


def test_probes_match_direct_adam_and_do_not_share_history():
    model, optimizer, _ = fixture()
    state = copy.deepcopy(optimizer.state_dict())
    probe = StageUpdateProbe(model, state)
    gradient = probe.vector(gradients=True)
    reference = copy.deepcopy(model)
    native = torch.optim.AdamW(reference.parameters(), lr=1e-4)
    native.load_state_dict(copy.deepcopy(state))
    for p, g in zip(reference.parameters(), model.parameters()):
        p.grad = g.grad.clone()
    torch.nn.utils.clip_grad_norm_(reference.parameters(), 1.)
    native.step()
    expected = torch.cat([p.detach().double().flatten() for p in reference.parameters()])
    delta, clipped, norm = probe.adam_direction(gradient, True)
    assert torch.equal(probe.origin + delta, expected)
    assert norm > 1 and clipped.norm() <= 1.000001
    assert torch.equal(probe.vector(), probe.origin)
    probe.adam_direction(gradient, False)
    again, _, _ = probe.adam_direction(gradient, True)
    assert torch.equal(delta, again)
    for key, value in state['state'].items():
        for name in value:
            assert torch.equal(value[name], probe.optimizer_state['state'][key][name])
    probe.assign(delta)
    assert torch.equal(probe.vector(), expected)
    probe.reset(); assert torch.equal(probe.vector(), probe.origin)


def test_site_weighting_and_directional_derivative():
    model = torch.nn.Linear(1, 1, bias=False).double()
    with torch.no_grad(): model.weight.fill_(2.)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    probe = StageUpdateProbe(model, optimizer.state_dict())
    gradients = []
    for target, scale in ((0., 1.), (1., 4.)):
        model.zero_grad()
        loss = (model.weight-target).square().mean()/scale
        loss.backward(); gradients.append(probe.vector(gradients=True))
    g = torch.stack(gradients).mean(0)
    assert torch.equal(g, torch.tensor([2.25], dtype=torch.double))
    direction = -g * .01
    measurement = probe.comparison(g, direction)
    assert measurement['dot'] < 0 and measurement['cosine'] == -1
    def objective():
        return float((model.weight.square() + (model.weight-1).square()/4).mean()/2)
    before = objective()
    probe.assign(direction, .001)
    assert abs((objective()-before)/.001-measurement['dot']) < 1e-6
    probe.assign(-direction, .001)
    assert objective() > before
    probe.reset(); assert torch.equal(probe.vector(), probe.origin)

