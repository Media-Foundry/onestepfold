import copy
import numpy as np
import torch
from fastglycan.adapter_supervision import build_adapter_supervision, adapter_loss_parts


def test_adapter_mask_and_clashes():
    reference=np.array([[-1,.7,0],[0,0,0],[1,.7,0],[1.7,1.7,0],[0,0,1],
                        [2,.7,0],[3,0,0],[4,.7,0],[4.7,1.7,0],[3,0,1]],dtype=float)
    names=np.array(['N','CA','C','O','CB']*2);residues=np.repeat([1,2],5)
    mask=np.ones(10,dtype=bool);mask[-1]=False
    mapping=dict(coordinates=reference.copy(),mask=mask,reference=reference,atom_names=names,residue_ids=residues)
    bonds=np.array([[0,1],[1,2],[2,3],[1,4],[2,5],[5,6],[6,7],[7,8],[6,9]])
    supervision=build_adapter_supervision(mapping,bonds,'AA')
    poisoned=copy.deepcopy(mapping);poisoned['coordinates'][~mask]=np.nan
    other=build_adapter_supervision(poisoned,bonds,'AA')
    x=torch.tensor(reference,dtype=torch.float64);x[-1]=torch.tensor([-1,.7,.4]);x.requires_grad_()
    parts=adapter_loss_parts(x,supervision);repeated=adapter_loss_parts(x,other)
    for name in parts:torch.testing.assert_close(parts[name],repeated[name],atol=1e-12,rtol=0)
    # Full dense independent geometric penalty, including the GT-missing atom.
    xyz=x.detach().numpy();depths=[]
    for i in range(10):
        for j in range(i+1,10):
            if i*10+j not in set(supervision['excluded']):
                depths.append(float(supervision['radii'][i]+supervision['radii'][j])-np.linalg.norm(xyz[i]-xyz[j]))
    depth=np.array(depths);k=min(16,len(depth))
    dense=np.maximum(depth-1.5,0).dot(np.maximum(depth-1.5,0))/10
    dense+=(np.maximum(np.sort(depth)[-k:]-1.9,0)/.1).dot(np.maximum(np.sort(depth)[-k:]-1.9,0)/.1)/k
    np.testing.assert_allclose(float(parts['clash'].detach()),dense,rtol=1e-12,atol=1e-12)
    gt=parts['coordinate']/100+parts['smooth_lddt']+10*parts['bond']
    gt_gradient,=torch.autograd.grad(gt,x,retain_graph=True)
    assert torch.count_nonzero(gt_gradient[-1])==0
    chem_gradient,=torch.autograd.grad(parts['clash'],x,retain_graph=True)
    assert chem_gradient[-1].norm()>0 and torch.isfinite(chem_gradient).all()
    rotation=torch.tensor([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]],dtype=torch.float64)
    transformed=adapter_loss_parts(x@rotation+7.,supervision)
    for name in parts:torch.testing.assert_close(parts[name],transformed[name],atol=1e-10,rtol=1e-10)
    teacher=torch.tensor(reference,dtype=torch.float64)
    with_teacher=adapter_loss_parts(x,supervision,teacher)
    gradient,=torch.autograd.grad(sum(with_teacher.values()),x)
    assert torch.isfinite(gradient).all()
