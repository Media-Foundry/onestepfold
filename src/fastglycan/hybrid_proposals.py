"""Single-substitution proposal sets; no candidate is accepted from soft loss."""
import numpy as np
import torch
from .models.soft_esm import AMINO_ACIDS


def mutation_proposals(sequence,probability_gradient,*,budget=8,seed=271):
    if probability_gradient.shape!=(len(sequence),20):raise ValueError('gradient shape mismatch')
    g=probability_gradient.detach().cpu().double().numpy()
    if not np.isfinite(g).all():raise ValueError('nonfinite proposal gradient')
    options=[]
    for i,old in enumerate(sequence):
        old_index=AMINO_ACIDS.index(old)
        for j,aa in enumerate(AMINO_ACIDS):
            if aa!=old:options.append((float(g[i,j]-g[i,old_index]),i,aa))
    if budget>len(options):raise ValueError('candidate budget too large')
    ranked=sorted(options,key=lambda x:(x[0],x[1],x[2]))[:budget]
    # Sampling can overlap the gradient set; this is a legitimate matched baseline.
    rng=np.random.default_rng(seed)
    random=[options[j] for j in rng.choice(len(options),budget,replace=False)]
    def records(rows):
        return [dict(position=i,from_aa=sequence[i],to_aa=aa,predicted_delta=delta,
                     sequence=sequence[:i]+aa+sequence[i+1:]) for delta,i,aa in rows]
    return dict(gradient=records(ranked),random=records(random))


def identity_noise(atoms,seed,*,device='cpu'):
    """Common raw Gaussian noise keyed by chain, residue, and atom identity."""
    import hashlib
    noise=[]
    for chain,res,name in zip(atoms.chain_id,atoms.res_id,atoms.atom_name):
        key=f'hybrid-v1:{seed}:{str(chain)}:{int(res)}:{str(name)}'.encode()
        rng=np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:8],'little'))
        noise.append(rng.standard_normal(3))
    return torch.tensor(np.asarray(noise),device=device,dtype=torch.float32)[None]*2560
