#!/usr/bin/env python3
"""Score paired CUDA/ROCm precision predictions on the same selected targets."""
import argparse,concurrent.futures,csv,json,tarfile
from pathlib import Path
import numpy as np
from evaluate_stage0 import evaluate_row
from score_c4_s1_attribution import summarize,METRICS
from fastglycan.paired_teacher_protocol import sha256,write_json

def worker(spec):
 rootstr,i,manifest=spec;root=Path(rootstr);f=root/f'worker_{i}';done=json.loads((f/'complete.json').read_text());assert done['complete'] and sha256(f/'progress.json')==done['progress_sha256']
 rows=[];archives={}
 try:
  for r in json.loads((f/'progress.json').read_text())['records']:
   assert sha256(f/r['artifact']['cif'])==r['artifact']['sha256']
   row=dict(manifest[r['group_id']]);row['shard']=row['shard'].replace('/hpc2hdd/home/shuang886/Folding/','/media/PM982/onestepfold/',1)
   score=evaluate_row(row,f/r['precision'],r['setting'],archives,seed=r['seed']);assert score['status']=='ok',score
   rows.append(score|dict(host='MI250',precision=r['precision'],seed=r['seed'],setting=r['setting'],feature_sha256=r['feature_sha256'],seconds=r['model_forward_seconds'],peak_bytes=r['peak_allocated_bytes']))
 finally:
  for a in archives.values():a.close()
 write_json(f/'scores.json',dict(complete=True,records=rows,progress_sha256=sha256(f/'progress.json')));return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root;lock=json.loads((root/'lock.json').read_text());manifest=json.loads((root/'manifest.json').read_text())
 with concurrent.futures.ProcessPoolExecutor(max_workers=8) as pool:chunks=list(pool.map(worker,[(str(root),i,manifest) for i in range(8)]))
 rows=[r for chunk in chunks for r in chunk]
 haccept=json.loads((root/'hpc_fp32/acceptance.json').read_text());assert haccept['complete']
 for i in range(8):
  bf=root/f'b_{i}/scores.json';fp=root/f'hpc_fp32/precision_v2_{i}/scores.json'
  assert sha256(fp)==haccept['source_scores'][f'precision_v2_{i}']
  for path,precision in [(bf,'bf16'),(fp,'fp32')]:
   for r in json.loads(path.read_text())['records']:
    if r['condition'] not in ('controlled','fp32_controlled'):continue
    rows.append(r|dict(host='H100',precision=precision,seconds=r['model_forward_seconds'],peak_bytes=r['peak_allocated_bytes']))
 index={}
 for r in rows:
  key=(r['host'],r['precision'],r['group_id'],r['seed'],r['setting']);assert key not in index;index[key]=r
 assert len(index)==102*4*3*4
 ids=lock['panel_b'];seeds=lock['seeds'];result=dict(complete=True,scope='Selected PanelB102 only; shared fixed initial noise. CUDA/ROCm and Torch versions differ; crosshost delta is a stack effect, not hardware alone.',absolute={},paired={},s1_persistence={})
 for host in ('H100','MI250'):
  for precision in ('bf16','fp32'):
   label=f'{host}_{precision}';result['absolute'][label]={};result['s1_persistence'][label]={}
   for s in ('c4_s1','c4_s2','c4_s5'):
    selected=[index[(host,precision,g,seed,s)] for g in ids for seed in seeds]
    result['absolute'][label][s]={m:float(np.mean([r[m] for r in selected])) for m in METRICS}|dict(mean_seconds=float(np.mean([r['seconds'] for r in selected])),peak_GiB=max(r['peak_bytes'] for r in selected)/2**30)
   for ref in ('c4_s2','c4_s5'):
    result['s1_persistence'][label][ref]={m:summarize(np.array([[index[(host,precision,g,seed,'c4_s1')][m]-index[(host,precision,g,seed,ref)][m] for seed in seeds] for g in ids])) for m in METRICS}
 contrasts=[('H100','fp32','H100','bf16'),('MI250','fp32','MI250','bf16'),('MI250','bf16','H100','bf16'),('MI250','fp32','H100','fp32')]
 for h,p,h0,p0 in contrasts:
  label=f'{h}_{p}_minus_{h0}_{p0}';result['paired'][label]={}
  for s in ('c4_s1','c4_s2','c4_s5'):
   for g in ids:
    for seed in seeds:
     l=index[(h,p,g,seed,s)];r=index[(h0,p0,g,seed,s)];assert l['feature_sha256']==r['feature_sha256'] and l['common_atom_count']==r['common_atom_count'] and l['all_atom_lddt_pair_count']==r['all_atom_lddt_pair_count']
   result['paired'][label][s]={m:summarize(np.array([[index[(h,p,g,seed,s)][m]-index[(h0,p0,g,seed,s)][m] for seed in seeds] for g in ids])) for m in METRICS}
 dest=root/'final';dest.mkdir(exist_ok=False);write_json(dest/'report.json',result)
 keys=['host','precision','group_id','pdb_id','seed','setting',*METRICS,'seconds','peak_bytes']
 with (dest/'per_target.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(rows)
 write_json(dest/'acceptance.json',dict(complete=True,report_sha256=sha256(dest/'report.json'),records=len(rows),csv_sha256=sha256(dest/'per_target.csv')))
if __name__=='__main__':main()
