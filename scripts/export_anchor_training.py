"""Collect completed anchored fits and their pre-locked historical controls."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def export_anchor_training(root):
    root=Path(root).resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    read=lambda p:json.loads(p.read_text())
    lock=read(root/'training_lock.json');state=read(root/'controller.json')
    assert state['complete'] and state['phase']=='closed'
    assert state['lock_sha256']==sha(root/'training_lock.json')
    assert set(state['jobs'])=={f'{k}_anchor_{s}' for k in ('train','score','verify') for s in lock['seeds']}
    assert all(j['status']=='complete' and j['exit_code']==0 for j in state['jobs'].values())
    assert sha(root/'protocol.md')==lock['protocol_sha256']
    for name,digest in lock['code'].items():assert sha(root/'code'/name)==digest,name
    previous=root.parent/Path(lock['controls_root']).name
    assert sha(previous/'training_lock.json')==lock['controls_lock_sha256']
    wanted={n:root/n for n in ('training_lock.json','protocol.md','controller.json','controller.log','launch.json',
                              'preflight_tests.log','preflight_imports.log')}
    wanted.update({p.name:p for p in root.glob('*.log') if not p.name.startswith('postprocess')})
    wanted['controls/training_lock.json']=previous/'training_lock.json'
    for seed in lock['seeds']:
        rel=Path('runs/anchor')/str(seed);folder=root/rel
        report=read(folder/'report.json');tensor=read(folder/'tensor_verification.json')
        assert report['complete'] and report['gradient_passes']==128
        assert report['training_lock_sha256']==state['lock_sha256']
        assert read(folder/'score_complete.json')['complete'] and tensor['complete']
        assert tensor['feature_forwards']==2736 and tensor['reference_forwards']==144
        for name in ('report.json','history.jsonl','tensor_verification.json','score_complete.json'):
            wanted[str(rel/name)]=folder/name
        for step in lock['checkpoints']:
            for name in (f'evaluation_{step}.json',f'summary_{step}.json',f'scores_{step}.json.gz'):
                wanted[str(rel/name)]=folder/name
            ev=read(folder/f'evaluation_{step}.json')
            assert ev['complete'] and sha(folder/ev['checkpoint'])==ev['sha256']
            for prediction in ev['predictions']:assert sha(folder/prediction['path'])==prediction['sha256']
            summary=read(folder/f'summary_{step}.json')
            assert summary['complete'] and summary['evaluation_sha256']==sha(folder/f'evaluation_{step}.json')
        controls=previous/'runs/adamw'/str(seed)
        for name,digest in lock['matched_controls'][str(seed)].items():
            assert sha(controls/name)==digest,name
            if not name.startswith('checkpoints/'):
                wanted[str(Path('controls/adamw')/str(seed)/name)]=controls/name
    audit=root.parent/Path(lock['reference_cache_root']).name
    assert sha(audit/'audit_lock.json')==lock['audit_lock_sha256']
    assert sha(audit/'report.json')==lock['audit_report_sha256']
    for rec in lock['reference_records']:assert sha(audit/rec['path'])==rec['sha256']
    for name in ('audit_lock.json','report.json','verification.json'):
        source=audit/('export' if name=='verification.json' else '')/name
        wanted['reference_audit/'+name]=source
    for name in lock['overlay']+['src/fastglycan/models/anchored_pair_recovery.py','src/fastglycan/models/stage_pair_recovery.py']:
        wanted['scientific_code/'+name]=root/'code'/name
    digests={n:sha(p) for n,p in wanted.items()}
    dest,partial=root/'export',root/'export.partial'
    if dest.exists() or partial.exists():raise FileExistsError('preserve previous export; no overwrite')
    partial.mkdir()
    for name,path in wanted.items():
        target=partial/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        assert sha(target)==digests[name]
    (partial/'manifest.json').write_text(json.dumps(dict(scientific_experiment_complete=True,
        files=digests,source=str(root),source_snapshot_verified=len(lock['code']),
        bulk_tensors_exported=False,exporter_sha256=sha(Path(__file__))),indent=2,sort_keys=True)+'\n')
    partial.rename(dest)
    return dest


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    print(export_anchor_training(parser.parse_args().root))
