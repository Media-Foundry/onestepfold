"""Separate output carbonyl geometry from immutable native input references."""
import numpy as np

from fastglycan.articulated_output import AA


def calibrate_output_reference(reference, atom_names, residue_ids, sequence, variants, parameters):
    """Change only interior C/O rays; keep topology, rings and termini intact."""
    original=np.asarray(reference,dtype=np.float64)
    names=np.asarray(atom_names);ids=np.asarray(residue_ids)
    if original.shape!=(len(names),3) or ids.shape!=names.shape or not np.isfinite(original).all():
        raise ValueError('invalid reference inventory')
    if not np.array_equal(np.unique(ids),np.arange(1,len(sequence)+1)):
        raise ValueError('noncontiguous residue inventory')
    result=original.copy();records=[]
    for residue in range(2,len(sequence)):
        ix=np.flatnonzero(ids==residue);local=names[ix].tolist()
        if len(set(local))!=len(local) or not {'N','CA','C','O'}.issubset(local):
            raise ValueError('missing or duplicate backbone atoms')
        variant=variants[AA[sequence[residue-1]]+':'+','.join(local)]
        if variant['atom_names']!=local:raise ValueError('variant inventory mismatch')
        ca,c,o=[local.index(n) for n in ['CA','C','O']]
        neighbors=[set() for _ in local]
        for a,b,_ in variant['bonds']:
            neighbors[a].add(b);neighbors[b].add(a)
        if c not in neighbors[ca] or o not in neighbors[c]:raise ValueError('missing carbonyl bonds')
        neighbors[ca].remove(c);neighbors[c].remove(ca)
        reached={c};frontier=[c]
        while frontier:
            node=frontier.pop()
            for next_node in neighbors[node]-reached:
                reached.add(next_node);frontier.append(next_node)
        if reached!={c,o}:raise ValueError('CA-C cut does not isolate interior C/O')
        target=parameters[sequence[residue-1]]
        if not target['supported']:raise ValueError('unsupported calibration amino acid')
        a=float(target['metrics']['ca_c']['median']);b=float(target['metrics']['c_o']['median'])
        if not np.isfinite([a,b]).all() or min(a,b)<=0:raise ValueError('invalid target lengths')
        ca,c,o=ix[[ca,c,o]]
        u=original[c]-original[ca];v=original[o]-original[c]
        lu=float(np.linalg.norm(u));lv=float(np.linalg.norm(v))
        if min(lu,lv)<1e-8:raise ValueError('degenerate reference carbonyl')
        result[c]=original[ca]+u*(a/lu)
        result[o]=result[c]+v*(b/lv)
        records.append(dict(residue=residue,amino_acid=sequence[residue-1],
            original_ca_c=lu,original_c_o=lv,target_ca_c=a,target_c_o=b))
    return result,records
