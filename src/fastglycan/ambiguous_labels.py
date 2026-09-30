"""Conservative D/E/F/Y naming alignment for a diagnostic, not coordinate repair.

The coupled naming orbits follow AlphaFold residue_atom_renaming_swaps. Choose
using distance error to observed, unambiguous atoms; never optimize the reported
lDDT threshold score directly. Unsupported or partially observed orbits stay put.
"""
import numpy as np

NAMING_ORBITS={'D':(('OD1','OD2'),),'E':(('OE1','OE2'),),
               'F':(('CD1','CD2'),('CE1','CE2')),'Y':(('CD1','CD2'),('CE1','CE2'))}


def align_ambiguous_gt(prediction,mapping,sequence):
    x=np.asarray(prediction,dtype=np.float64);y=np.asarray(mapping['coordinates'],dtype=np.float64)
    names=np.asarray(mapping['atom_names']);res=np.asarray(mapping['residue_ids']);mask=np.asarray(mapping['mask'])
    if x.shape!=y.shape or x.shape!=(len(names),3) or mask.dtype!=np.bool_ or not np.isfinite(x).all() or not np.isfinite(y[mask]).all():
        raise ValueError('invalid coordinates or observed mask')
    if len(set(np.asarray(mapping['chain_ids']).tolist()))!=1:raise ValueError('single-chain scope only')
    lookup={(int(r),str(n)):i for i,(r,n) in enumerate(zip(res,names))}
    if len(lookup)!=len(names):raise ValueError('duplicate atom identity')
    groups=[];ambiguous=set()
    for i,aa in enumerate(sequence,1):
        swaps=NAMING_ORBITS.get(aa,())
        if not swaps:continue
        ids=[lookup.get((i,n)) for pair in swaps for n in pair]
        if any(k is None for k in ids):raise ValueError('missing native inventory atom')
        ambiguous.update(ids);groups.append((i,aa,np.array(ids,dtype=np.int64)))
    anchors=np.array([i for i in np.flatnonzero(mask) if i not in ambiguous],dtype=np.int64)
    perm=np.arange(len(x));records=[]
    for residue,aa,ids in groups:
        record=dict(residue=residue,aa=aa,observed=bool(mask[ids].all()),swapped=False)
        if not mask[ids].all():records.append(record);continue
        stable=anchors[res[anchors]!=residue]
        distances=np.linalg.norm(y[ids,None,:]-y[stable][None,:,:],axis=-1)
        stable=stable[(distances<15.).any(axis=0)]
        record['anchors']=len(stable)
        if not len(stable):records.append(record);continue
        alternative=ids.reshape(-1,2)[:,::-1].reshape(-1)
        measured=np.linalg.norm(x[ids,None,:]-x[stable][None,:,:],axis=-1)
        old=np.linalg.norm(y[ids,None,:]-y[stable][None,:,:],axis=-1)
        new=np.linalg.norm(y[alternative,None,:]-y[stable][None,:,:],axis=-1)
        old_error=float(np.abs(measured-old).mean());new_error=float(np.abs(measured-new).mean())
        record.update(original_distance_mae=old_error,alternative_distance_mae=new_error)
        if new_error<old_error:perm[ids]=alternative;record['swapped']=True
        records.append(record)
    if not np.array_equal(mask,mask[perm]):raise AssertionError('diagnostic changed observed support')
    if not np.array_equal(perm[~np.isin(np.arange(len(x)),list(ambiguous))],np.flatnonzero(~np.isin(np.arange(len(x)),list(ambiguous)))):
        raise AssertionError('changed a nonambiguous atom')
    return dict(permutation=perm,coordinates=y[perm],records=records)
