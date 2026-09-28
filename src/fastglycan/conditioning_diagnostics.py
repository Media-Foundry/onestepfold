"""Read-only decomposition for the locked fixed-chart derivative diagnostics."""
import torch
from .sequence_gate_metrics import contact_objective


def weighted_geometry_objectives(coordinates, ca_indices, topology):
    ca=coordinates[0,ca_indices]
    distance=torch.cdist(ca,ca)
    index=torch.arange(len(ca),device=ca.device)
    separation=(index[:,None]-index[None,:]).abs()
    contact=-torch.sigmoid((8-distance)/1.5)[separation>8].double().mean()
    ca_clash=torch.relu(3-distance[separation>1]).square().double().mean()
    ca_chain=.1*(torch.linalg.vector_norm(ca[1:]-ca[:-1],dim=-1)-3.8).square().double().mean()
    terms,_=topology.terms(coordinates)
    result=dict(contact=contact,ca_clash=ca_clash,ca_chain=ca_chain,
                bond=terms['bond'],peptide=2*terms['peptide'],clash=terms['clash'],
                chirality=.2*terms['chirality'])
    # Preserve the original expression/accumulation order for exact replay.
    result['old']=contact_objective(coordinates,ca_indices)[0]
    result['new']=result['old']+terms['bond']+2*terms['peptide']+terms['clash']+.2*terms['chirality']
    return result


def directional_comparison(analytic, linear, nonlinear):
    def passed(value):return abs(value-analytic)<=1e-6+.05*max(abs(value),abs(analytic))
    return dict(analytic=analytic,linearized_coordinate_fd=linear,objective_fd=nonlinear,
                linear_pass=passed(linear),objective_pass=passed(nonlinear),
                curvature_remainder=nonlinear-linear)
