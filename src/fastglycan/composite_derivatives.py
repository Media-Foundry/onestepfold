"""Native-trajectory true forward-mode helpers; no secant substitution."""
from contextlib import contextmanager
import torch


@contextmanager
def without_checkpoint_wrappers(model):
    saved=[]
    for m in model.modules():
        if hasattr(m,'blocks_per_ckpt'):
            saved.append((m,m.blocks_per_ckpt));m.blocks_per_ckpt=None
    import fastglycan.models.soft_sequence_chart as chart
    original=chart.soft_esm2
    def uncheckpointed(esm,alphabet,p):return original(esm,alphabet,p,checkpoint_layers=False)
    chart.soft_esm2=uncheckpointed
    try:yield
    finally:
        chart.soft_esm2=original
        for m,value in saved:m.blocks_per_ckpt=value


def dictionary_jvp(function,point,tangent):
    names=list(point);output_names=[]
    def wrapped(*values):
        result=function(dict(zip(names,values)));output_names[:]=list(result)
        return tuple(result.values())
    primal,derivative=torch.func.jvp(wrapped,tuple(point[k] for k in names),tuple(tangent[k] for k in names))
    return dict(zip(output_names,primal)),dict(zip(output_names,derivative))


def consistency(a,b,rtol=.05,atol=1e-6):
    error=abs(a-b)
    return dict(left=a,right=b,absolute_error=error,relative_error=error/max(abs(a),abs(b),1e-30),tolerance=atol+rtol*max(abs(a),abs(b)),passed=error<=atol+rtol*max(abs(a),abs(b)))
