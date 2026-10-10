import hashlib
import inspect
import json
from pathlib import Path
import time
import torch

parent = Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding')
virtual_parent = Path('/data/user/shuang886/Folding')
root = parent/'stage_fullbatch_v1_20261010'
source = parent/'stage_pair_recovery_v1_20261010'
audit = parent/'stage_update_audit_v1_20261010_integrity1'
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (root/'training_lock.json').exists() and not (root/'runs').exists()
assert '3 passed' in (root/'prelock_tests.log').read_text()
selection = json.loads((root/'source_selection.json').read_text())
old = json.loads((source/'n15/training_lock.json').read_text())
original = json.loads((source/'build_lock.json').read_text())
for name, expected in original['code'].items():
    assert digest(source/'code'/name) == expected
    if name not in selection['replacements']:
        assert digest(root/'code'/name) == expected
fields = ['source','build_root','cache_manifest_sha256','stage_root','stage_manifest_sha256',
          'oracle_root','oracle_lock_sha256','site_scale_squared','train_sites','eval_sites','initial_hashes']
lock = {key: old[key] for key in fields}
refs = {}
for seed in (272001,272003):
    record = json.loads((audit/'runs/final'/str(seed)/'node_0.json').read_text())
    path = audit/'runs/final'/str(seed)/record['vectors']['path']
    assert digest(path) == record['vectors']['sha256']
    refs[str(seed)] = dict(path=str(virtual_parent/path.relative_to(parent)), sha256=digest(path),
                          objective=record['baseline']['objective'])
assert refs['272001']['objective'] == refs['272003']['objective']
(root/'protocol.md').write_bytes((root/'code/docs/mini_stage_fullbatch_v1.md').read_bytes())
lock.update(schema='mini_stage_fullbatch_v1', cohort='n15', arms=['adamw','lbfgs'], seeds=[272001,272003],
    gradient_budget=128, checkpoints=[0,32,128], budget_unit='complete513-candidate TRAIN gradient evaluation',
    objective='final', gradient_references=refs, initial_objective=refs['272001']['objective'],
    resident_tensor_byte_cap=32*1024**3, source_training_lock_sha256=digest(source/'n15/training_lock.json'),
    source_update_audit_lock_sha256=digest(audit/'audit_lock.json'),
    code={name:digest(root/'code'/name) for name in selection['copied_files']},
    protocol_sha256=digest(root/'protocol.md'), source_selection_sha256=digest(root/'source_selection.json'),
    prelock_test_log_sha256=digest(root/'prelock_tests.log'), torch_version=torch.__version__,
    lbfgs_source_sha256=digest(Path(inspect.getsourcefile(torch.optim.LBFGS))), created_unix=time.time(),
    per_run_training_forwards=65664, per_run_training_backwards=65664,
    per_run_fixed_prediction_forwards=2736, per_run_isolation_forwards=6, per_run_s1=7296,
    per_run_verification_forwards=2736, native_recycle_calls=0, new_esm_msa_preparation=False,
    previous_commit='d1ed39a8b886f6d3c8addcde2ff5dff96821bede', promoted=False,
    independent_confirmation=False)
(root/'training_lock.json').write_text(json.dumps(lock,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(root=str(root), lock_sha256=digest(root/'training_lock.json'),
                     files=len(lock['code']), protocol_sha256=lock['protocol_sha256'],
                     torch_version=lock['torch_version'], gradient_budget=lock['gradient_budget'])))
