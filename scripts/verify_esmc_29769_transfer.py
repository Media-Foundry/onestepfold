#!/usr/bin/env python3
"""Validate copied ESMC partitions and write a reusable relative-path manifest."""
import argparse,gzip,hashlib,json,time
from pathlib import Path
import torch
from safetensors import safe_open

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def read(p):
    with gzip.open(p,'rt') as f:return [json.loads(x) for x in f if x.strip()]
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root
    torch.set_num_threads(4);start=time.time();lock=json.loads((r/'lock.json').read_text());assert sha(r/'groups.jsonl.gz')==lock['groups_sha256']
    for n,h in lock['source_sha256'].items():assert sha(r/n)==h,n
    wanted={x['group_id']:x for x in read(r/'groups.jsonl.gz')};assert len(wanted)==29769
    merged=[];seen=set();files={};spec=None
    for part in range(3):
        d=r/f'part-{part:03d}';progress=json.loads((d/'progress.json').read_text());assert progress['complete'] and progress['lock_sha256']==sha(r/'lock.json')
        assert sha(d/'manifest.jsonl.gz')==progress['manifest_sha256'];rows=read(d/'manifest.jsonl.gz')
        s=json.loads((d/'feature_spec.json').read_text())
        if spec is None:spec=s
        assert s==spec and s['feature_variant']=='layers_12_24_36' and s['hidden_dim']==1152
        assert len(rows)==lock['partitions'][str(part)]['groups']
        shards={}
        for x in rows:
            g=x['group_id'];assert g not in seen and g in wanted and int(g[:16],16)%3==part
            assert x['sequence_sha256']==g and x['sequence_length']==len(wanted[g]['sequence'])
            assert x['feature_names']==['layer_12','layer_24','layer_36'] and x['feature_variant']==s['feature_variant']
            for key in ['model_id','hf_revision','code_revision','dtype']:assert x[key]==s[key]
            seen.add(g);shards.setdefault(x['shard'],[]).append(x)
            merged.append(x|{'shard':f'part-{part:03d}/'+x['shard']})
        for name,items in sorted(shards.items()):
            path=d/name;h=sha(path);assert all(x['shard_sha256']==h for x in items)
            offset=0
            for x in sorted(items,key=lambda x:x['offset_start']):
                assert x['offset_start']==offset and x['offset_end']-offset==x['sequence_length'];offset=x['offset_end']
            with safe_open(str(path),framework='pt',device='cpu') as f:
                assert sorted(f.keys())==['layer_12','layer_24','layer_36']
                for key in f.keys():
                    t=f.get_tensor(key);assert t.shape==(offset,1152) and t.dtype==torch.bfloat16 and torch.isfinite(t).all();del t
            files[str(path.relative_to(r))]=h
            if len(files)%25==0:print(json.dumps({'checked_shards':len(files),'seconds':time.time()-start}),flush=True)
    assert seen==set(wanted) and len(files)==547
    temporary=r/'manifest.jsonl.gz.tmp'
    with temporary.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as z:
            for x in sorted(merged,key=lambda x:x['group_id']):z.write((json.dumps(x,sort_keys=True)+'\n').encode())
    temporary.replace(r/'manifest.jsonl.gz');(r/'feature_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    report={'transfer_complete':True,'groups':len(seen),'shards':len(files),'residues':sum(len(x['sequence']) for x in wanted.values()),
      'all_shard_hashes_match':True,'tensor_shape_dtype_finite_checked':True,'groups_sha256':lock['groups_sha256'],
      'merged_manifest_sha256':sha(r/'manifest.jsonl.gz'),'shard_sha256':files,'source_sha256':sha(Path(__file__)),
      'cross_hardware_numerical_compatibility_checked':False,'structure_training_packets_accepted':False,'seconds':time.time()-start}
    (r/'transfer_acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='shard_sha256'}),flush=True)
if __name__=='__main__':main()
