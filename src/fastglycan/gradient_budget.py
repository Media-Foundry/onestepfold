"""Signed component-gradient diagnostics; these are not causal error fractions."""
import torch


def component_gradient_statistics(gradients,names,weights):
    g=torch.as_tensor(gradients).detach().cpu().double()
    required=['coordinate','smooth_lddt','bond','chirality','clash','teacher']
    if list(names)!=required or g.ndim!=2 or len(g)!=6 or not torch.isfinite(g).all():
        raise ValueError('invalid component gradients/order')
    scale=torch.tensor([weights[n] for n in names],dtype=torch.float64)
    if not torch.isfinite(scale).all() or (scale<0).any():raise ValueError('invalid weights')
    gram=g@g.T;weighted=g*scale[:,None];weighted_gram=weighted@weighted.T
    norms=gram.diagonal().clamp_min(0).sqrt();wnorms=weighted_gram.diagonal().clamp_min(0).sqrt()
    vectors=dict(structure=weighted[:3].sum(0),chemistry=weighted[3:5].sum(0),
        gt=weighted[:5].sum(0),teacher=weighted[5],gt_s2=weighted.sum(0))
    group_norms={n:float(v.norm()) for n,v in vectors.items()}
    cosines={}
    for a,b in [('structure','chemistry'),('teacher','gt'),('gt','gt_s2')]:
        denom=group_norms[a]*group_norms[b]
        cosines[a+'_vs_'+b]=float(torch.dot(vectors[a],vectors[b])/denom) if denom>0 else None
    pairwise=[]
    for i in range(6):
        pairwise.append([float(gram[i,j]/(norms[i]*norms[j])) if norms[i]*norms[j]>0 else None for j in range(6)])
    denominator=group_norms['gt']**2
    projection={names[i]:float(torch.dot(weighted[i],vectors['gt'])/denominator) if denominator>0 else None for i in range(5)}
    return dict(raw_gram=gram.tolist(),weighted_gram=weighted_gram.tolist(),
        raw_norm=dict(zip(names,norms.tolist())),weighted_norm=dict(zip(names,wnorms.tolist())),
        pairwise_cosine=pairwise,group_norms=group_norms,group_cosines=cosines,
        teacher_to_gt_norm_ratio=group_norms['teacher']/group_norms['gt'] if group_norms['gt'] else None,
        chemistry_to_structure_norm_ratio=group_norms['chemistry']/group_norms['structure'] if group_norms['structure'] else None,
        signed_projection_onto_gt=projection,
        interpretation='Euclidean parameter-space diagnostics; signed projections may exceed one or be negative, not causal percentages')
