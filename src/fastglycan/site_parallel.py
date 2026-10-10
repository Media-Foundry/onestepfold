"""Ordered site-parallel gradients; the model's candidate batch is unchanged.

Gloo communicates CPU FP64 site gradients. Rank zero sums in the same site order
as the serial trainer, clips once, steps once and broadcasts parameters. This
prototype is not wired into an existing locked training run.
"""
import math

import torch
import torch.distributed as dist

from fastglycan.anchor_training import AnchoredFullBatchTrainer
from fastglycan.stage_fullbatch import parameter_digest


def local_anchor_gradients(model, sites, fetch, reference_pairs, alphabet, scales,
                           reference_bases, reference_boundaries, indices):
    """Execute complete sites, including the shared WT reference pullback."""
    records=[]
    digest=parameter_digest(list(model.parameters()))
    for index in indices:
        trainer=AnchoredFullBatchTrainer(model,[sites[index]],fetch,reference_pairs,
            alphabet,scales,reference_bases,reference_boundaries)
        result=trainer.objective()
        records.append(dict(index=index,site=sites[index]['site_key'],row=result['sites'][0],
            gradient=trainer.last_gradient,counts=dict(trainer.counts),parameter_sha256=digest))
    if parameter_digest(list(model.parameters()))!=digest:
        raise RuntimeError('parameters changed while computing site gradients')
    return records


def ordered_site_mean(records, site_keys, parameter_count):
    """Reject missing/duplicated sites and reduce in canonical order, not rank order."""
    if not site_keys or len(set(site_keys))!=len(site_keys):
        raise ValueError('distinct nonempty site list required')
    ordered={}
    for record in records:
        index=record['index']
        if not isinstance(index,int) or index not in range(len(site_keys)) or index in ordered:
            raise ValueError('missing, duplicated or invalid site index')
        if record['site']!=site_keys[index] or record['row']['site']!=site_keys[index]:
            raise ValueError('site identity mismatch')
        gradient=record['gradient']
        if (gradient.device.type!='cpu' or gradient.dtype!=torch.float64 or gradient.ndim!=1
                or gradient.numel()!=parameter_count or not torch.isfinite(gradient).all()):
            raise ValueError('finite CPU FP64 full-parameter gradient required')
        row=record['row']
        if (not all(math.isfinite(row[k]) for k in ('raw','common','centered'))
                or not math.isclose(row['raw'],row['common']+row['centered'],rel_tol=1e-10,abs_tol=1e-10)):
            raise ValueError('invalid objective decomposition')
        counts=record['counts']
        if (counts['gradient_passes']!=1 or counts['reference_forwards']!=1
                or counts['reference_backwards']!=1 or counts['forwards']!=counts['backwards']
                or counts['forwards']<=0):
            raise ValueError('incomplete site/reference backward')
        ordered[index]=record
    if len(ordered)!=len(site_keys):raise ValueError('missing site gradient')
    total=None;rows=[]
    for index in range(len(site_keys)):
        row=ordered[index]
        total=row['gradient'].clone() if total is None else total+row['gradient']
        rows.append(row['row'])
    gradient=total/len(site_keys)
    # Keep the serial NumPy averaging rule for diagnostics as well.
    import numpy as np
    objective={key:float(np.mean([r[key] for r in rows])) for key in ('raw','common','centered')}
    counts={key:sum(r['counts'][key] for r in ordered.values())
            for key in ('forwards','backwards','reference_forwards','reference_backwards')}
    counts['gradient_passes']=1
    return gradient,dict(**objective,sites=rows,counts=counts)


def synchronized_anchor_step(model, local_records, site_keys, optimizer=None,
                             *, local_error=None, max_norm=1.):
    """One global update with a root optimizer and identical parameter replicas.

    All ranks must call even when their local calculation fails; pass its error
    string so peers also stop. Process death remains a process-group timeout.
    No automatic retry or continuation is provided. Only rank zero owns AdamW
    state; every reference graph/cache must be rebuilt after this function.
    """
    if not dist.is_initialized() or dist.get_backend()!='gloo':
        raise ValueError('initialized Gloo default process group required')
    rank,world=dist.get_rank(),dist.get_world_size()
    if not 1<=world<=6:raise ValueError('prototype supports one to six ranks')
    parameters=list(model.parameters())
    schema=[(name,tuple(p.shape),str(p.dtype)) for name,p in model.named_parameters()]
    payload=dict(records=local_records,error=local_error,schema=schema,site_keys=list(site_keys),
                 parameter_sha256=parameter_digest(parameters))
    gathered=[None]*world if rank==0 else None
    dist.gather_object(payload,gathered,dst=0)
    status=[None];gradient=None
    if rank==0:
        try:
            if optimizer is None:raise ValueError('rank zero optimizer required')
            for part in gathered:
                if part['error'] is not None:raise RuntimeError(f"worker failed: {part['error']}")
                if part['schema']!=schema or part['parameter_sha256']!=payload['parameter_sha256']:
                    raise ValueError('model replicas differ before update')
                if part['site_keys']!=payload['site_keys']:
                    raise ValueError('site order differs between workers')
            records=[r for part in gathered for r in part['records']]
            if any(r['parameter_sha256']!=payload['parameter_sha256'] for r in records):
                raise ValueError('stale site gradients from a different parameter version')
            gradient,summary=ordered_site_mean(records,site_keys,sum(p.numel() for p in parameters))
            offset=0
            for parameter in parameters:
                size=parameter.numel()
                parameter.grad=gradient[offset:offset+size].reshape(parameter.shape).to(parameter).clone()
                offset+=size
            norm=torch.nn.utils.clip_grad_norm_(parameters,max_norm,error_if_nonfinite=True)
            optimizer.step()
            values=torch.cat([p.detach().cpu().double().flatten() for p in parameters])
            if not torch.isfinite(values).all():raise FloatingPointError('nonfinite optimizer output')
            status[0]=dict(complete=True,summary=summary,gradient_norm=float(norm),
                clipped=bool(norm>max_norm),parameter_sha256=parameter_digest(parameters),
                world_size=world,site_gradient_bytes=gradient.numel()*8*len(site_keys))
        except Exception as error:
            status[0]=dict(complete=False,error=repr(error))
    dist.broadcast_object_list(status,src=0)
    if not status[0]['complete']:
        raise RuntimeError('site-parallel step failed: '+status[0]['error'])
    if rank!=0:values=torch.empty(sum(p.numel() for p in parameters),dtype=torch.float64)
    dist.broadcast(values,src=0)
    with torch.no_grad():
        offset=0
        for parameter in parameters:
            size=parameter.numel()
            parameter.copy_(values[offset:offset+size].reshape(parameter.shape).to(parameter))
            offset+=size
    digests=[None]*world
    dist.all_gather_object(digests,parameter_digest(parameters))
    if set(digests)!={status[0]['parameter_sha256']}:
        raise RuntimeError('model replicas differ after update')
    # The large vector is returned only to root for explicit numerical auditing.
    return dict(**status[0],gradient=gradient if rank==0 else None)
