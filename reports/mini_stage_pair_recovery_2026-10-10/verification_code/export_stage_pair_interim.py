"""Snapshot completed n1 evidence; explicitly leave n15 unclosed."""
import hashlib,json,pathlib
root=pathlib.Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/stage_pair_recovery_v1_20261010')
dest=root/'interim_export';dest.mkdir(exist_ok=False);files={}
lock=json.loads((root/'build_lock.json').read_text())
for name,digest in lock['code'].items():
    assert hashlib.sha256((root/'code'/name).read_bytes()).hexdigest()==digest,name
paths=['build_lock.json','protocol.md','stage_manifest.json','preflight_tests.log','n1/training_lock.json']
paths.extend(f'cache_{i}.json' for i in range(4))
for arm in ('final','hint'):
    for seed in (272001,272003):
        rel=f'n1/runs/{arm}/{seed}';folder=root/rel
        for key in ('report','tensor_verification'):
            assert json.loads((folder/f'{key}.json').read_text())['complete']
        paths.extend(f'{rel}/{name}' for name in ('report.json','tensor_verification.json','history.jsonl','score_complete.json'))
        for step in (0,304,1216,4104,8208):
            paths.extend(f'{rel}/{name}' for name in (f'evaluation_{step}.json',f'summary_{step}.json',f'scores_{step}.json.gz'))
paths.extend(str(p.relative_to(root)) for p in sorted((root/'verification_code').glob('*.py')))
paths.extend(str(p.relative_to(root)) for p in sorted(root.glob('*.log')) if not p.name.startswith('n15'))
for name in paths:
    data=(root/name).read_bytes();target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(data);files[name]=hashlib.sha256(data).hexdigest()
status=(root/'controller.json').read_bytes()
(dest/'controller_at_interim.json').write_bytes(status)
files['controller_at_interim.json']=hashlib.sha256(status).hexdigest()
(dest/'interim_manifest.json').write_text(json.dumps(dict(status='n1_complete_n15_pending',
    scientific_experiment_complete=False,source=str(root),source_snapshot_hashes_verified=len(lock['code']),
    files=files),indent=2,sort_keys=True)+'\n')
print('EXPORTED_N1_ONLY',len(files),sum((dest/p).stat().st_size for p in files))
