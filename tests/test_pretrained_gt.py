import pytest
import torch
from torch import nn

from fastglycan.pretrained_gt import configure_gt_optimizer, gt_epoch_batches


def test_epoch_coverage_repeatability_and_reshuffle():
    rows=[{'group_id':str(i),'sequence':'A'*(32+i%225)} for i in range(132)]
    batches=gt_epoch_batches(rows,1)
    assert batches==gt_epoch_batches(list(reversed(rows)),1)
    assert len(batches)==33 and all(len(b)==4 for b in batches)
    flat=[r['group_id'] for b in batches for r in b]
    assert len(set(flat))==len(rows) and set(flat)=={r['group_id'] for r in rows}
    assert batches!=gt_epoch_batches(rows,2)
    with pytest.raises(ValueError):gt_epoch_batches(rows[:-1],1)
    with pytest.raises(ValueError):gt_epoch_batches(rows[:-1]+[rows[0]],1)


def test_optimizer_updates_both_paths_and_freezes_heads():
    model=nn.Module();model.core=nn.Module();c=model.core
    c.input_embedder=nn.Module();c.input_embedder.linear_esm=nn.Linear(3,4)
    c.body=nn.Linear(4,2);c.confidence_head=nn.Linear(2,1);c.distogram_head=nn.Linear(2,1)
    optimizer=configure_gt_optimizer(model)
    before={n:p.detach().clone() for n,p in model.named_parameters()}
    c.body(c.input_embedder.linear_esm(torch.ones(2,3))).square().sum().backward()
    optimizer.step()
    for n,p in model.named_parameters():
        if 'head' in n:assert not p.requires_grad and torch.equal(p,before[n])
        else:assert p.requires_grad and not torch.equal(p,before[n])
    registered=[id(p) for group in optimizer.param_groups for p in group['params']]
    assert len(registered)==len(set(registered))
    assert set(registered)=={id(p) for p in model.parameters() if p.requires_grad}
