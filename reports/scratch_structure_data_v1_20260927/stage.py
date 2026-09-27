import gzip,json,hashlib,shutil
from pathlib import Path
b=Path('/media/PM982/onestepfold');r=b/'scratch_structure_data_v1_20260927';r.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with gzip.open(b/'data/esmc_29769_layers_12_24_36_v1_20260927/groups.jsonl.gz','rt') as f:rows=list(map(json.loads,f))
old=json.loads((b/'scratch_structure_inputs_v1_20260927/selection.json').read_text())
qa=json.loads((b/'scratch_structure_inputs_v1_20260927/acceptance.json').read_text())
assert qa['complete'] and qa['selection_sha256']==sha(b/'scratch_structure_inputs_v1_20260927/selection.json')
oldtrain=[x for x in old if x['split']=='train'];dev=[x for x in old if x['split']=='validation'];existing={x['group_id'] for x in oldtrain}
assert len(oldtrain)==8192 and len(dev)==128 and existing<={x['group_id'] for x in rows}
new=[]
for row in rows:
 if row['group_id'] in existing:continue
 row=dict(row);row['input_shard']='primary-%04d'%(len(new)//128);row['teacher_shard']=row['input_shard'];new.append(row)
assert len(new)==21577
(r/'input').mkdir();(r/'new/examples').mkdir(parents=True);(r/'examples').mkdir()
for shard in sorted({x['input_shard'] for x in new}):
 d=r/'input'/shard;d.mkdir()
 with gzip.open(d/'metadata.jsonl.gz','wt') as f:
  for x in new:
   if x['input_shard']==shard:f.write(json.dumps(x,sort_keys=True)+'\n')
for row in new:(r/'examples'/row['group_id']).symlink_to(r/'new/examples'/row['group_id'])
full=oldtrain+new+dev
(r/'selection.json').write_text(json.dumps(full,indent=2)+'\n')
(r/'new/selection.json').write_text(json.dumps(new,indent=2)+'\n')
(r/'new/selection_report.json').write_text(json.dumps({'complete':True,'selection_sha256':sha(r/'new/selection.json')})+'\n')
lengthsort=sorted(new,key=lambda x:(len(x['sequence']),x['group_id']))
smoke=[lengthsort[i] for i in sorted(set([0,len(lengthsort)//4,len(lengthsort)//2,3*len(lengthsort)//4,len(lengthsort)-2,len(lengthsort)-1]))]
(r/'smoke/examples').mkdir(parents=True)
(r/'smoke/selection.json').write_text(json.dumps(smoke,indent=2)+'\n')
(r/'smoke/selection_report.json').write_text(json.dumps({'complete':True,'selection_sha256':sha(r/'smoke/selection.json')})+'\n')
report={'complete':True,'train':29769,'validation':128,'new_train':21577,'reused':8320,'selection_sha256':sha(r/'selection.json'),'new_selection_sha256':sha(r/'new/selection.json'),'old_acceptance_sha256':sha(b/'scratch_structure_inputs_v1_20260927/acceptance.json'),'esmc_manifest_sha256':sha(b/'esmc_600m_final_v1/manifest.jsonl.gz'),'structure_preparation_complete':False,'smoke_lengths':[len(x['sequence']) for x in smoke]}
(r/'selection_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
