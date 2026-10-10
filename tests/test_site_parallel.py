"""Actual Gloo workers versus serial reference-gradient accumulation and AdamW."""
import copy
from datetime import timedelta

import pytest
import torch
import torch.distributed as dist
import torch.multiprocessing as mp

from fastglycan.anchor_training import AnchoredFullBatchTrainer
from fastglycan.site_parallel import local_anchor_gradients, ordered_site_mean, synchronized_anchor_step
from test_anchored_pair_recovery import _case


def _parallel_worker(rank,world,path,site_count,dtype_name):
    torch.set_num_threads(1)
    dist.init_process_group('gloo',init_method='file://'+path,rank=rank,world_size=world,
                            timeout=timedelta(seconds=45))
    try:
        model,_,reference,(wt,boundary),candidates=_case(getattr(torch,dtype_name))
        serial=copy.deepcopy(model) if rank==0 else None
        sites=[dict(site_key=f's{i}',parent_index=i,position_zero_based=i%4,
                    original_aa='A',candidates=list('CDE')) for i in range(site_count)]
        labels={(i,aa):torch.randn_like(reference) for i in range(site_count) for aa in 'CDE'}
        scales={f's{i}':.2+i*.4 for i in range(site_count)}
        refs={i:reference for i in range(site_count)}
        bases={i:wt for i in range(site_count)};boundaries={i:boundary for i in range(site_count)}
        def fetch(site,aa):
            base,z=candidates['CDE'.index(aa)]
            return base,z,labels[site['parent_index'],aa]
        optimizer=torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8) if rank==0 else None
        serial_optimizer=torch.optim.AdamW(serial.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8) if rank==0 else None
        if rank==0:
            serial_trainer=AnchoredFullBatchTrainer(serial,sites,fetch,refs,'ACDE',scales,bases,boundaries)
        for step in range(3):
            if rank==0:
                expected=serial_trainer.objective();expected_gradient=serial_trainer.last_gradient.clone()
                torch.nn.utils.clip_grad_norm_(serial.parameters(),1.,error_if_nonfinite=True)
                serial_optimizer.step()
            local=local_anchor_gradients(model,sites,fetch,refs,'ACDE',scales,bases,boundaries,
                list(range(rank,site_count,world)))
            result=synchronized_anchor_step(model,local,[s['site_key'] for s in sites],optimizer)
            assert result['summary']['counts']==dict(forwards=site_count*3,backwards=site_count*3,
                reference_forwards=site_count,reference_backwards=site_count,gradient_passes=1)
            if rank==0:
                torch.testing.assert_close(result['gradient'],expected_gradient,rtol=0,atol=0)
                assert result['summary']['raw']==expected['raw']
                for a,b in zip(model.parameters(),serial.parameters()):
                    torch.testing.assert_close(a,b,rtol=0,atol=0)
                for a,b in zip(optimizer.state.values(),serial_optimizer.state.values()):
                    for key in ('step','exp_avg','exp_avg_sq'):
                        torch.testing.assert_close(a[key],b[key],rtol=0,atol=0)
        guard=[p.detach().clone() for p in model.parameters()]
        # Reusing the preceding pass is rejected collectively before an update.
        with pytest.raises(RuntimeError,match='stale site gradients'):
            synchronized_anchor_step(model,local,[s['site_key'] for s in sites],optimizer)
        for a,b in zip(model.parameters(),guard):torch.testing.assert_close(a,b,rtol=0,atol=0)
        # A local failure is broadcast before any further optimizer update.
        with pytest.raises(RuntimeError,match='worker failed'):
            synchronized_anchor_step(model,[],[s['site_key'] for s in sites],optimizer,
                local_error='intentional test failure' if rank==world-1 else None)
        for a,b in zip(model.parameters(),guard):torch.testing.assert_close(a,b,rtol=0,atol=0)
    finally:dist.destroy_process_group()


@pytest.mark.parametrize('site_count',[2,5])
@pytest.mark.parametrize('dtype_name',['float32','float64'])
def test_three_ranks_match_serial_with_empty_and_uneven_shards(tmp_path,site_count,dtype_name):
    # CPU/Gloo only; the native Mini workload and existing GPU jobs are untouched.
    mp.spawn(_parallel_worker,args=(3,str(tmp_path/'rendezvous'),site_count,dtype_name),nprocs=3,join=True)


def test_ordered_site_reducer_rejects_duplicate_identity_and_nonfinite_gradients():
    def record(i):
        return dict(index=i,site=f's{i}',row=dict(site=f's{i}',raw=3.,common=1.,centered=2.),
            gradient=torch.ones(4,dtype=torch.float64),counts=dict(forwards=19,backwards=19,
                reference_forwards=1,reference_backwards=1,gradient_passes=1))
    with pytest.raises(ValueError,match='duplicated'):ordered_site_mean([record(0),record(0)],['s0','s1'],4)
    with pytest.raises(ValueError,match='missing'):ordered_site_mean([record(0)],['s0','s1'],4)
    broken=record(1);broken['gradient'][0]=float('nan')
    with pytest.raises(ValueError,match='finite'):ordered_site_mean([record(0),broken],['s0','s1'],4)
