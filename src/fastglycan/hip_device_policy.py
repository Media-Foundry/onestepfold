"""Fail closed on DiamondHill's distinct HIP and management GPU enumerations."""
import ctypes
import os
from pathlib import Path

SAFE_HIP_ORDINALS=(0,1,2,3)
# Intersection of user-authorized HIP0--5 and management-GCD0--5 on DiamondHill.
SAFE_PCI_TO_GCD={'0000:11:00.0':0,'0000:14:00.0':1,'0000:32:00.0':2,'0000:35:00.0':3}
RESERVED_PCI={'0000:ae:00.0','0000:b3:00.0'}
SIX_HIP_PCI={0:'0000:32:00.0',1:'0000:35:00.0',2:'0000:11:00.0',
             3:'0000:14:00.0',4:'0000:ae:00.0',5:'0000:b3:00.0'}


def validate_selected_device(environment,pci):
    if any(k in environment for k in ['CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES']):raise RuntimeError('only HIP_VISIBLE_DEVICES may select devices')
    hip=environment.get('HIP_VISIBLE_DEVICES','')
    if environment.get('FASTGLYCAN_AUTHORIZED_HIP_0_5')=='1':
        if hip not in tuple(map(str,SIX_HIP_PCI)) or pci.lower()!=SIX_HIP_PCI[int(hip)]:
            raise RuntimeError('six-device authorization requires verified single HIP0..5 mapping')
        gcd={**SAFE_PCI_TO_GCD,'0000:ae:00.0':6,'0000:b3:00.0':7}[pci.lower()]
        return dict(hip_visible=hip,cuda_visible=None,rocr_visible=None,pci_bus_id=pci.lower(),
                    management_gcd=gcd,physical_mapping_verified=True,authorization='explicit HIP0..5')
    if hip not in tuple(map(str,SAFE_HIP_ORDINALS)):raise RuntimeError('use one safe HIP ordinal0..3; HIP4/5 reach reserved management GCD6/7')
    pci=pci.lower()
    if pci in RESERVED_PCI or pci not in SAFE_PCI_TO_GCD:raise RuntimeError(f'refusing unapproved PCI device {pci}')
    return dict(hip_visible=hip,cuda_visible=None,rocr_visible=None,pci_bus_id=pci,management_gcd=SAFE_PCI_TO_GCD[pci],physical_mapping_verified=True)


def guarded_hip_runtime():
    # Check selectors BEFORE importing torch or initializing the HIP runtime.
    env=os.environ;hip=env.get('HIP_VISIBLE_DEVICES','')
    allowed=SIX_HIP_PCI if env.get('FASTGLYCAN_AUTHORIZED_HIP_0_5')=='1' else SAFE_HIP_ORDINALS
    if hip not in tuple(map(str,allowed)) or any(k in env for k in ['CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES']):raise RuntimeError('invalid HIP-only resource policy')
    import torch
    paths={line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'libamdhip64.so' in line and line.split()[-1].startswith('/')}
    if len(paths)!=1:raise RuntimeError(f'cannot unambiguously locate loaded HIP runtime: {paths}')
    library=ctypes.CDLL(paths.pop());count=ctypes.c_int()
    if library.hipGetDeviceCount(ctypes.byref(count))!=0 or count.value!=1:raise RuntimeError('expected exactly one HIP device')
    bus=ctypes.create_string_buffer(64)
    if library.hipDeviceGetPCIBusId(bus,64,0)!=0:raise RuntimeError('could not verify selected PCI device')
    result=validate_selected_device(env,bus.value.decode())
    # Only after physical verification may any model/tensor be allocated.
    if torch.cuda.device_count()!=1:raise RuntimeError('Torch and HIP device counts differ')
    torch.set_num_threads(1)
    return dict(result,torch=torch.__version__,hip=torch.version.hip,device=torch.cuda.get_device_name())
