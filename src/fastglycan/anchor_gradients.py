"""Instantaneous gradient decomposition for a paired WT-reference suffix."""
import torch


def flat_gradients(loss, parameters, *, retain_graph=False):
    values = torch.autograd.grad(loss, parameters, retain_graph=retain_graph)
    return torch.cat([g.detach().reshape(-1) for g in values])


def gradient_alignment(left, right):
    scale = float(left.norm()) * float(right.norm())
    return float(left.dot(right)) / scale if scale > 0 else None


def gradient_description(vectors):
    return dict(norms={k: float(v.norm()) for k, v in vectors.items()},
        raw_aa_cosine=gradient_alignment(vectors['raw'], vectors['aa']),
        anchored_aa_cosine=gradient_alignment(vectors['anchored'], vectors['aa']),
        raw_common_cosine=gradient_alignment(vectors['raw'], vectors['common']),
        anchored_common_cosine=gradient_alignment(vectors['anchored'], vectors['anchored_common']),
        common_aa_cosine=gradient_alignment(vectors['common'], vectors['aa']),
        anchored_common_aa_cosine=gradient_alignment(vectors['anchored_common'], vectors['aa']))


def initial_site_gradients(model, candidates, reference_base, reference_boundary,
                           reference_pair, position, original, scale):
    """All candidate predictions must equal their frozen baseline at this point.

    candidates contains (aa_index, base, block13, TRAIN label). Labels enter
    losses/VJPs only. The reference VJP changes raw and common gradients equally,
    leaving the centered-AA gradient unchanged in real arithmetic.
    """
    parameters = list(model.parameters())
    mean_error = torch.stack([(base[2] - target).double()
                             for _, base, _, target in candidates]).mean(0).to(candidates[0][1][2])
    raw_sum = common_sum = None
    error_sum = None
    energy = 0.
    for aa, base, boundary, target in candidates:
        conditioning, _ = model.run_pair_suffix(base, boundary, reference_pair,
                                                position, original, aa)
        prediction = conditioning[2]
        assert torch.equal(prediction, base[2])
        assert conditioning[0] is base[0] and conditioning[1] is base[1]
        loss = (prediction - target).square().mean() / scale / len(candidates)
        raw = flat_gradients(loss, parameters, retain_graph=True)
        surrogate = 2 * (prediction * mean_error).mean() / scale / len(candidates)
        common = flat_gradients(surrogate, parameters)
        raw_sum = raw if raw_sum is None else raw_sum + raw
        common_sum = common if common_sum is None else common_sum + common
        error = prediction.detach().double() - target.double()
        energy += float(error.square().sum())
        error_sum = error if error_sum is None else error_sum + error
    reference, _ = model.run_pair_suffix(reference_base, reference_boundary, reference_pair,
                                         position, original, original)
    assert torch.equal(reference[2], reference_base[2])
    reference_vjp = flat_gradients(2 * (reference[2] * mean_error).mean() / scale, parameters)
    raw, common, reference_vjp = [g.cpu().double() for g in (raw_sum, common_sum, reference_vjp)]
    vectors = dict(raw=raw, common=common, aa=raw-common, reference=reference_vjp,
                   anchored=raw-reference_vjp, anchored_common=common-reference_vjp)
    raw_error = energy / len(candidates) / error_sum.numel() / scale
    common_error = float((error_sum / len(candidates)).square().mean()) / scale
    return vectors, dict(raw=raw_error, common=common_error, centered=raw_error-common_error,
                         **gradient_description(vectors))
