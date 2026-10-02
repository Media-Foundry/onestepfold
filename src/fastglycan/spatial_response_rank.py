"""Per-mutant residue-axis compression; never compress the amino-acid axis."""
import torch

SPATIAL_RANKS = (0, 4, 8, 16, 32, 64, 'full')
SPATIAL_VARIANTS = ('channel', 'shared')


class SpatialResponseBasis:
    """FP64 oracle decompositions of a single [L,L,C] hard response.

    channel: independent optimal truncated matrix SVD for each channel.
    shared: two residue bases from HOSVD, with an unrestricted [R,R,C] core.
    Shared is not optimal Tucker fitting, nor a learned common channel decoder.
    Neither construction symmetrizes z, centers across AA, or changes s.
    """
    def __init__(self, wt_z, target_z):
        if wt_z.shape != target_z.shape or wt_z.ndim != 3 or wt_z.shape[0] != wt_z.shape[1]:
            raise ValueError('expected matching square [L,L,C] pair states')
        if not torch.isfinite(wt_z).all() or not torch.isfinite(target_z).all():
            raise ValueError('nonfinite pair state')
        self.wt = wt_z
        self.delta = target_z.double() - wt_z.double()
        self.length, _, self.channels = wt_z.shape
        self.energy = float(self.delta.square().sum())
        self.u, self.sigma, self.vh = torch.linalg.svd(self.delta.permute(2, 0, 1), full_matrices=False)
        left = torch.einsum('ikc,jkc->ij', self.delta, self.delta)
        right = torch.einsum('kic,kjc->ij', self.delta, self.delta)
        self.left = torch.linalg.eigh((left + left.T) * .5)[1].flip(1)
        self.right = torch.linalg.eigh((right + right.T) * .5)[1].flip(1)

    def rank_value(self, rank):
        if rank not in SPATIAL_RANKS:
            raise ValueError('rank outside locked grid')
        return self.length if rank == 'full' else min(rank, self.length)

    def core(self, rank):
        r = self.rank_value(rank)
        return torch.einsum('ir,ijc,js->rsc', self.left[:, :r], self.delta, self.right[:, :r])

    def reconstruct(self, variant, rank):
        if variant not in SPATIAL_VARIANTS:
            raise ValueError('unknown spatial representation')
        r = self.rank_value(rank)
        if variant == 'channel':
            d = ((self.u[:, :, :r] * self.sigma[:, None, :r]) @ self.vh[:, :r, :]).permute(1, 2, 0)
        else:
            d = torch.einsum('ir,rsc,js->ijc', self.left[:, :r], self.core(rank), self.right[:, :r])
        return (self.wt.double() + d).to(self.wt.dtype)

    def evidence(self):
        rows = []
        channel_energy = self.sigma.square().sum(-1)
        for variant in SPATIAL_VARIANTS:
            for rank in SPATIAL_RANKS:
                r = self.rank_value(rank)
                kept = self.sigma[:, :r].square().sum(-1) if variant == 'channel' else self.core(rank).square().sum((0, 1))
                # Singular values may be absorbed into either factor.
                parameters = 2 * self.length * r * self.channels if variant == 'channel' else 2 * self.length * r + r * r * self.channels
                rows.append(dict(variant=variant,rank=rank,effective_rank=r,
                    energy_retained=float(kept.sum())/self.energy if self.energy else None,
                    channel_energy_retained=[float(x/y) if y > 0 else None for x,y in zip(kept,channel_energy)],
                    factor_elements=parameters,dense_elements=self.wt.numel(),factor_to_dense=parameters/self.wt.numel()))
        return dict(shape=list(self.wt.shape),response_energy=self.energy,rows=rows)
