"""Compare streamed, site-weighted training with an independent joint graph."""
import copy

import pytest
import torch

from fastglycan.anchor_training import AnchoredFullBatchTrainer
from test_anchored_pair_recovery import _case


@pytest.mark.parametrize('steps', [1, 3])
def test_fullbatch_anchor_gradient_and_adam_match_joint_graph(steps):
    model, _, reference, (wt, boundary), candidates = _case()
    with torch.no_grad():
        for p in model.parameters():
            p.add_(torch.randn_like(p)*.01)
    other = copy.deepcopy(model)
    sites = [dict(site_key=f's{k}', parent_index=k, position_zero_based=k,
                  original_aa='A', candidates=list('CDE')) for k in range(2)]
    labels = {(k,aa):torch.randn_like(reference) for k in range(2) for aa in 'CDE'}
    scales = {'s0':.2, 's1':3.}
    def fetch(site,aa):
        base,z = candidates['CDE'.index(aa)]
        return base,z,labels[site['parent_index'],aa]
    trainer = AnchoredFullBatchTrainer(model,sites,fetch,{0:reference,1:reference},
        'ACDE',scales,{0:wt,1:wt},{0:boundary,1:boundary})
    optimizers = [torch.optim.AdamW(n.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8)
                  for n in (model,other)]
    for _ in range(steps):
        result = trainer.objective()
        other.zero_grad(set_to_none=True)
        loss = 0.
        for site in sites:
            pos=site['position_zero_based']
            anchor=other.prepare_reference(wt,boundary,reference,pos,0)
            for aa in 'CDE':
                base,z,label=fetch(site,aa)
                pred=other(base,z,reference,pos,0,'ACDE'.index(aa),anchor=anchor)[2]
                loss=loss+(pred-label).square().mean()/scales[site['site_key']]/6
        loss.backward()
        assert result['raw'] == pytest.approx(float(loss.detach()),rel=1e-12)
        assert result['raw'] == pytest.approx(result['common']+result['centered'],rel=1e-12)
        for p,q in zip(model.parameters(),other.parameters()):
            torch.testing.assert_close(p.grad,q.grad,rtol=1e-10,atol=1e-12)
        for net,optimizer in zip((model,other),optimizers):
            torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True)
            optimizer.step()
        for p,q in zip(model.parameters(),other.parameters()):
            torch.testing.assert_close(p,q,rtol=1e-10,atol=1e-12)
    assert trainer.counts == dict(forwards=6*steps,backwards=6*steps,gradient_passes=steps,
                                reference_forwards=2*steps,reference_backwards=2*steps)
