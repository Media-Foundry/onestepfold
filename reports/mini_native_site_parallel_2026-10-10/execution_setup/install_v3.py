"""Install, preflight, lock and launch one corrected native audit on DiamondHill."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time


base = Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding')
old = base/'native_site_parallel_v2_20261010'
root = base/'native_site_parallel_v3_20261010'
virtual = '/data/user/shuang886/Folding/'+root.name
overlay = Path('/tmp/native_parallel_loader_fix_3a4b1d58.tar')
metadata = json.loads(overlay.with_suffix('.json').read_text())
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert digest(overlay) == metadata['sha256']
assert json.loads((old/'controller.json').read_text())['phase'] == 'failed'
assert not root.exists(), 'attempts are immutable; never overwrite/restart'
for pid in [1050466,1050467,1050468,*range(1050487,1050493)]:
    assert not Path('/proc'/Path(str(pid))).exists(), pid
root.mkdir()
shutil.copytree(old/'code', root/'code')
with tarfile.open(overlay) as archive:
    assert all(member.isfile() and not Path(member.name).is_absolute()
               and '..' not in Path(member.name).parts for member in archive.getmembers())
    archive.extractall(root/'code')
for name, value in metadata['files'].items():
    assert digest(root/'code'/name) == value, name
shutil.copyfile(__file__, root/'install.py')
old_lock = json.loads((old/'audit_lock.json').read_text())
training = base/'reference_anchor_training_v1_20261010'
training_lock = json.loads((training/'training_lock.json').read_text())
assert digest(training/'training_lock.json') == old_lock['training_lock_sha256']
for name, value in training_lock['code'].items():
    assert digest(root/'code'/name) == value, name

runtime = '/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime'
physical_runtime = base/'protenix_stage0_pkg/v1_1/runtime'
weights = ['protenix_mini_esm_v0.5.0.pt', 'esm2_t36_3B_UR50D.pt',
           'esm2_t36_3B_UR50D-contact-regression.pt']
for name in weights:
    assert (physical_runtime/'checkpoint'/name).is_file(), name
env = dict(os.environ, HIP_VISIBLE_DEVICES='', FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
           PROTENIX_ROOT_DIR=runtime, LAYERNORM_TYPE='torch', OMP_NUM_THREADS='1',
           OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
           PYTHONPATH=virtual+'/code/src:'+virtual+'/code/scripts')
assert not any(key in env for key in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES',
                                     'GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES'))
prefix = [old_lock['proot'], '-b', str(base)+':'+old_lock['bind_target'],old_lock['python']]
tests = ['test_native_parallel_audit.py','test_hip_device_policy.py']
command = prefix+['-m','pytest','-q','-p','no:cacheprovider']+[
    virtual+'/code/tests/'+name for name in tests]
started = time.time()
with (root/'preflight.log').open('x') as stream:
    result = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT,
                            timeout=180)
preflight = dict(complete=result.returncode==0, exit_code=result.returncode,
                 seconds=time.time()-started, log_sha256=digest(root/'preflight.log'),
                 command=command)
(root/'preflight.json').write_text(json.dumps(preflight,indent=2)+'\n')
print((root/'preflight.log').read_text(),flush=True)
assert result.returncode == 0, 'preflight failed; no GPU process launched'

hardware = json.loads(subprocess.check_output(
    ['rocm-smi','--showuse','--showmeminfo','vram','--showbus','--json'],text=True))
by_bus = {item['PCI Bus'].lower(): item for item in hardware.values()}
for bus in old_lock['pci_buses']:
    card = by_bus[bus]
    assert int(card['GPU use (%)']) == 0, (bus,card)
    assert int(card['VRAM Total Used Memory (B)']) < 128*1024**2, (bus,card)
(root/'hardware_preflight.json').write_text(json.dumps(hardware,indent=2)+'\n')
protocol = '\n'.join((root/'code/docs'/name).read_text() for name in [
    'mini_native_site_parallel_v1.md','mini_native_site_parallel_v2.md',
    'mini_native_site_parallel_v3.md'])
(root/'protocol.md').write_text(protocol)
code = {str(path.relative_to(root/'code')):digest(path)
        for path in sorted((root/'code').rglob('*'))
        if path.is_file() and '__pycache__' not in path.parts and '.pytest_cache' not in path.parts}
lock = dict(old_lock, created_unix=time.time(), virtual_root=virtual, code=code,
            protenix_root_dir=runtime, protocol_sha256=digest(root/'protocol.md'),
            preflight_sha256=digest(root/'preflight.json'),
            hardware_preflight_sha256=digest(root/'hardware_preflight.json'),
            failed_v2_lock_sha256=digest(old/'audit_lock.json'),
            loader_correction_sha256=digest(root/'code/docs/mini_native_site_parallel_v3.md'),
            installer_sha256=digest(root/'install.py'),
            native_loader_rank_isolation='configure_torchrun_worker then explicit Gloo',
            runtime_environment={key:env[key] for key in ['PROTENIX_ROOT_DIR',
                'LAYERNORM_TYPE','FASTGLYCAN_AUTHORIZED_HIP_0_5','OMP_NUM_THREADS',
                'OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']})
(root/'audit_lock.json').write_text(json.dumps(lock,sort_keys=True,indent=2)+'\n')
with (root/'controller.log').open('x') as stream:
    process = subprocess.Popen(['python3',str(root/'code/scripts/control_native_site_parallel.py'),
        '--root',str(root)],stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,
        start_new_session=True)
launch = dict(pid=process.pid,started_unix=time.time(),audit_lock_sha256=digest(root/'audit_lock.json'))
(root/'launch.json').write_text(json.dumps(launch,indent=2)+'\n')
print(json.dumps(launch),flush=True)
