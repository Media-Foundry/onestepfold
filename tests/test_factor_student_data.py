import json
import pytest
from fastglycan.factor_student_data import FactorTeacherStore


def test_training_store_rejects_validation_before_reading(tmp_path):
    (tmp_path/'teacher_lock.json').write_text(json.dumps(dict(assignments=[[0]],rows=[dict(index=0,role='validation',sequence='AAA')])) )
    (tmp_path/'teacher_report.json').write_text(json.dumps(dict(complete=True)))
    (tmp_path/'teacher_manifest.json').write_text('[]')
    store=FactorTeacherStore(tmp_path,training_only=True)
    with pytest.raises(ValueError,match='validation teacher'):store.load(0,1,'C')
    assert not store.checked and not store.cache
