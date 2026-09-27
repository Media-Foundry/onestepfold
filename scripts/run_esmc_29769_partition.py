#!/usr/bin/env python3
"""Frozen three-layer extraction with disjoint partitions and startup evidence."""
import argparse,hashlib,json,os,socket,time
from pathlib import Path
import torch
from safetensors.torch import save_file
import build_esmc_cache as builder


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def write(p,d):
    q=p.with_suffix('.tmp');q.write_text(json.dumps(d,indent=2)+'\n');q.replace(p)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--partition',type=int,required=True);a=p.parse_args()
    root=a.root;lock=json.loads((root/'lock.json').read_text());out=root/f'part-{a.partition:03d}'
    assert a.partition in range(3) and not out.exists()
    for name,h in lock['source_sha256'].items():assert sha(root/name)==h,name
    groups=root/'groups.jsonl.gz';assert sha(groups)==lock['groups_sha256']
    allrows=builder._read_groups(groups,None);rows=builder._read_groups(groups,None,3,a.partition)
    assert len(allrows)==29769 and len(rows)==lock['partitions'][str(a.partition)]['groups']
    assert sum(len(r['sequence']) for r in rows)==lock['partitions'][str(a.partition)]['residues']
    for r in allrows:assert hashlib.sha256(r['sequence'].encode()).hexdigest()==r['group_id'] and len(r['sequence'])==r['sequence_length']
    assert torch.cuda.device_count()==1
    torch.set_num_threads(4);torch.manual_seed(101)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    out.mkdir();started=time.time();progress={'partition':a.partition,'pid':os.getpid(),'host':socket.gethostname(),'started':started,
       'gpu':torch.cuda.get_device_name(),'torch':torch.__version__,'hip':torch.version.hip,'groups_total':len(rows),'groups_processed':0,
       'groups_sha256':sha(groups),'lock_sha256':sha(root/'lock.json'),'complete':False}
    write(out/'progress.json',progress)
    original_load=builder._load_model;original_extract=builder._extract_batch
    def load(*args,**kwargs):
        model,tok=original_load(*args,**kwargs)
        ordered=sorted(allrows,key=lambda r:(r['sequence_length'],r['group_id']))
        probes=[ordered[0],ordered[len(ordered)//2],ordered[-1]];features={}
        for i,r in enumerate(probes):
            value=original_extract(model,tok,[r['sequence']],'cuda','layers_12_24_36')[0]
            value.update(original_extract(model,tok,[r['sequence']],'cuda','final')[0])
            features.update({f'probe{i}_{k}':v.contiguous() for k,v in value.items()})
        save_file(features,str(out/'startup_probes.safetensors'))
        write(out/'startup.json',{'complete':True,'probes':[{'group_id':r['group_id'],'length':r['sequence_length']} for r in probes],
              'tensor_sha256':sha(out/'startup_probes.safetensors'),'model_dtype':str(next(model.parameters()).dtype),
              'scope':'Finite, residue-aligned 20/median/longest startup probes. Cross-host and old-final-cache compatibility remain unaccepted.'})
        print(json.dumps({'startup_pass':True,'partition':a.partition}),flush=True)
        return model,tok
    def extract(model,tok,sequences,device,variant):
        values=original_extract(model,tok,sequences,device,variant)
        progress['groups_processed']+=len(sequences);progress['elapsed_seconds']=time.time()-started
        progress['peak_gpu_bytes']=torch.cuda.max_memory_allocated()
        write(out/'progress.json',progress)
        if progress['groups_processed']<30 or progress['groups_processed']%100< len(sequences):print(json.dumps(progress),flush=True)
        return values
    builder._load_model=load;builder._extract_batch=extract
    summary=builder.build_cache(groups,out,model_id='biohub/ESMC-600M',hf_revision=lock['hf_revision'],code_revision=lock['code_revision'],
       feature_variant='layers_12_24_36',device='cuda',batch_tokens=2048,shard_tokens=16384,local_files_only=True,
       partition_count=3,partition_index=a.partition)
    assert summary['groups_processed']==len(rows)
    progress['complete']=True;progress['manifest_sha256']=sha(out/'manifest.jsonl.gz');write(out/'progress.json',progress)

if __name__=='__main__':main()
