"""Check failure gating and the protein-weighted latent summary independently."""
import importlib.util
import json
from pathlib import Path

import pytest

from fastglycan.anchor_results import pool_anchor_latent


def test_incomplete_anchor_training_cannot_export(tmp_path):
    script=Path(__file__).parents[1]/'scripts/export_anchor_training.py'
    spec=importlib.util.spec_from_file_location('anchor_export',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    (tmp_path/'training_lock.json').write_text('{}')
    (tmp_path/'controller.json').write_text(json.dumps(dict(complete=False,phase='training')))
    with pytest.raises(AssertionError):module.export_anchor_training(tmp_path)
    assert not (tmp_path/'export').exists() and not (tmp_path/'export.partial').exists()


def test_latent_pool_weights_proteins_not_pair_rows_or_sites():
    def row(parent,value):
        m=dict(nmse=value,energy_ratio=value/2,cosine=.5,predicted_energy=4)
        return dict(parent=parent,role='train',moments=dict(raw=dict(m),common=dict(m,predicted_energy=1),centered=dict(m)))
    pooled=pool_anchor_latent(dict(step=0,latent=[row(0,1.),row(0,3.),row(1,8.)]))['train']
    assert pooled['centered_nmse']==5. and pooled['common_fraction']==.25
    assert pooled['parents']==2 and pooled['sites']==3
