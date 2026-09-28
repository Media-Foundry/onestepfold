import torch
from fastglycan.conditioning_diagnostics import weighted_geometry_objectives,directional_comparison
from fastglycan.sequence_gate_metrics import contact_objective


class Topology:
    def terms(self,x):
        return dict(bond=x.square().mean(),peptide=x.sin().square().mean(),
                    clash=torch.relu(x-.2).square().mean(),chirality=(x[...,0]+1).square().mean()),{}


def test_objective_decomposition_preserves_value_and_coordinate_gradient():
    generator=torch.Generator().manual_seed(91)
    x=torch.randn((1,12,3),generator=generator,dtype=torch.float64,requires_grad=True)
    ca=torch.arange(12);topology=Topology();values=weighted_geometry_objectives(x,ca,topology)
    terms,_=topology.terms(x);old=contact_objective(x,ca)[0]
    new=old+terms['bond']+2*terms['peptide']+terms['clash']+.2*terms['chirality']
    torch.testing.assert_close(values['old'],old,rtol=0,atol=0)
    torch.testing.assert_close(values['new'],new,rtol=0,atol=0)
    decomposed=sum(v for k,v in values.items() if k not in ('old','new'))
    torch.testing.assert_close(decomposed,new)
    grad,=torch.autograd.grad(new,x,retain_graph=True)
    split,=torch.autograd.grad(decomposed,x)
    torch.testing.assert_close(grad,split)


def test_linearized_fd_and_nonlinear_fd_are_separate_gates():
    result=directional_comparison(.16,.159,.085)
    assert result['linear_pass'] and not result['objective_pass']
    assert abs(result['curvature_remainder']+.074)<1e-12
