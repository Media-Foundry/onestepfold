#!/usr/bin/env python3
"""HPC3 CPU source recovery; no folding or training, no reuse of failed new packets."""
import argparse,concurrent.futures,hashlib,json,multiprocessing,os,shutil,sys,tarfile,time,importlib
from pathlib import Path
import numpy as np
import torch


def hpc3_source_worker_init(root):
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    assert torch.get_num_threads()==torch.get_num_interop_threads()==1 and not torch.cuda.is_available()
    (Path(root)/'worker_threads'/f'{os.getpid()}.json').write_text(json.dumps(dict(pid=os.getpid(),threads=1,interop=1,gpu=False)))


def run_hpc3_source_migration(root,mode,index):
    begin=time.monotonic();base=root.parent;torch.set_num_threads(1)
    if mode=='preflight':
        assert not (root/'preflight.json').exists()
        transfer=json.loads((root/'transfer.json').read_text())
        assert hashlib.sha256((root/'inputs.tar.gz').read_bytes()).hexdigest()==transfer['archive_sha256']
        with tarfile.open(root/'inputs.tar.gz') as archive:archive.extractall(root,filter='data')
        manifest=json.loads((root/'manifest.json').read_text())
        for name,row in manifest.items():
            data=(root/name).read_bytes();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],name
        sys.path[:0]=[str(root/'code/scripts'),str(root/'code/src')]
        importlib.invalidate_caches()
        from fastglycan.paired_teacher_protocol import sha256,write_json
        from fastglycan.models.soft_sequence_chart import native_sequence_features
        hashes=json.loads((root/'cif_hashes.json').read_text());assert sha256(root/'cif_hashes.json')==transfer['cif_hashes_sha256']
        for pdb,digest in hashes.items():assert sha256(base/'Dataset/raw/pdb_mmcif'/pdb[1:3]/(pdb+'.cif.gz'))==digest,pdb
        old=json.loads((root/'origin/old/selection.json').read_text());inherited=[r for r in old if r['role']=='train'];assert len(inherited)==128
        for r in inherited:
            provenance=json.loads((root/'inherited/data/examples'/r['group_id']/'input_provenance.json').read_text());pdb=r['pdb_id']
            assert sha256(base/'Dataset/raw/pdb_mmcif'/pdb[1:3]/(pdb+'.cif.gz'))==provenance['source_mmcif_sha256']
        compatibility=[]
        for r in inherited[:2]:
            oldnative=torch.load(root/'inherited/chemistry'/r['group_id']/'native.pt',map_location='cpu',weights_only=False)
            new,atoms=native_sequence_features(r['sequence']);previous=oldnative['features']
            assert set(new)==set(previous)
            for name in ['atom_name','res_id','chain_id']:assert np.array_equal(getattr(atoms,name),getattr(oldnative['atoms'],name))
            assert np.array_equal(atoms.bonds.as_array(),oldnative['atoms'].bonds.as_array())
            pending=[(k,previous[k],new[k]) for k in previous];maximum=0.;not_exact=[]
            while pending:
                name,a,b=pending.pop()
                if isinstance(a,dict):assert set(a)==set(b);pending.extend((name+'/'+k,a[k],b[k]) for k in a)
                elif isinstance(a,torch.Tensor):
                    assert a.dtype==b.dtype and a.shape==b.shape
                    if a.is_floating_point():
                        assert torch.isfinite(a).all() and torch.isfinite(b).all();error=float((a.double()-b.double()).abs().max()) if a.numel() else 0.;maximum=max(maximum,error)
                        if not torch.equal(a,b):not_exact.append(name)
                    else:assert torch.equal(a,b)
                elif isinstance(a,np.ndarray):assert np.array_equal(a,b)
                else:assert a==b,(name,type(a))
            assert maximum<=1e-6
            compatibility.append(dict(group_id=r['group_id'],pdb_id=r['pdb_id'],floating_max_abs=maximum,nonexact_fields=not_exact))
        for folder in ['data','chemistry']:
            if folder=='data':shutil.copytree(root/'inherited/data',root/'data')
            else:shutil.copytree(root/'inherited/chemistry',root/'chemistry')
        (root/'worker_threads').mkdir()
        write_json(root/'preflight.json',dict(complete=True,transfer_members=len(manifest),candidate_cifs=len(hashes),inherited_cifs=128,native_compatibility=compatibility,torch_version=torch.__version__,seconds=time.monotonic()-begin))
        write_json(root/'migration_lock.json',dict(protocol='mini_diffusion_source_migration_hpc3_v1',hashes={str(p.relative_to(root)):sha256(p) for p in [root/'cif_hashes.json',root/'manifest.json',root/'transfer.json',root/'preflight.json',root/'migrate_expanded_sources_hpc3.py',root/'mini_diffusion_source_migration_hpc3_v1.md']},old_source_lock_sha256=sha256(root/'origin/failed/source_lock.json'),order_sha256=sha256(root/'origin/failed/candidate_order.json'),workers_per_shard=96,shards=2,folding_started=False,training_started=False))
    else:
        sys.path[:0]=[str(root/'code/scripts'),str(root/'code/src')]
        importlib.invalidate_caches()
        from fastglycan.paired_teacher_protocol import sha256,write_json
        from prepare_diffusion_training_sources import qualify_adapter_source
        lock=json.loads((root/'migration_lock.json').read_text())
        for name,digest in lock['hashes'].items():assert sha256(root/name)==digest
        assert sha256(root/'origin/failed/candidate_order.json')==lock['order_sha256']
        ordered=json.loads((root/'origin/failed/candidate_order.json').read_text())
        if mode=='worker':
            assert index in [0,1] and not (root/f'shard_{index}.json').exists()
            rows=ordered[index::2]
            with concurrent.futures.ProcessPoolExecutor(max_workers=96,mp_context=multiprocessing.get_context('spawn'),initializer=hpc3_source_worker_init,initargs=(str(root),)) as pool:
                outcomes=list(pool.map(qualify_adapter_source,[(r,base,root) for r in rows]))
            write_json(root/f'shard_{index}.json',dict(complete=True,index=index,outcomes=outcomes,seconds=time.monotonic()-begin,lock_sha256=sha256(root/'migration_lock.json')))
        elif mode=='select':
            shards=[json.loads((root/f'shard_{i}.json').read_text()) for i in [0,1]]
            assert all(s['complete'] and s['lock_sha256']==sha256(root/'migration_lock.json') for s in shards)
            results={r['group_id']:r for s in shards for r in s['outcomes']};assert len(results)==len(ordered)
            old=json.loads((root/'origin/old/selection.json').read_text());inherited=[r for r in old if r['role']=='train']
            from fastglycan.sequence_isolation import read_hsps
            edges={tuple(sorted((int(h.query[1:]),int(h.subject[1:])))) for h in read_hsps(root/'origin/old/pool_hsps.tsv') if h.query!=h.subject and h.evidence()['excluded']}
            selected=[];rejected=[]
            for r in ordered:
                result=results[r['group_id']]
                if not result['passed']:rejected.append(dict(group_id=r['group_id'],reason='native_source_preflight'));continue
                if len(selected)>=384:continue
                conflict=next((a['group_id'] for a in selected if r['pdb_id']==a['pdb_id'] or set(r['accessions']).intersection(a['accessions']) or tuple(sorted((r['pool_index'],a['pool_index']))) in edges),None)
                if conflict:rejected.append(dict(group_id=r['group_id'],reason='new_train_conflict',conflict=conflict));continue
                selected.append(r|dict(role='train',inherited=False,source=result['source'],chemistry_packet=result['chemistry_packet'],observed_heavy_fraction=result['observed_heavy_fraction']))
            combined=[r|dict(inherited=True,source=str(root/'data/examples'/r['group_id']),chemistry_packet=str(root/'chemistry'/r['group_id'])) for r in inherited]+selected
            write_json(root/'selection.json',combined);write_json(root/'rejections.json',rejected);write_json(root/'preflight_all.json',list(results.values()))
            write_json(root/'data_manifest.json',{str(p.relative_to(root)):sha256(p) for folder in ['data','chemistry'] for p in (root/folder).rglob('*') if p.is_file()})
            write_json(root/'selection_lock.json',dict(complete=len(selected)==384,selected=len(combined),additional=len(selected),inherited=128,qualified=sum(r['passed'] for r in results.values()),candidates=len(ordered),selection_sha256=sha256(root/'selection.json'),data_manifest_sha256=sha256(root/'data_manifest.json'),migration_lock_sha256=sha256(root/'migration_lock.json'),folding_started=False,training_started=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['preflight','worker','select'],required=True);p.add_argument('--index',type=int,default=-1);a=p.parse_args();assert not torch.cuda.is_available();run_hpc3_source_migration(a.root.resolve(),a.mode,a.index)
