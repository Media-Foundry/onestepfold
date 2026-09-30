"""Streaming parameter-space Gram matrices for fixed weighted objective VJPs."""
import torch


def parameter_gradient_grams(vectors, parameter_names, *, chunk=1048576):
    if not vectors or not parameter_names or chunk<1 or len(set(parameter_names))!=len(parameter_names):
        raise ValueError('invalid components, parameter names, or chunk size')
    components=list(vectors)
    if any(len(v)!=len(parameter_names) for v in vectors.values()):
        raise ValueError('parameter count mismatch')
    total=torch.zeros(len(components),len(components),dtype=torch.float64);blocks=[]
    for i,name in enumerate(parameter_names):
        values=[vectors[k][i].detach().cpu().reshape(-1) for k in components]
        if any(v.shape!=values[0].shape or not torch.isfinite(v).all() for v in values):
            raise ValueError('invalid gradient shape/values')
        gram=torch.zeros_like(total)
        for start in range(0,len(values[0]),chunk):
            matrix=torch.stack([v[start:start+chunk].double() for v in values]);gram+=matrix@matrix.T
        total+=gram;blocks.append(dict(name=name,elements=len(values[0]),gram=gram.tolist()))
    return dict(components=components,gram=total.tolist(),parameters=blocks,elements=sum(x['elements'] for x in blocks))
