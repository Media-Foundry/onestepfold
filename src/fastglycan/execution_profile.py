"""Read-only timing and tensor inventory helpers for the native C4 audit."""
from contextlib import contextmanager
import hashlib
import json
import time
import numpy as np
import torch


def leaf_inventory(value, path=''):
    """Compare exact observed values; equality alone does not prove cache safety."""
    if isinstance(value,dict):
        out={}
        for key in sorted(value,key=str):out.update(leaf_inventory(value[key],f'{path}/{key}'))
        return out
    if isinstance(value,(list,tuple)):
        out={}
        for i,x in enumerate(value):out.update(leaf_inventory(x,f'{path}/{i}'))
        return out
    if isinstance(value,torch.Tensor):
        x=value.detach().contiguous().cpu();data=x.view(torch.uint8).numpy().tobytes() if x.ndim else x.reshape(1).view(torch.uint8).numpy().tobytes()
        return {path:dict(kind='tensor',shape=list(x.shape),dtype=str(x.dtype),bytes=x.numel()*x.element_size(),sha256=hashlib.sha256(data).hexdigest())}
    if isinstance(value,np.ndarray):
        data=np.ascontiguousarray(value).tobytes();return {path:dict(kind='ndarray',shape=list(value.shape),dtype=str(value.dtype),bytes=value.nbytes,sha256=hashlib.sha256(data).hexdigest())}
    if value is None or isinstance(value,(str,bool,int,float)):
        return {path:dict(kind=type(value).__name__,value=value)}
    return {path:dict(kind='opaque',type=type(value).__name__,comparable=False)}


def compare_inventory(a,b):
    keys=set(a)|set(b);same=[];changed=[];unknown=[]
    for k in sorted(keys):
        if k not in a or k not in b:changed.append(k)
        elif a[k].get('comparable') is False or b[k].get('comparable') is False:unknown.append(k)
        elif a[k]==b[k]:same.append(k)
        else:changed.append(k)
    return dict(equal_observed=same,changed=changed,unknown=unknown)


class StageRecorder:
    def __init__(self,synchronize=None,annotate=False):
        self.synchronize=synchronize;self.annotate=annotate;self.seconds={}

    @contextmanager
    def stage(self,name):
        if self.synchronize:self.synchronize()
        marker=torch.profiler.record_function(name) if self.annotate else None
        if marker:marker.__enter__()
        started=time.perf_counter()
        try:yield
        finally:
            if self.synchronize:self.synchronize()
            self.seconds[name]=self.seconds.get(name,0.)+time.perf_counter()-started
            if marker:marker.__exit__(None,None,None)


def operator_table(profiler):
    rows=[]
    for e in profiler.key_averages():
        rows.append(dict(name=e.key,calls=e.count,cpu_total_us=e.cpu_time_total,self_cpu_us=e.self_cpu_time_total,
            device_total_us=getattr(e,'device_time_total',None),self_device_us=getattr(e,'self_device_time_total',None),
            self_cpu_memory_bytes=e.self_cpu_memory_usage,self_device_memory_bytes=getattr(e,'self_device_memory_usage',None)))
    return sorted(rows,key=lambda x:x['self_cpu_us'],reverse=True)
