"""Terminal conditioning interventions; no teacher values enter construction."""


def pair_split_conditioning(base, adapted, mean_pair_delta, mode):
    """Mean is over the same site's 19 AA deltas, never over residue/channel.

    Exact endpoints return their original objects. Other conditions preserve
    the actual candidate's native inputs and unadapted final single state.
    """
    if mode == 'disabled':
        return base
    if mode == 'full':
        return adapted
    if mode == 'pair':
        return base[0], base[1], adapted[2]
    if mode == 'common':
        return base[0], base[1], base[2] + mean_pair_delta
    if mode == 'aa':
        return base[0], base[1], base[2] + ((adapted[2] - base[2]) - mean_pair_delta)
    raise ValueError(mode)
