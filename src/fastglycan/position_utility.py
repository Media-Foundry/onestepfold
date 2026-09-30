"""Position proposals and GT-free chemistry for a bounded hard-search diagnostic."""
import numpy as np
import torch
from .models.soft_esm import AMINO_ACIDS
from .hybrid_geometry import GeometryTopology
from .geometry_audit import pair_attribution
from .connection_audit import measure_connections
from .connection_diagnostics import describe_connection_distribution


def position_mutation_proposals(sequence, probability_gradient, *, seed):
    g=torch.as_tensor(probability_gradient).detach().cpu().double().numpy()
    if not sequence or g.shape!=(len(sequence),20) or not np.isfinite(g).all():
        raise ValueError('finite probability gradient must match sequence')
    original=np.array([AMINO_ACIDS.index(a) for a in sequence])
    delta=g-g[np.arange(len(sequence)),original,None]
    delta[np.arange(len(sequence)),original]=np.inf
    scores=delta.min(1)
    chosen=dict(gradient=int(np.argmin(scores)),random=int(np.random.default_rng(seed).integers(len(sequence))))
    arms={}
    for arm,i in chosen.items():
        arms[arm]=[dict(position=i,from_aa=sequence[i],to_aa=aa,sequence=sequence[:i]+aa+sequence[i+1:])
                   for aa in AMINO_ACIDS if aa!=sequence[i]]
    return dict(position_scores=scores.tolist(),positions=chosen,arms=arms,
                sequences=[sequence]+list(dict.fromkeys(r['sequence'] for rows in arms.values() for r in rows)))


def mutation_chemistry(atoms, reference, sequence, coordinate, calibration):
    """No experimental labels/quality invented for mutant sequences."""
    x=np.asarray(coordinate,dtype=float).reshape(-1,3);ref=np.asarray(reference,dtype=float)
    if x.shape!=ref.shape or len(x)!=len(atoms) or not np.isfinite(x).all():
        raise ValueError('invalid full-inventory coordinates')
    topology=GeometryTopology(atoms,ref)
    _,legacy=topology.terms(torch.as_tensor(x))
    lookup={(int(r),str(n)):i for i,(r,n) in enumerate(zip(atoms.res_id,atoms.atom_name))}
    anchors=np.array([[lookup[(i,a)] for a in ['N','CA','C','O']] for i in range(1,len(sequence)+1)])
    centres=[];labels=[]
    for i,aa in enumerate(sequence,1):
        if aa!='G':centres.append([lookup[(i,a)] for a in ['CA','N','C','CB']]);labels.append('CA')
        if aa in 'IT':centres.append([lookup[(i,a)] for a in ['CB','CA','CG1' if aa=='I' else 'OG1','CG2']]);labels.append(aa)
    if centres:
        a,b,c,d=np.asarray(centres).T
        rv=(np.cross(ref[b]-ref[a],ref[c]-ref[a])*(ref[d]-ref[a])).sum(1)
        if np.any(np.abs(rv)<1e-4):raise ValueError('degenerate reference chirality')
        xv=(np.cross(x[b]-x[a],x[c]-x[a])*(x[d]-x[a])).sum(1);wrong=xv*rv<=0
    else:wrong=np.zeros(0,dtype=bool)
    ca=np.asarray(labels)=='CA'; attribution=pair_attribution(atoms,x,topology.pairs.numpy())
    assert attribution['all_atoms']['severe_pairs']==legacy['severe_pairs']
    return dict(legacy_geometry=legacy,strict_checked_chirality=not bool(wrong.any()),
                ca_wrong=int(wrong[ca].sum()),side_wrong=int(wrong[~ca].sum()),
                zero_severe=legacy['severe_pairs']==0,pair_attribution=attribution,
                connection_distribution=describe_connection_distribution(measure_connections(x,anchors,sequence),sequence,calibration))


def audit_probability_pullback(q, probabilities, gp, gq):
    """Variable-space audit, not an independent certification of the full model."""
    local=q.detach().clone().requires_grad_(True);p=local.softmax(-1)
    if not torch.equal(p.detach(),probabilities.detach()):raise ValueError('probability reconstruction drift')
    pullback,=torch.autograd.grad((p*gp.detach()).sum(),local)
    manual=p.detach()*(gp.detach()-(gp.detach()*p.detach()).sum(-1,keepdim=True))
    p64=p.detach().double();g64=gp.detach().double()
    reference=p64*(g64-(g64*p64).sum(-1,keepdim=True))
    return dict(local_softmax_vjp_exact=torch.equal(pullback,gq),local_softmax_vjp_max_abs=float((pullback-gq).abs().max()),
                legacy_manual_allclose=bool(torch.allclose(gq,manual,rtol=1e-5,atol=1e-8)),
                manual_fp32_max_abs=float((manual-gq).abs().max()),
                manual_fp64_max_abs=float((reference-gq.double()).abs().max()),
                manual_fp64_relative_l2=float((reference-gq.double()).norm()/reference.norm().clamp_min(1e-30)))
