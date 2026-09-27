#!/usr/bin/env python3
"""Select every eligible pre-cutoff structure sequence, preserving all prior DEV."""
import gzip, hashlib, json
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    with gzip.open(p,'rt') as f:return [json.loads(x) for x in f if x.strip()]

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    b=a.base;o=a.output;assert not o.exists()
    catalog={r['group_id']:r for r in read(b/'splits_v1/groups.jsonl.gz')}
    train=read(b/'splits_v1/train.jsonl.gz');teacher=[];sources={}
    for path in sorted((b/'stage1b/teacher_pairs_v3/input').glob('*/metadata.jsonl.gz')):
        teacher+=read(path);sources[str(path)]=sha(path)
    assert len({r['group_id'] for r in teacher})==16000
    rank=lambda g:(hashlib.sha256(('onestepfold-stage1b-teacher-pairs-v1:101:'+g).encode()).hexdigest(),g)
    reserved=set(sorted({r['group_id'] for r in teacher},key=rank)[:1600])
    oldroot=b/'esmc_expansion_data_v1_20260927';old=json.loads((oldroot/'selection.json').read_text())
    accepted=json.loads((oldroot/'acceptance.json').read_text());assert accepted['complete'] and accepted['selection_sha256']==sha(oldroot/'selection.json')
    anchors=[r for r in old if r['split']=='train'];dev=[r for r in old if r['split']=='validation']
    assert len(anchors)==8192 and len(dev)==128 and {r['group_id'] for r in dev}<=reserved
    reps={}
    def repkey(r):return (r['resolution_high_angstrom'] if r['resolution_high_angstrom'] is not None else float('inf'),r['sample_id'],r['shard'],r['npz'])
    for r in train:
        g=r['group_id'];c=catalog[g];s=c['sequence']
        if g in reserved or not set(s)<=set('ACDEFGHIKLMNPQRSTVWY'):continue
        assert c['train_seen'] and r['initial_release_date']<='2021-09-30'
        assert 20<=len(s)<=1024 and len(s)==r['sequence_length'] and hashlib.sha256(s.encode()).hexdigest()==g
        if g not in reps or repkey(r)<repkey(reps[g]):reps[g]=r
    for r in anchors:assert r['group_id'] in reps;reps[r['group_id']]=r
    ids=[r['group_id'] for r in anchors]+sorted(set(reps)-{r['group_id'] for r in anchors})
    assert len(ids)==29769 and not set(ids)&reserved
    cache={r['group_id']:r for r in read(b/'esmc_600m_final_v1/manifest.jsonl.gz')}
    rows=[]
    for i,g in enumerate(ids):
        r=dict(reps[g]);s=catalog[g]['sequence'];r.update(sequence=s,sequence_sha256=g,sequence_length=len(s),split='train',selection_index=i)
        assert cache[g]['sequence_sha256']==g and cache[g]['sequence_length']==len(s)
        assert cache[g]['feature_variant']=='final' and cache[g]['model_id']=='biohub/ESMC-600M'
        rows.append(r)
    o.mkdir(parents=True)
    for name,items in [('groups.jsonl.gz',rows),('fixed_dev.jsonl.gz',dev)]:
        with (o/name).open('wb') as f:
            with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z:
                for r in items:z.write((json.dumps(r,sort_keys=True)+'\n').encode())
    report={'complete':True,'selected_train':len(rows),'residues':sum(r['sequence_length'] for r in rows),'length_range':[20,1024],
            'length_bins':{str(n):sum(r['sequence_length']<=n for r in rows) for n in (256,384,512,768,1024)},
            'old_8192_representatives_retained':True,'all_original_1600_dev_excluded':True,'fixed_dev':128,'cached_final':len(rows),
            'sequence_contract':'Structure-derived construct sequence from accepted Stage B exact-sequence groups; NOT UniProt full length; retain unresolved positions and original residue indices, never concatenate only observed residues.',
            'source_hashes':sources|{str(b/'splits_v1/train.jsonl.gz'):sha(b/'splits_v1/train.jsonl.gz'),str(b/'splits_v1/groups.jsonl.gz'):sha(b/'splits_v1/groups.jsonl.gz'),str(oldroot/'selection.json'):sha(oldroot/'selection.json')},
            'groups_sha256':sha(o/'groups.jsonl.gz'),'source_script_sha256':sha(Path(__file__)),
            'frozen_test_coordinates_or_manifest_read':False,'structure_packets_accepted':False}
    (o/'selection_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='source_hashes'}))
if __name__=='__main__':main()
