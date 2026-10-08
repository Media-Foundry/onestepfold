import torch
import pytest
from fastglycan.paired_distributed import atomic_checkpoint,paired_local_index


def test_pair_mean_before_clip_and_adam_matches_serial():
    torch.manual_seed(11)
    a=torch.nn.Linear(5,3);b=torch.nn.Linear(5,3);b.load_state_dict(a.state_dict())
    oa=torch.optim.AdamW(a.parameters(),lr=1e-4);ob=torch.optim.AdamW(b.parameters(),lr=1e-4)
    x=torch.randn(2,5);y=torch.randn(2,3)
    grads=[]
    for i in range(2):
        ((a(x[i])-y[i]).square().mean()/2).backward()
        b.zero_grad();(b(x[i])-y[i]).square().mean().backward()
        grads.append([p.grad.clone() for p in b.parameters()])
    for j,p in enumerate(b.parameters()):p.grad=(grads[0][j]+grads[1][j])/2
    for pa,pb in zip(a.parameters(),b.parameters()):torch.testing.assert_close(pa.grad,pb.grad,rtol=0,atol=0)
    torch.nn.utils.clip_grad_norm_(a.parameters(),1.);torch.nn.utils.clip_grad_norm_(b.parameters(),1.)
    oa.step();ob.step()
    for pa,pb in zip(a.parameters(),b.parameters()):torch.testing.assert_close(pa,pb,rtol=0,atol=0)


def test_atomic_checkpoint_and_locked_global_batch(tmp_path):
    p=tmp_path/'state.pt';atomic_checkpoint(p,{'step':9,'x':torch.ones(2)})
    assert torch.load(p,weights_only=True)['step']==9
    atomic_checkpoint(p,{'step':10});assert torch.load(p,weights_only=True)['step']==10
    assert list(tmp_path.iterdir())==[p]
    assert [paired_local_index(i,2) for i in range(2)]==[0,1]
    with pytest.raises(ValueError):paired_local_index(2,3)
