"""Read-only atom-pair attribution; never changes the locked geometry policy."""
from __future__ import annotations
import numpy as np
from scipy.sparse import csr_matrix, eye
from .hybrid_geometry import RADII


def independent_allowed_pairs(atoms):
    """Sparse path powers independently exclude covalent paths of length <= 3."""
    n = len(atoms)
    bonds = np.asarray(atoms.bonds.as_array()[:, :2], dtype=int)
    i, j = bonds.T
    adjacency = csr_matrix((np.ones(2*len(i), dtype=np.int32),
                            (np.r_[i,j], np.r_[j,i])), shape=(n,n))
    reach = eye(n, dtype=np.int32, format='csr') + adjacency
    reach = reach + adjacency @ adjacency + adjacency @ adjacency @ adjacency
    return np.column_stack(np.where(np.triu(reach.toarray() == 0, 1)))


def pair_attribution(atoms, coordinates, pairs, *, observed=None, reference=None, top_k=12):
    x = np.asarray(coordinates, dtype=np.float64).reshape(-1, 3)
    if len(x) != len(atoms) or not np.isfinite(x).all():
        raise ValueError('invalid full native coordinate array')
    i, j = np.asarray(pairs).T
    radius = np.array([RADII[str(e).upper()] for e in atoms.element])
    distance = np.linalg.norm(x[i]-x[j], axis=1)
    penetration = radius[i]+radius[j]-distance
    observed = np.ones(len(x),dtype=bool) if observed is None else np.asarray(observed,bool)
    common = observed[i] & observed[j]
    residues = np.asarray(atoms.res_id)
    # Diagnostic only; excluding termini is NOT a design acceptance policy.
    terminal = (residues <= residues.min()+9) | (residues >= residues.max()-9)
    internal = ~terminal[i] & ~terminal[j]
    severe = distance < 1.
    def stats(mask):
        return dict(pair_count=int(mask.sum()), severe_pairs=int((severe & mask).sum()),
                    max_penetration=float(max(0., penetration[mask].max())) if mask.any() else None)
    def label(k):
        return dict(index=int(k),chain=str(atoms.chain_id[k]),residue=int(residues[k]),
                    residue_name=str(atoms.res_name[k]),atom=str(atoms.atom_name[k]),
                    experimentally_observed=bool(observed[k]))
    rows=[]
    for k in np.argsort(-penetration,kind='stable')[:top_k]:
        row=dict(first=label(i[k]),second=label(j[k]),distance=float(distance[k]),
                 penetration=float(penetration[k]),both_observed=bool(common[k]))
        if reference is not None and common[k]:
            row['experimental_distance']=float(np.linalg.norm(reference[i[k]]-reference[j[k]]))
        rows.append(row)
    return dict(all_atoms=stats(np.ones(len(i),bool)),observed_atoms=stats(common),
                excluding_terminal10=stats(internal),
                severe_touching_terminal10=int((severe & ~internal).sum()),
                severe_touching_unobserved=int((severe & ~common).sum()),top_pairs=rows)


def observed_bond_geometry(coordinates, topology, observed):
    """Mask both endpoints/whole chiral centres; never use missing GT zero fills."""
    x=np.asarray(coordinates,dtype=np.float64).reshape(-1,3)
    observed=np.asarray(observed,dtype=bool)
    bonds=topology.bonds.numpy();valid=observed[bonds].all(1)
    error=np.linalg.norm(x[bonds[:,0]]-x[bonds[:,1]],axis=1)-topology.ideal.numpy()
    peptide=topology.peptide.numpy() & valid
    centres=topology.centres.numpy();present=observed[centres].all(1)
    centres=centres[present];reference_volume=topology.volumes.numpy()[present]
    if len(centres):
        ca,n,c,cb=centres.T
        volume=np.sum(np.cross(x[n]-x[ca],x[c]-x[ca])*(x[cb]-x[ca]),axis=-1)
        chirality=float(np.mean(volume*reference_volume>0))
    else:chirality=None
    return dict(observed_bonds=int(valid.sum()),observed_peptides=int(peptide.sum()),
                bond_rmse=float(np.sqrt(np.mean(error[valid]**2))) if valid.any() else None,
                peptide_mae=float(np.mean(np.abs(error[peptide]))) if peptide.any() else None,
                observed_chiral_centres=len(centres),chirality_fraction=chirality)
