import json,torch
from pathlib import Path
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.reference_editor import ReferenceEditModel
print(guarded_hip_runtime(),flush=True)
data=FactorTeacherStore('/data/user/shuang886/Folding/factor_student_pilot_v1_20261002');seq=data.rows[3]['sequence'];aa=data.lock['aa'];raw=tuple(t.cuda() for t in data.load(3)['conditioning']);print('raw',[(x.shape,x.dtype,float(x.abs().max())) for x in raw],flush=True)
torch.manual_seed(271001);net=ReferenceEditModel(*[x.shape[-1] for x in raw]).cuda().eval()
with torch.no_grad():
 ref=net.prepare_reference(raw,[aa.index(a) for a in seq]);query=[[],[(36,aa.index(seq[36]),0)],[(83,aa.index(seq[83]),1)]]
 events=[]
 for i,b in enumerate(net.blocks):b.register_forward_hook(lambda m,a,o,i=i:events.append((i,tuple(t.clone() for t in o))))
 x=net(ref,query);event1=events.copy();events.clear();y=net(ref,query[::-1]);event2=events.copy();events.clear()
 print('errors', [float((a-b.flip(0)).abs().max()) for a,b in zip(x,y)],flush=True)
 for (i,a),(_,b) in zip(event1,event2):print('block',i,[float((s-t.flip(0)).abs().max()) for s,t in zip(a,b)],flush=True)
 print('solo',[[float((a[j]-b[0]).abs().max()) for a,b in zip(x,net(ref,[q]))] for j,q in enumerate(query)],flush=True)
 print('repeat',[float((a-b).abs().max()) for a,b in zip(x,net(ref,query))],flush=True)
