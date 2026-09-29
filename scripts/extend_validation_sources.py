#!/usr/bin/env python3
"""Expand pre-cutoff structural sources without changing the calibrated rule."""
import argparse,collections,csv,gzip,hashlib,json,subprocess,tarfile,traceback
import concurrent.futures,multiprocessing
from pathlib import Path
import numpy as np
from fastglycan.sequence_isolation import read_hsps
from onestepfold.data.gt_materializer import materialize_entry,ATOM37_INDEX
from fastglycan.experimental_metrics import validate_experimental_record


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')


def jsonl(p):
    with gzip.open(p,'rt') as f:
        yield from (json.loads(line) for line in f if line.strip())


def materialize(row,base,root):
    folder=root/'examples'/row['group_id'];folder.mkdir(parents=True,exist_ok=False)
    result=dict(group_id=row['group_id'],passed=False)
    try:
        shard=base/'processed_stageb_v1/shards'/Path(row['shard']).name
        with tarfile.open(shard) as archive:
            for key,name in [('npz','gt.npz'),('metadata','gt.json')]:
                assert Path(row[key]).name==row[key]
                with archive.extractfile(row[key]) as f:(folder/name).write_bytes(f.read())
        meta=json.loads((folder/'gt.json').read_text())
        with np.load(folder/'gt.npz') as saved:arrays=dict(saved)
        validate_experimental_record(arrays,meta,row['sequence'],row['sample_id'])
        raw=base/'Dataset/raw/pdb_mmcif'/row['pdb_id'][1:3]/(row['pdb_id']+'.cif.gz')
        assert sha(raw)==meta['provenance']['source_mmcif_sha256']
        rebuilt,_=materialize_entry(dict(pdb_id=row['pdb_id'],sequence=row['sequence'],
            source_label_asym_id=meta['chains'][0]['source_label_asym_id'],assembly_id=meta['assembly_id']),raw)
        assert all(np.array_equal(v,rebuilt[k]) for k,v in arrays.items())
        qa=meta['qa'];assert qa['modified_residue_count']==qa['chain_break_count']==0 and qa['backbone4_coverage']==1
        sgmask=arrays['atom37_mask'][:,ATOM37_INDEX['SG']] & arrays['residue_mask']
        sg=arrays['atom37_positions'][sgmask,ATOM37_INDEX['SG']].astype(float)
        if len(sg)>1:
            d=np.linalg.norm(sg[:,None]-sg[None],axis=-1)
            assert not np.any(d[np.triu_indices(len(sg),1)]<2.3),'unsupported SG close contact'
        write(folder/'input_provenance.json',dict(group_id=row['group_id'],sequence=row['sequence'],
            raw_gt_rebuild_exact=True,source_mmcif_sha256=sha(raw),source_shard=str(shard),
            source_kind='validation-only GT extraction, not an ESMC training packet'))
        write(folder/'prepared.json',dict(complete=True,files_sha256={n:sha(folder/n) for n in ['gt.json','gt.npz','input_provenance.json']}))
        result.update(passed=True,prepared_sha256=sha(folder/'prepared.json'))
    except Exception:result['error']=traceback.format_exc()
    write(folder/'materialization_report.json',result);return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--base',type=Path,required=True)
    p.add_argument('--v1',type=Path,required=True);p.add_argument('--v2',type=Path,required=True);p.add_argument('--bin',type=Path,required=True)
    a=p.parse_args();r=a.root;b=a.base;r.mkdir(parents=True,exist_ok=True)
    assert not (r/'source_lock.json').exists()
    old=json.loads((a.v1/'screen_lock.json').read_text());retained=json.loads((a.v2/'qualified_panel.json').read_text());assert len(retained)==27
    refs=json.loads((a.v1/'references.json').read_text());seen={x['group_id'] for x in json.loads((a.v1/'pool.json').read_text())}
    denied={x['group_id'] for x in refs}|seen;denied_pdb=set(old['excluded_pdbs']);denied_acc=set(old['excluded_accessions'])
    for x in retained:denied_acc.update(x['accessions'])
    sifts=b/'Dataset/raw/sifts/2026-09-08/pdb_chain_uniprot.csv.gz';accessions={}
    with gzip.open(sifts,'rt') as f:
        for x in csv.DictReader(line for line in f if not line.startswith('#')):accessions.setdefault(x['PDB'].lower(),set()).add(x['SP_PRIMARY'])
    train=b/'splits_v1/train.jsonl.gz';pairs={(x['group_id'],x['sample_id']) for x in jsonl(train)}
    representatives={};counts=collections.Counter();indexes=sorted((b/'processed_stageb_v1').glob('index-worker-*.jsonl.gz'));assert len(indexes)==32
    for path in indexes:
        for row in jsonl(path):
            seq=row['sequence'];g=hashlib.sha256(seq.encode()).hexdigest();pdb=row['pdb_id'].lower()
            if (g,row['sample_id']) not in pairs or row['initial_release_date']>'2021-09-30':continue
            if not 256<=len(seq)<=1024:continue
            counts['source_rows']+=1
            if g in denied:counts['seen_group']+=1;continue
            if pdb in denied_pdb:counts['development_pdb']+=1;continue
            acc=accessions.get(pdb,set())
            if not acc or acc&denied_acc:counts['accession']+=1;continue
            qa=row['qa']
            if not set(seq)<=set('ACDEFGHIKLMNPQRSTVWY') or qa['modified_residue_count'] or qa['chain_break_count'] or qa['backbone4_coverage']<1:
                counts['source_scope']+=1;continue
            out=dict(row,group_id=g,sequence_sha256=g,split='new_validation_reserved',stratum=2 if len(seq)<512 else 3,accessions=sorted(acc))
            rank=lambda x:(x.get('resolution_high_angstrom') or float('inf'),x['sample_id'],x['shard'])
            if g not in representatives or rank(out)<rank(representatives[g]):representatives[g]=out
    pool=[]
    for stratum in [2,3]:
        pool+=sorted((x for x in representatives.values() if x['stratum']==stratum),
                     key=lambda x:hashlib.sha256(('anchored-extension-v1:20260930:'+x['group_id']).encode()).hexdigest())[:128]
    write(r/'pool.json',pool)
    lock=dict(protocol_sha256=sha(r/'code/docs/mini_validation_source_extension_v1.md'),script_sha256=sha(Path(__file__)),
        source_counts=dict(counts),eligible_groups=len(representatives),pool=len(pool),strata_counts=[sum(x['stratum']==i for x in pool) for i in [2,3]],
        pool_sha256=sha(r/'pool.json'),source_hashes={str(x):sha(x) for x in [train,sifts,a.v1/'screen_lock.json',a.v1/'references.json',a.v2/'qualified_panel.json',*indexes]})
    write(r/'source_lock.json',lock);print(json.dumps(lock['strata_counts']),flush=True)
    allrows=pool+retained;aliases={x['group_id'][:32]:x['group_id'] for x in [*refs,*allrows]};assert len(aliases)==len({x['group_id'] for x in [*refs,*allrows]})
    write(r/'aliases.json',aliases)
    fasta=lambda path,rows:path.write_text(''.join('>'+x['group_id'][:32]+'\n'+x['sequence']+'\n' for x in rows))
    fasta(r/'candidates.fasta',pool);fasta(r/'pair_panel.fasta',allrows)
    commands=[]
    def run(cmd,label):
        commands.append(cmd);write(r/'commands.json',commands)
        with (r/(label+'.log')).open('w') as log:subprocess.run(cmd,check=True,stdout=log,stderr=subprocess.STDOUT)
    def search(query,db,out,n,dbsize=None):
        cmd=[str(a.bin/'blastp'),'-task','blastp','-query',str(query),'-db',str(db),'-out',str(out),'-word_size','3',
            '-matrix','BLOSUM62','-gapopen','11','-gapextend','1','-seg','yes','-comp_based_stats','2','-evalue','.001',
            '-max_target_seqs',str(n),'-num_threads','32','-outfmt','6 qseqid sseqid qlen slen evalue qseq sseq']
        if dbsize is not None:cmd+=['-dbsize',str(dbsize)]
        run(cmd,out.stem)
    if not pool:
        write(r/'search_report.json',dict(complete=True,pool=0,eligible=0));return
    search(r/'candidates.fasta',a.v2/'db',r/'development.tsv',len(refs))
    bad={}
    for h in read_hsps(r/'development.tsv'):
        if h.evidence()['excluded']:bad.setdefault(aliases[h.query],[]).append(dict(subject=aliases[h.subject],**h.evidence()))
    write(r/'exclusions.json',bad)
    run([str(a.bin/'makeblastdb'),'-in',str(r/'pair_panel.fasta'),'-dbtype','prot','-parse_seqids','-out',str(r/'pair_db')],'make_pair_db')
    search(r/'pair_panel.fasta',r/'pair_db',r/'pairs.tsv',len(allrows),sum(len(x['sequence']) for x in refs))
    edges=set()
    for h in read_hsps(r/'pairs.tsv'):
        if h.query!=h.subject and h.evidence()['excluded']:edges.add(tuple(sorted((aliases[h.query],aliases[h.subject]))))
    write(r/'pair_edges.json',sorted(edges))
    eligible=[x for x in pool if x['group_id'] not in bad and not any(tuple(sorted((x['group_id'],s['group_id']))) in edges for s in retained)]
    write(r/'homology_eligible.json',eligible)
    # Source-only materialization. No folding. Chemistry subsequently checks all
    # supported candidates before fixed-order panel assembly.
    data=r/'data';data.mkdir()
    with concurrent.futures.ProcessPoolExecutor(max_workers=16,mp_context=multiprocessing.get_context('fork')) as executor:
        jobs=[executor.submit(materialize,x,b,data) for x in eligible]
        outcomes=[job.result() for job in jobs]
    write(r/'materialization_report.json',outcomes)
    good={x['group_id'] for x in outcomes if x['passed']};ready=[x for x in eligible if x['group_id'] in good]
    write(r/'chemistry_selection.json',ready)
    write(r/'search_report.json',dict(complete=True,pool=len(pool),development_rejected=len(bad),
        homology_eligible=len(eligible),materialized=len(ready),source_lock_sha256=sha(r/'source_lock.json'),folding_started=False))


if __name__=='__main__':main()
