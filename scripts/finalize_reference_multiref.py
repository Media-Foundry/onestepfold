"""Watch the fixed queue, audit completed runs, and write non-promotional tables."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import hashlib


def finalize_reference_multiref(root):
    virtual = Path('/data/user/shuang886/Folding') / root.name
    lock = json.loads((root/'auditor_lock.json').read_text())
    for path, digest in lock['code'].items():
        assert hashlib.sha256((root/'audit_code'/path).read_bytes()).hexdigest() == digest, path
    plan = json.loads((root/'plan.json').read_text())
    jobs = {r['run_id']: r for r in plan['runs']}
    base = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                LAYERNORM_TYPE='torch',
                PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
                PYTHONPATH=f'{virtual}/audit_code/src:{virtual}/audit_code/scripts')
    if any(k in base for k in ('CUDA_VISIBLE_DEVICES', 'ROCR_VISIBLE_DEVICES', 'GPU_DEVICE_ORDINAL', 'HSA_VISIBLE_DEVICES')):
        raise RuntimeError('conflicting inherited device selector')
    command = ['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
               '-b', str(root.parent)+':/data/user/shuang886/Folding',
               '/home/pc/anaconda3/envs/fold/bin/python', '-u',
               str(virtual/'audit_code/scripts/audit_reference_multiref.py'), '--root', str(virtual)]
    started = time.monotonic(); running = {}; records = {}
    while True:
        try:
            controller = json.loads((root/'controller.json').read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(5); continue
        if controller['phase'] == 'preflight_failed':
            break
        for name in jobs:
            state = controller.get('jobs', {}).get(name, {}).get('status')
            if name in records or name in running:
                continue
            if state == 'failed':
                records[name] = dict(training_complete=False, audit_complete=False)
            elif state == 'complete':
                log = (root/f'score_{name}.log').open('w')
                # This mode uses CPU only; it does not construct a Mini runtime.
                proc = subprocess.Popen(command+['--run-id', name, '--mode', 'score'],
                                        env=base, stdout=log, stderr=subprocess.STDOUT)
                running[name] = (proc, log)
        for name, (proc, log) in list(running.items()):
            code = proc.poll()
            if code is not None:
                log.close(); del running[name]
                records[name] = dict(training_complete=True, scoring_exit_code=code, audit_complete=False)
        state = dict(complete=False, phase='waiting_or_scoring', records=records,
                     active_scores=list(running), seconds=time.monotonic()-started)
        (root/'finalizer.json').write_text(json.dumps(state, indent=2)+'\n')
        if controller['phase'] == 'closed' and not running and len(records) == len(jobs):
            break
        time.sleep(10)
    # Replay only after all training/timing workers have exited, on one allowed device.
    for name, record in records.items():
        if not record['training_complete'] or record.get('scoring_exit_code') != 0:
            continue
        with (root/f'replay_{name}.log').open('w') as log:
            result = subprocess.run(command+['--run-id', name, '--mode', 'replay'],
                                    env=dict(base, HIP_VISIBLE_DEVICES='0'), stdout=log, stderr=subprocess.STDOUT)
        record.update(replay_exit_code=result.returncode, audit_complete=result.returncode == 0)
        (root/'finalizer.json').write_text(json.dumps(dict(complete=False, phase='replaying', records=records), indent=2)+'\n')
    summaries = {}
    for name, record in records.items():
        if record.get('audit_complete'):
            summaries[name] = json.loads((root/'runs'/name/'summary.json').read_text())
    complete = len(summaries) == 8
    result = dict(complete=complete, records=records, summaries=summaries,
                  independent_confirmation=False, promoted=False,
                  seconds=time.monotonic()-started,
                  finalizer_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (root/'aggregate.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Mini multi-reference editor: automatic terminal audit', '',
             f'All eight fixed runs and independent audits complete: **{complete}**.',
             'Reused development data; no automatic promotion or experimental-accuracy claim.', '',
             '| Run | Stratum | Parent mean rho | Top1 / sites | Raw old-select/new regret | Max local RMSD A | Exact pass-to-fail |',
             '|---|---|---:|---:|---:|---:|---:|']
    for name, data in sorted(summaries.items()):
        terminal = str(jobs[name]['updates'])
        for role, arms in data['summary'].items():
            for arm in ['reference_only', terminal]:
                row = arms[arm]; rho = row['spearman']
                rho_text = 'undefined' if rho is None else f'{rho:.6f}'
                lines.append(f"| {name}/{arm} | {role} | {rho_text} | {row['top1']}/{row['sites']} | {row['regret']:.6f} | {row['local_max']:.4f} | {row['exact_pass_to_fail']} |")
    lines += ['', 'See per-run scores.json.gz for every checkpoint, candidate/noise, geometry transition,',
              'continuous checked volumes, distance response and parent bootstrap contrast.',
              'A stopped or failed seed remains in finalizer.json; it is not replaced.',
              'Component timing excludes reference ESM/C4 preparation and is not an end-to-end speedup.']
    (root/'terminal_tables.md').write_text('\n'.join(lines)+'\n')
    (root/'finalizer.json').write_text(json.dumps(dict(complete=complete, phase='closed', records=records,
                                                      seconds=time.monotonic()-started), indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True)
    finalize_reference_multiref(p.parse_args().root)
