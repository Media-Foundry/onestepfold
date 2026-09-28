"""Full fixed-cotangent VJP comparison, including explicit identity subtraction."""
import math
import torch


def vector_metrics(actual,reference,low_norm=1e-10):
    a=actual.detach().double().flatten();b=reference.detach().double().flatten()
    na=float(a.norm());nb=float(b.norm());error=float((a-b).norm())
    return dict(elements=a.numel(),actual_norm=na,reference_norm=nb,absolute_l2_error=error,
                max_absolute_error=float((a-b).abs().max()) if a.numel() else 0.,
                relative_l2_error=error/nb if nb>0 else None,
                cosine=float(torch.dot(a,b)/(na*nb)) if na>0 and nb>0 else None,
                low_reference_norm=nb<low_norm,zero_reference=nb==0)


def compare_fields(actual,reference,identity=None):
    if set(actual)!=set(reference):raise ValueError('field mismatch')
    fields={k:vector_metrics(actual[k],reference[k]) for k in actual}
    total=vector_metrics(torch.cat([x.detach().double().flatten() for x in actual.values()]),torch.cat([reference[k].detach().double().flatten() for k in actual]))
    result=dict(total=total,fields=fields,low_norm_annotation_threshold=1e-10)
    if identity is not None:
        a={k:actual[k].double()-identity.get(k,torch.zeros_like(actual[k])).double() for k in actual}
        b={k:reference[k].double()-identity.get(k,torch.zeros_like(reference[k])).double() for k in reference}
        result['without_explicit_identity']=compare_fields(a,b)
        result['identity_fields']=list(identity)
    return result
