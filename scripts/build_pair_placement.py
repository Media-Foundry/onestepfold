"""Cache only legal warm candidate boundaries; verify both initialization arms."""
import argparse
import json
from pathlib import Path
import time

import torch

from fastglycan.anchor_training import load_anchor_boundaries
from fastglycan.models.compensated_recycle import initialize_cached_recycle, native_recycle_step
from fastglycan.models.prefix_recycle import capture_rng_state, restore_rng_state
from fastglycan.pair_placement import PairEntryCapture, placement_lock, placement_model
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_multiref import editor_state_digest
from fastglycan.stage_pair_data import PairStageCapture, StagePairData
from run_recycle_lora import LoRARuntime


def build_pair_placement(root, shard):
    lock = placement_lock(root); start = time.monotonic()
    folder = root/('reference_gate' if shard == -1 else f'boundary_gate_{shard}')
    folder.mkdir(exist_ok=False)
    report = dict(complete=False, shard=shard, records=[], identities=0,
                  source_lock_sha256=sha256(root/'training_lock.json'))
    rt = LoRARuntime(Path(lock['source']), str(folder/'runtime')); b = rt.base
    data = PairRecoveryData(lock['build_root'], lock['cache_manifest_sha256'])
    stages = StagePairData(lock['stage_root'], lock['stage_manifest_sha256'])
    previous = json.loads((Path(lock['previous_root'])/'training_lock.json').read_text())
    old_boundaries = load_anchor_boundaries(previous, 'cuda')
    nets = {(arm, seed): placement_model(rt.model, arm, seed).eval()
            for arm in lock['arms'] for seed in lock['seeds']}
    initial = {f'{arm}_{seed}': editor_state_digest(net) for (arm,seed),net in nets.items()}
    for seed in lock['seeds']:
        assert initial[f'late_{seed}'] == previous['initial_hashes'][str(seed)]
        for name,value in nets['late',seed].state_dict().items():
            if not name.startswith('blocks.'):
                assert torch.equal(value,nets['early',seed].state_dict()[name]), name
    native_hash = editor_state_digest(rt.model)

    def save():
        report.update(seconds=time.monotonic()-start, native_counts=dict(b.counts))
        write_json(folder/'report.json', report)

    def record(path, **fields):
        report['records'].append(dict(path=str(path.relative_to(root)), sha256=sha256(path),
                                     bytes=path.stat().st_size, **fields))

    save()
    try:
        with torch.no_grad():
            if shard == -1:
                (root/'reference_cache').mkdir(exist_ok=False)
                for pi in sorted(b.references):
                    wt = b.references[pi]; item = b.item(pi)
                    init = initialize_cached_recycle(rt.model,item['features'],wt[0])
                    state,rng = rt.prefixes[pi]; ambient = capture_rng_state()
                    try:
                        with PairEntryCapture(rt.model.pairformer_stack) as entry, PairStageCapture(rt.model.pairformer_stack,indices=(13,)) as capture:
                            final = native_recycle_step(rt.model,item['features'],init,state,rng=rng)
                    finally:
                        restore_rng_state(ambient)
                    assert all(torch.equal(x,y) for x,y in zip(final,wt[1:])), pi
                    assert torch.equal(capture.values[13],old_boundaries[pi]), pi
                    boundaries = dict(early=entry.value,late=capture.values[13])
                    sites = [s for s in b.plan['sites'] if s['parent_index']==pi]
                    for site in sites:
                        pos,old = site['position_zero_based'],b.aa.index(site['original_aa'])
                        for (arm,seed),net in nets.items():
                            anchor = net.prepare_reference(wt,boundaries[arm],state[1],pos,old)
                            assert torch.count_nonzero(anchor.drift)==0,(pi,arm,seed)
                            assert net(wt,boundaries[arm],state[1],pos,old,old,anchor=anchor) is wt
                            report['identities'] += 1
                    path = root/'reference_cache'/f'{pi}.pt'
                    torch.save({k:v.cpu() for k,v in boundaries.items()},path); record(path,parent=pi)
                    save()
                assert len(report['records'])==24 and report['identities']==192
                assert b.counts==dict(c4=0,input_embedder=0,recycle=24,s1=0,updates=0)
            else:
                refs = json.loads((root/'reference_gate/report.json').read_text())
                assert refs['complete']
                refs = {r['parent']: r for r in refs['records']}
                for index,site in enumerate(b.plan['sites']):
                    if index%6 != shard: continue
                    pi,pos = site['parent_index'],site['position_zero_based']
                    old = b.aa.index(site['original_aa']); reference_pair = rt.prefixes[pi][0][1]
                    path=root/refs[pi]['path'];assert sha256(path)==refs[pi]['sha256']
                    reference = {k:v.cuda() for k,v in torch.load(path,map_location='cpu',weights_only=True).items()}
                    anchors = {(arm,seed):net.prepare_reference(b.references[pi],reference[arm],reference_pair,pos,old)
                               for (arm,seed),net in nets.items()}
                    assert all(torch.count_nonzero(a.drift)==0 for a in anchors.values())
                    for aa in site['candidates']:
                        label=b.label(pi,pos,aa);base=data.base(label)
                        with PairEntryCapture(rt.model.pairformer_stack) as entry, PairStageCapture(rt.model.pairformer_stack,indices=(13,)) as capture:
                            _,actual=rt.conditioning(None,site,aa)
                        assert all(torch.equal(x,y) for x,y in zip(actual,base)),label
                        old_boundary=stages.load(label,training=False)[0]
                        assert torch.equal(capture.values[13],old_boundary),label
                        for (arm,seed),net in nets.items():
                            result=net(base,entry.value if arm=='early' else old_boundary,reference_pair,
                                pos,old,b.aa.index(aa),anchor=anchors[arm,seed])
                            assert result[0] is base[0] and result[1] is base[1]
                            assert torch.equal(result[2],base[2]),(label,arm,seed)
                            report['identities']+=1
                        path=folder/f'{label}.pt';torch.save(dict(early=entry.value.cpu()),path)
                        record(path,label=label,site=site['site_key'],role=site['role_n15'])
                    save();print('PLACEMENT_BOUNDARY',shard,site['site_key'],flush=True)
                assert len(report['records'])==152 and report['identities']==608
                assert b.counts==dict(c4=0,input_embedder=0,recycle=152,s1=0,updates=0)
        for (arm,seed),net in nets.items():
            assert editor_state_digest(net)==initial[f'{arm}_{seed}']
            if arm=='early':net.continuation.check_unchanged()
        assert editor_state_digest(rt.model)==native_hash
        rt.finish()
        report.update(complete=True,initial_hashes=initial,parameters=1315332,
                      frozen_digest=nets['early',lock['seeds'][0]].continuation.initial_digest,
                      peak_allocated_bytes=torch.cuda.max_memory_allocated())
    except BaseException as error:
        report['error']=repr(error);raise
    finally:
        save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--shard',type=int,choices=range(-1,6),required=True)
    a=p.parse_args();build_pair_placement(a.root,a.shard)
