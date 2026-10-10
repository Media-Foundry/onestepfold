"""Export only after all original fits, scores and separate replays succeed."""
import argparse
import json
from pathlib import Path
import shutil

from fastglycan.fullbatch_results import _json, _sha
from fastglycan.placement_results import require_placement_completion


def export_pair_placement(training, verification, destination):
    training,verification,destination=map(lambda p:Path(p).resolve(),(training,verification,destination))
    lock=require_placement_completion(training,verification)
    assert _sha(training/'protocol.md')==lock['protocol_sha256']
    for name,digest in lock['code'].items():assert _sha(training/'code'/name)==digest,name
    previous=training.parent/Path(lock['previous_root']).name
    assert _sha(previous/'training_lock.json')==lock['previous_lock_sha256']
    wanted={name:training/name for name in ('training_lock.json','protocol.md','controller.json',
        'tests.log','parallel_gate.json','parallel_gate_verification.json','ledger_verification.json')}
    wanted['historical/training_lock.json']=previous/'training_lock.json'
    for path in training.glob('*.log'):wanted[path.name]=path
    for path in (training/'parallel_gate').glob('rank_*/report.json'):
        wanted[str(path.relative_to(training))]=path
    for name in ('controller.json','verification_lock.json','verify_pair_placement.py','control_placement_verification.py','import_check.log'):
        wanted['verification_source/'+name]=verification/name
    vlock=_json(verification/'verification_lock.json')
    assert _sha(verification/'verify_pair_placement.py')==vlock['verifier_sha256']
    assert _sha(verification/'control_placement_verification.py')==vlock['controller_sha256']
    checkpoints={}
    for arm,seed in lock['run_order']:
        relative=Path('runs')/arm/str(seed);folder=training/relative
        assert _json(folder/'score_complete.json')['complete']
        for path in folder.glob('rank_*/report.json'):wanted[str(path.relative_to(training))]=path
        for name in ('history.jsonl','score_complete.json'):wanted[str(relative/name)]=folder/name
        for step in lock['checkpoints']:
            for name in (f'evaluation_{step}.json',f'summary_{step}.json',f'scores_{step}.json.gz'):
                wanted[str(relative/name)]=folder/name
            ev=_json(folder/f'evaluation_{step}.json')
            assert ev['complete'] and _sha(folder/ev['checkpoint'])==ev['sha256']
            checkpoints[str(relative/ev['checkpoint'])]=dict(sha256=ev['sha256'],bytes=(folder/ev['checkpoint']).stat().st_size)
            for row in ev['predictions']:assert _sha(folder/row['path'])==row['sha256']
        vdir=verification/f'{arm}_{seed}'
        wanted[f'verification_source/{arm}_{seed}/tensor_verification.json']=vdir/'tensor_verification.json'
        wanted[f'verification_source/{arm}_{seed}.log']=verification/f'{arm}_{seed}.log'
    for seed in lock['seeds']:
        wanted[f'historical/{seed}/scores_0.json.gz']=previous/f'runs/anchor/{seed}/scores_0.json.gz'
    for name in lock['code']:wanted['scientific_code/'+name]=training/'code'/name
    partial=destination.with_name(destination.name+'.partial')
    if destination.exists() or partial.exists():raise FileExistsError('preserve existing exports and partial evidence')
    digests={name:_sha(path) for name,path in wanted.items()};partial.mkdir(parents=True)
    for name,path in wanted.items():
        out=partial/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,out)
        assert _sha(out)==digests[name]
    (partial/'manifest.json').write_text(json.dumps(dict(scientific_experiment_complete=True,
        source=str(training),verification_source=str(verification),files=digests,
        checkpoints=checkpoints,bulk_tensors_exported=False,source_snapshot_verified=len(lock['code']),
        exporter_sha256=_sha(Path(__file__))),indent=2,sort_keys=True)+'\n')
    partial.rename(destination)
    return destination


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--training',type=Path,required=True)
    p.add_argument('--verification',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(export_pair_placement(a.training,a.verification,a.output))
