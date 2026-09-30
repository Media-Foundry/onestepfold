"""Whole CCD ideal local geometry for output construction only."""
import numpy as np

from fastglycan.articulated_output import AA


def ideal_output_reference(reference, atom_names, residue_ids, sequence, variants, templates):
    """Replace complete interior residues by rigidly aligned named CCD templates.

    Retain native termini, CA anchors and the caller's native covalent graph.
    Adjacency is checked by atom identity; bond order is not reinterpreted.
    """
    original = np.asarray(reference, dtype=np.float64)
    names = np.asarray(atom_names); ids = np.asarray(residue_ids)
    if original.shape != (len(names), 3) or ids.shape != names.shape or not np.isfinite(original).all():
        raise ValueError('invalid reference inventory')
    if not np.array_equal(np.unique(ids), np.arange(1, len(sequence)+1)):
        raise ValueError('noncontiguous residue inventory')
    result = original.copy(); records = []
    def basis(x, lookup):
        ca = x[lookup['CA']]
        e1 = x[lookup['C']] - ca
        n1 = np.linalg.norm(e1)
        if n1 < 1e-8: raise ValueError('degenerate CA-C frame')
        e1 = e1/n1
        e2 = x[lookup['N']] - ca
        e2 = e2 - np.dot(e1, e2)*e1
        n2 = np.linalg.norm(e2)
        if n2 < 1e-8: raise ValueError('degenerate N-CA-C frame')
        e2 = e2/n2
        return np.stack([e1, e2, np.cross(e1, e2)], axis=1)
    for residue in range(2, len(sequence)):
        aa = sequence[residue-1]; ix = np.flatnonzero(ids == residue)
        local = names[ix].tolist(); template = templates[aa]; tn = template['atom_names']
        if len(set(local)) != len(local) or len(set(tn)) != len(tn) or set(local) != set(tn):
            raise ValueError('ideal/native atom inventory mismatch')
        variant = variants[AA[aa]+':'+','.join(local)]
        if variant['atom_names'] != local: raise ValueError('variant inventory mismatch')
        native_edges = {tuple(sorted((local[a], local[b]))) for a,b,_ in variant['bonds']}
        ideal_edges = {tuple(sorted((tn[a], tn[b]))) for a,b,_ in template['bonds']}
        if native_edges != ideal_edges: raise ValueError('ideal/native adjacency mismatch')
        lookup = {n:i for i,n in enumerate(local)}
        ideal = np.asarray(template['ideal'], dtype=np.float64)[[tn.index(n) for n in local]]
        if not np.isfinite(ideal).all(): raise ValueError('nonfinite ideal template')
        ca = lookup['CA']; native = original[ix]
        rotation = basis(ideal, lookup) @ basis(native, lookup).T
        assert abs(np.linalg.det(rotation)-1) < 1e-10
        moved = (ideal-ideal[ca]) @ rotation + native[ca]
        moved[ca] = native[ca]
        centres = [] if aa == 'G' else [['CA','N','C','CB']]
        if aa in 'IT': centres.append(['CB','CA','CG1' if aa == 'I' else 'OG1','CG2'])
        for centre in centres:
            indices = [lookup[n] for n in centre]
            a,b,c,d = native[indices]; e,f,g,h = moved[indices]
            if np.dot(np.cross(b-a,c-a),d-a)*np.dot(np.cross(f-e,g-e),h-e) <= 0:
                raise ValueError('reference stereocentre disagreement')
        result[ix] = moved
        records.append(dict(residue=residue, amino_acid=aa, atoms=len(ix),
                            checked_stereocentres=len(centres), adjacency_matches=True))
    return result, records
