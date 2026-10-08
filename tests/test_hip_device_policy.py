import pytest
from fastglycan.hip_device_policy import validate_selected_device


def test_mapped_safe_hip_device_and_reserved_pci_are_distinct():
    assert validate_selected_device({'HIP_VISIBLE_DEVICES':'0'},'0000:32:00.0')['management_gcd']==2
    for env,pci in [({'HIP_VISIBLE_DEVICES':'4'},'0000:ae:00.0'),({'HIP_VISIBLE_DEVICES':'5'},'0000:b3:00.0'),({'HIP_VISIBLE_DEVICES':'0'},'0000:ae:00.0'),({'HIP_VISIBLE_DEVICES':'6'},'0000:8e:00.0'),({'HIP_VISIBLE_DEVICES':'0,1,2,3,4,5'},'0000:32:00.0')]:
        with pytest.raises(RuntimeError):validate_selected_device(env,pci)


def test_other_device_selectors_fail_even_if_empty():
    for selector in ['CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES']:
        with pytest.raises(RuntimeError):validate_selected_device({'HIP_VISIBLE_DEVICES':'0',selector:''},'0000:32:00.0')


def test_explicit_six_hip_authorization_is_scoped_and_mapping_checked():
    from fastglycan.hip_device_policy import SIX_HIP_PCI
    for i,pci in SIX_HIP_PCI.items():
        env={'HIP_VISIBLE_DEVICES':str(i),'FASTGLYCAN_AUTHORIZED_HIP_0_5':'1'}
        assert validate_selected_device(env,pci)['physical_mapping_verified']
        with pytest.raises(RuntimeError): validate_selected_device(env,'0000:8e:00.0')
    for selector in ['6','7','0,1']:
        with pytest.raises(RuntimeError):
            validate_selected_device({'HIP_VISIBLE_DEVICES':selector,'FASTGLYCAN_AUTHORIZED_HIP_0_5':'1'},'0000:32:00.0')
