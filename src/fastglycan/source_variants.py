"""Deterministic source admission without model-quality selection."""


def canonical_hsp_index(identifier, prefix, size):
    """BLAST can uppercase accession-like local IDs; retain exact numeric mapping."""
    try:
        index=int(identifier[1:])
    except (ValueError,TypeError):
        raise ValueError('invalid HSP identifier') from None
    if identifier.lower()!=prefix+str(index) or not 0<=index<size:
        raise ValueError('unexpected HSP namespace or index')
    return index


def select_isolated_variants(qualified, edges):
    if len({r['group_id'] for r in qualified})!=len(qualified):
        raise ValueError('at most one qualifying source per sequence group')
    selected=[];rejected=[]
    edges={tuple(sorted(e)) for e in edges}
    for r in qualified:
        conflicts=[s['group_id'] for s in selected if r['pdb_id'].lower()==s['pdb_id'].lower()
            or set(r['accessions'])&set(s['accessions'])
            or tuple(sorted((r['group_id'],s['group_id']))) in edges]
        if conflicts:rejected.append(dict(group_id=r['group_id'],conflicts=conflicts))
        else:selected.append(r)
    return selected,rejected
