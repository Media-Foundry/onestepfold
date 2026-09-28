"""Fixed-graph upstream-source interventions for diagnosis, not deployment."""
from contextlib import contextmanager
import inspect
import numpy as np
import torch
from .models.soft_sequence_chart import REFERENCE_FEATURES


def probability_interpolation(onehot, alpha):
    if not 0 <= alpha < .95:raise ValueError('alpha must retain the native argmax')
    if onehot.ndim!=2 or onehot.shape[1]!=20:raise ValueError('expected Lx20 one-hot')
    return (1-alpha)*onehot+(alpha/19)*(1-onehot)


def mix_reference(bank, probabilities, token_indices):
    p=probabilities[token_indices]
    return {name:(value*p.reshape(*p.shape,*([1]*(value.ndim-2)))).sum(1)
            for name,value in bank.items()}


def source_intervention(native, soft_reference, soft_restype, hard_esm, soft_esm, sources):
    """Only selected source fields change; pair features must be regenerated next."""
    if set(sources)-set('ERC'):raise ValueError('unknown source')
    f=dict(native)
    f['esm_token_embedding']=soft_esm if 'E' in sources else hard_esm
    if 'R' in sources:
        f['restype']=soft_restype;f['profile']=soft_restype
    if 'C' in sources:
        for name in REFERENCE_FEATURES:f[name]=soft_reference[name]
    for name in ('d_lm','v_lm','pad_info'):f.pop(name,None)
    return f


def tensor_delta(value, baseline):
    d=(value.double()-baseline.double());rms=float(d.square().mean().sqrt())
    scale=float(baseline.double().square().mean().sqrt())
    return dict(rms=rms,max_abs=float(d.abs().max()),relative_rms=rms/scale if scale else None)


def aligned_rmsd(first, second):
    p=np.asarray(first,dtype=float);q=np.asarray(second,dtype=float)
    p=p-p.mean(0);q=q-q.mean(0);u,_,vt=np.linalg.svd(p.T@q)
    sign=np.eye(3);sign[-1,-1]=np.linalg.det(u@vt)
    return float(np.sqrt(np.mean(np.sum((p@u@sign@vt-q)**2,axis=-1))))


@contextmanager
def audit_reference_caches(model, features):
    """Assert both real cache builders read the currently intervened chemistry."""
    objects={'input_atom_encoder':model.input_embedder.atom_attention_encoder,
             'diffusion_atom_encoder':model.diffusion_module.atom_attention_encoder}
    originals={name:obj.prepare_cache for name,obj in objects.items()}
    records=[]
    def wrap(label,original):
        signature=inspect.signature(original)
        def checked(*args,**kwargs):
            bound=signature.bind_partial(*args,**kwargs).arguments
            names=(*REFERENCE_FEATURES,'d_lm','v_lm')
            for name in names:
                if name not in bound:raise RuntimeError('cache audit missing '+name)
                if not torch.equal(bound[name],features[name]):raise RuntimeError('stale reference cache input '+label+':'+name)
            records.append(dict(encoder=label,checked_fields=list(names)))
            return original(*args,**kwargs)
        return checked
    try:
        for name,obj in objects.items():obj.prepare_cache=wrap(name,originals[name])
        yield records
        for name in objects:
            if not any(r['encoder']==name for r in records):raise RuntimeError('cache builder was bypassed: '+name)
    finally:
        for name,obj in objects.items():obj.prepare_cache=originals[name]
