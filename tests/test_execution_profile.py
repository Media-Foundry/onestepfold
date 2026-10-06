import torch
from fastglycan.execution_profile import leaf_inventory,compare_inventory,StageRecorder


def test_inventory_distinguishes_shape_dtype_value_and_opaque():
    a=leaf_inventory(dict(x=torch.tensor([1.,2.]),count=2,opaque=object()))
    assert compare_inventory(a,leaf_inventory(dict(x=torch.tensor([1.,2.]),count=2,opaque=object())))==dict(equal_observed=['/count','/x'],changed=[],unknown=['/opaque'])
    for x in [torch.tensor([1.,3.]),torch.tensor([[1.,2.]]),torch.tensor([1,2])]:
        assert '/x' in compare_inventory(a,leaf_inventory(dict(x=x,count=2)))['changed']
    assert leaf_inventory(torch.tensor(2.))['']['bytes']==4


def test_stage_recorder_sync_and_accumulation_preserve_output():
    events=[];r=StageRecorder(synchronize=lambda:events.append('sync'))
    with r.stage('x'):value=torch.tensor(3)+4
    with r.stage('x'):value=value*2
    assert value.item()==14 and len(events)==4 and r.seconds['x']>=0
