from collections import Counter
from types import SimpleNamespace
import pytest
import torch

from fastglycan.noise_lora import NoiseCandidateLoss, noise_index_for_exposure, noise_schedule_exposures


def test_every_candidate_gets_exact_matched_noise_budget():
    single = noise_schedule_exposures('single')
    dual = noise_schedule_exposures('dual')
    assert len(single)==513 and set(single.values())=={32}
    assert len(dual)==1026 and set(dual.values())=={16}
    totals = Counter()
    for (site,aa,noise),count in dual.items():
        totals[site,aa] += count
    assert totals == Counter({(s,a):n for (s,a,_),n in single.items()})
    # At a wrap, two candidates in one update can have different noise indices.
    assert [noise_index_for_exposure('dual',9*27,r) for r in (0,1)] == [0,1]
    for arm,step,rank in [('other',0,0),('dual',8208,0),('single',-1,0),('dual',0,2)]:
        with pytest.raises(ValueError):
            noise_index_for_exposure(arm,step,rank)


def test_decoder_noise_and_supervision_match_without_conditioning_leak():
    bank = torch.nn.Linear(1,1,bias=False)
    packet = dict(teacher=[torch.tensor(11.),torch.tensor(29.)],ca='ca',labels='labels')
    calls = []
    def condition(actual_bank,site,aa):
        assert actual_bank is bank
        calls.append(('conditioning',site,aa))
        return packet,bank.weight.sum()
    def decode(item,conditioning,noise):
        calls.append(('decode',noise))
        return conditioning+noise
    def objective(x,y,ca,labels):
        assert ca=='ca' and labels=='labels'
        calls.append(('teacher',float(y)))
        return (x-y).square(),dict(target=float(y))
    runtime=SimpleNamespace(conditioning=condition,base=SimpleNamespace(decode=decode))
    model=NoiseCandidateLoss(bank,runtime,objective)
    model('site','W',1).backward()
    assert calls == [('conditioning','site','W'),('decode',1),('teacher',29.)]
    assert bank.weight.grad is not None
    assert set(model.state_dict())=={'bank.weight'}
    with pytest.raises(ValueError):
        model('site','W',2)
