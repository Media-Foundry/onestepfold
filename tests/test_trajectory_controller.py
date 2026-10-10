import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


spec=importlib.util.spec_from_file_location('trajectory_controller',
    Path(__file__).resolve().parents[1]/'scripts/control_recycle_trajectory.py')
controller=importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def dependency(tmp_path, state):
    lock=tmp_path/'source_lock.json';lock.write_text('{"fixed":true}\n')
    (tmp_path/'controller.json').write_text(json.dumps(state))
    return dict(root=str(tmp_path),lock_file=lock.name,
                lock_sha256=hashlib.sha256(lock.read_bytes()).hexdigest())


def test_waiting_does_not_count_as_success(tmp_path):
    dep=dependency(tmp_path,dict(complete=False,phase='training',jobs={
        'train':dict(status='running',pid=123)}))
    assert not controller.preceding_batches_complete([dep])


def test_success_requires_completed_jobs_and_immutable_lock(tmp_path):
    dep=dependency(tmp_path,dict(complete=True,phase='complete',jobs={
        'verify':dict(status='complete',exit_code=0)}))
    assert controller.preceding_batches_complete([dep])
    (tmp_path/dep['lock_file']).write_text('changed')
    with pytest.raises(RuntimeError,match='lock changed'):
        controller.preceding_batches_complete([dep])


@pytest.mark.parametrize('state',[
    dict(complete=False,phase='failed',error='native replay failed'),
    dict(complete=True,phase='complete',jobs={}),
    dict(complete=True,phase='complete',jobs={'verify':dict(status='running')}),
    dict(complete=True,phase='complete',jobs={'verify':dict(status='complete',exit_code=1)}),
])
def test_failed_or_incomplete_evidence_cannot_release_next_batch(tmp_path,state):
    dep=dependency(tmp_path,state)
    with pytest.raises(RuntimeError):
        controller.preceding_batches_complete([dep])
