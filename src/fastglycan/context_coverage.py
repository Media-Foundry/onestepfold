"""Read-only diagnostics of context replication and categorical label shortcuts."""
from collections import Counter
import hashlib
import numpy as np


def aa_table_projection(cases, alphabet):
    """Least-squares AA-pair table on TRAIN old-noise means, not a test predictor.

    Uniform case/candidate weights match the previous global-scale MSE. Within a
    source-AA group candidate columns align after deleting the WT column.
    """
    if not cases:
        raise ValueError('empty training cases')
    source = np.array([c['wt'] for c in cases])
    y = np.array([np.delete(np.asarray(c['target_delta'])[:2].mean(0), c['wt']) for c in cases])
    if y.shape != (len(cases), len(alphabet)-1) or not np.isfinite(y).all():
        raise ValueError('invalid task labels')
    fitted = np.empty_like(y)
    counts = Counter(source.tolist())
    for aa in counts:
        group = source == aa
        fitted[group] = y[group].mean(0)
    energy = np.square(y).sum(axis=1)
    error = np.square(y-fitted).sum(axis=1)
    total = float(energy.sum())
    explained = float(np.square(fitted).sum())
    assert np.isclose(total, explained+error.sum(), rtol=1e-12, atol=1e-12)
    per_site = []
    for index, c in enumerate(cases):
        per_site.append(dict(parent_index=c['parent_index'], position=c['position'],
                             source_aa=alphabet[c['wt']], same_source_contexts=counts[c['wt']],
                             label_energy=float(energy[index]),
                             energy_fraction=float(energy[index]/total) if total else None,
                             table_error_energy=float(error[index]),
                             table_mse=float(error[index]/y.shape[1]),
                             target_old=y[index].tolist(), fitted_table=fitted[index].tolist()))
    return dict(contexts=len(cases), source_types=len(counts),
                source_counts={alphabet[k]:v for k,v in sorted(counts.items())},
                singleton_contexts=sum(counts[x] == 1 for x in source),
                singleton_energy_fraction=float(sum(energy[i] for i,x in enumerate(source) if counts[x]==1)/total) if total else None,
                label_squared_energy=total, table_squared_error=float(error.sum()),
                irreducible_global_normalized_mse=float(error.sum()/total) if total else None,
                residual_squared_mean=float(error.sum()/y.size),
                pythagorean_error=float(abs(total-explained-error.sum())), sites=per_site)


def repeated_source_inventory(contexts, alphabet):
    """Keep the common held panel intact; never count its sites as available TRAIN."""
    output=[]
    for aa in alphabet:
        matching=[c for c in contexts if c['source_aa']==aa]
        allowed=[c for c in matching if c['eligible_train'] and not c['common_holdout']]
        held=[c for c in matching if c['common_holdout']]
        output.append(dict(aa=aa, archive_sites=len(matching),
                           archive_proteins=len({c['parent_index'] for c in matching}),
                           available_train_sites=len(allowed),
                           available_train_components=len({c['component'] for c in allowed}),
                           held_sites=len(held), held_components=len({c['component'] for c in held})))
    return output


def context_selection_key(identity, tag):
    return hashlib.sha256(f'context-replication-v1:20261004:{tag}:{identity}'.encode()).hexdigest()


def select_repeated_contexts(candidates, sources='ADLT'):
    """Sequence/GT-only candidate manifest: 32 TRAIN + 8 sealed candidates.

    Candidates must already be isolated from all previous response parents and
    have an observed, finite CA at each selectable source site. No task labels.
    """
    selected=[];used=set()
    plan=[(80,112,10,3),(113,150,11,3),(151,192,11,2)]
    for low,high,nt,nv in plan:
        available=sorted([c for c in candidates if low<=len(c['sequence'])<=high],
                         key=lambda c:context_selection_key(c['group_id'],'parent'))
        group=[]
        for c in available:
            if c['component'] in used or not all(c['eligible_positions'].get(a) for a in sources):
                continue
            used.add(c['component']);group.append(c)
            if len(group)==nt+nv:break
        if len(group)!=nt+nv:
            raise ValueError(f'insufficient independent candidates in {low}-{high}: {len(group)}')
        for j,c in enumerate(group):
            sites={a:min(c['eligible_positions'][a],key=lambda p:context_selection_key(f'{c["group_id"]}:{p}','site')) for a in sources}
            selected.append(dict(c, role='confirmation_candidate' if j<nv else 'train',
                                 sites=sites, length_stratum=[low,high]))
    tiers={str(n):[] for n in (8,16,32)}
    for n,counts in [(8,[2,3,3]),(16,[5,6,5]),(32,[10,11,11])]:
        for (lo,hi,_,_),count in zip(plan,counts):
            group=[r for r in selected if r['role']=='train' and r['length_stratum']==[lo,hi]]
            tiers[str(n)].extend(r['group_id'] for r in group[:count])
    assert set(tiers['8'])<=set(tiers['16'])<=set(tiers['32'])
    assert len({r['component'] for r in selected})==40
    return dict(rows=selected, sources=sources, nested_train_tiers=tiers,
                train_parents=32, confirmation_candidate_parents=8,
                training_sites=128, confirmation_candidate_sites=32,
                teachers_generated=False, training_started=False)
