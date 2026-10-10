"""Export complete diagnostic scalars/provenance; large vectors stay on runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def export_stage_update_audit(root):
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    load=lambda p:json.loads(p.read_text())
    assert load(root/'controller.json')['complete']
    assert load(root/'verification.json')['complete']
    lock=load(root/'audit_lock.json')
    for path,expected in lock['code'].items():assert digest(root/'code'/path)==expected,path
    output=root/'export';output.mkdir(exist_ok=False)
    paths=['audit_lock.json','protocol.md','source_selection.json','launch.json','controller.json',
           'controller.log','verification.json','verification.log']
    counts=dict(forwards=0,backwards=0,virtual_adam_steps=0)
    for arm in ('final','hint'):
        for seed in (272001,272003):
            run=Path('runs')/arm/str(seed);report=load(root/run/'report.json')
            assert report['complete'] and len(report['nodes'])==3
            assert all(v==0 for v in report['native_counts'].values())
            for key in counts:counts[key]+=report['counts'][key]
            paths.extend([str(run/'report.json'),f'audit_{arm}_{seed}.log'])
            for node in report['nodes']:
                path=run/node['path'];assert digest(root/path)==node['sha256']
                paths.append(str(path))
    assert counts==dict(forwards=56052,backwards=6804,virtual_adam_steps=660)
    for path in paths:
        dest=output/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/path,dest)
    additions=['src/fastglycan/stage_update_diagnostic.py','scripts/audit_stage_updates.py',
               'scripts/control_stage_update_audit.py','scripts/verify_stage_update_audit.py',
               'tests/test_stage_update_diagnostic.py']
    for name in additions:
        dest=output/'verification_code'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/'code'/name,dest)
    failed=Path(lock['integrity_failure']['root'])
    failure=load(failed/'controller.json');assert failure['phase']=='failed'
    assert not (failed/'runs').exists()
    failures=['audit_lock.json','controller.json','controller.log','launch.json']
    failures.extend(f"audit_{j['arm']}_{j['seed']}.log" for j in failure['jobs'])
    for name in failures:
        dest=output/'initial_integrity_failure'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(failed/name,dest)
    manifest=dict(complete=True,source=str(root),counts=counts,accepted_training_updates=0,
                  source_files_verified=len(lock['code']),no_held_labels=True,no_native_calls=True,
                  large_parameter_vectors_exported=False,files={})
    for path in sorted(output.rglob('*')):
        if path.is_file():manifest['files'][str(path.relative_to(output))]=dict(sha256=digest(path),bytes=path.stat().st_size)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(complete=True,files=len(manifest['files']),counts=counts)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    export_stage_update_audit(p.parse_args().root)
