import importlib.util
from pathlib import Path
import sys
import types


def test_alternative_preflight_stops_at_first_supported_record(monkeypatch, tmp_path):
    script=Path(__file__).parents[1]/'scripts/prepare_folding_source_variants.py'
    spec=importlib.util.spec_from_file_location('source_variant_test_driver',script)
    driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    calls=[]
    def fake_qualification(args):
        row,base,folder=args;calls.append((row,base,folder))
        return dict(passed=row['pdb_id']=='second',group_id='group',pdb_id=row['pdb_id'],
            source=str(folder/'data/examples/group'),chemistry_packet=str(folder/'chemistry/group'),
            source_mmcif_sha256='fixture',observed_heavy_fraction=1.)
    monkeypatch.setitem(sys.modules,'prepare_diffusion_training_sources',
        types.SimpleNamespace(qualify_adapter_source=fake_qualification))
    group=dict(index=7,group_id='group',variants=[dict(group_id='group',pdb_id=p,source_label_asym_id='A')
        for p in ['first','second','third']])
    result=driver.qualify_folding_variant_group((group,str(tmp_path)))
    assert [x[0]['pdb_id'] for x in calls]==['first','second']
    assert calls[0][2]!=calls[1][2] and all(x[1]==tmp_path.parent for x in calls)
    assert result['chosen']['variant_index']==1 and result['chosen']['role']=='reserved_source'
    assert [x['passed'] for x in result['attempts']]==[False,True]
