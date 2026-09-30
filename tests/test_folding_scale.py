import copy
import pytest
import torch
from fastglycan.folding_scale import PARENT_SHA256, folding_scale_lr, load_folding_scale_terminal


def test_schedule_has_locked_warmup_and_terminal_without_extra_updates():
    setting=dict(peak=1e-5,warmup_updates=64,terminal=1e-6)
    assert folding_scale_lr(1,setting,2048)==1e-5/64
    assert folding_scale_lr(64,setting,2048)==1e-5
    assert folding_scale_lr(2048,setting,2048)==1e-6
    assert all(folding_scale_lr(i,setting,2048)>=folding_scale_lr(i+1,setting,2048) for i in range(64,2048))
    for i in (0,2049):
        with pytest.raises(ValueError):folding_scale_lr(i,setting,2048)


def test_terminal_rejects_invalid_payload_before_any_tensor_changes():
    model=torch.nn.Module();model.diffusion_module=torch.nn.Linear(3,2);model.trunk=torch.nn.Linear(3,3)
    model.requires_grad_(False)
    original={n:p.clone() for n,p in model.named_parameters()}
    names=[n for n in original if n.startswith('diffusion_module.')]
    good=dict(schema='folding_scale_continuation_v1',arm='expanded',update=2048,exposures=8192,
        parent_sha256=PARENT_SHA256,lock_sha256='locked',trained={n:torch.ones_like(original[n]) for n in names})
    variants=[]
    for field,value in [('update',512),('parent_sha256','other'),('lock_sha256','other'),('arm','train128')]:
        bad=copy.deepcopy(good);bad[field]=value;variants.append(bad)
    bad=copy.deepcopy(good);bad['trained'][names[-1]].fill_(float('nan'));variants.append(bad)
    bad=copy.deepcopy(good);bad['trained']['trunk.weight']=torch.ones_like(original['trunk.weight']);variants.append(bad)
    for bad in variants:
        with pytest.raises(ValueError):load_folding_scale_terminal(model,bad,arm='expanded',expected_names=names,lock_sha256='locked')
        assert all(torch.equal(p,original[n]) for n,p in model.named_parameters())
    load_folding_scale_terminal(model,good,arm='expanded',expected_names=names,lock_sha256='locked')
    assert all(torch.equal(p,good['trained'][n] if n in names else original[n]) for n,p in model.named_parameters())
