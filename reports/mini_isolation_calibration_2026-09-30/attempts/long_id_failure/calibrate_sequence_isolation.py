#!/usr/bin/env python3
"""Bounded BLAST calibration, then conditional sequence-only candidate screening."""
import argparse
import csv
import gzip
import hashlib
import itertools
import json
import random
import subprocess
import time
from pathlib import Path

from fastglycan.sequence_isolation import read_hsps
from onestepfold.data.sequence_identity import _new_homology_aligner, calculate_pairwise_identity

BINS = [(50,127),(128,255),(256,511),(512,1024)]
PREFIX = 'isolation-v2:20260930:'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(value):
    return hashlib.sha256((PREFIX+value).encode()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def fasta(path, rows):
    path.write_text(''.join('>'+r['id']+'\n'+r['sequence']+'\n' for r in rows))


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--v1',type=Path,required=True);p.add_argument('--base',type=Path,required=True)
    p.add_argument('--bin',type=Path,required=True);a=p.parse_args()
    root=a.root;root.mkdir(parents=True,exist_ok=True)
    if (root/'lock.json').exists():raise ValueError('locked root already exists')
    refs=json.loads((a.v1/'references.json').read_text());pool=json.loads((a.v1/'pool.json').read_text())
    by_id={r['group_id']:r for r in refs};queries=[];parents=[]
    for lo,hi in BINS:
        parents.extend(sorted((r for r in refs if lo<=len(r['sequence'])<=hi),key=lambda r:key(r['group_id']))[:8])
    assert len(parents)==32
    aa='ACDEFGHIKLMNPQRSTVWY'
    for i,r in enumerate(parents):
        seq=r['sequence'];n=len(seq)
        crop=max(50,int(.8*n));offset=(n-crop)//2
        variants={'exact':seq,'crop':seq[offset:offset+crop]}
        for name,rate in [('mutation20',.2),('mutation60',.6)]:
            rng=random.Random(key(name+r['group_id']));x=list(seq)
            for ix in rng.sample(range(n),int(n*rate)):
                x[ix]=rng.choice(aa.replace(x[ix],''))
            variants[name]=''.join(x)
        for j in range(10):
            x=list(seq);random.Random(key('shuffle'+str(j)+r['group_id'])).shuffle(x)
            variants['shuffle'+str(j)]=''.join(x)
        for name,seq in variants.items():
            queries.append(dict(id=f'p{i:02d}_{name}',kind='shuffle' if name.startswith('shuffle') else name,
                                intended=r['group_id'],sequence=seq))
    # Biological-source positives are not selected from the new candidate pool.
    sifts=a.base/'Dataset/raw/sifts/2026-09-08/pdb_chain_uniprot.csv.gz';accessions={}
    with gzip.open(sifts,'rt') as f:
        for r in csv.DictReader(line for line in f if not line.startswith('#')):
            accessions.setdefault(r['PDB'].lower(),set()).add(r['SP_PRIMARY'])
    selection=a.base/'scratch_structure_data_v1_20260927/selection.json';groups={}
    for r in json.loads(selection.read_text()):
        acc=accessions.get(r['pdb_id'].lower(),set())
        if r['group_id'] in by_id and len(acc)==1 and 50<=len(r['sequence'])<=1024:
            groups.setdefault(next(iter(acc)),[]).append(r)
    aligner=_new_homology_aligner();natural=[]
    for acc in sorted(groups,key=key):
        rows=sorted(groups[acc],key=lambda r:key(r['group_id']))
        for x,y in itertools.combinations(rows,2):
            if min(len(x['sequence']),len(y['sequence']))/max(len(x['sequence']),len(y['sequence']))<.8:continue
            z=calculate_pairwise_identity(x['sequence'],y['sequence'],aligner=aligner)
            if z.residue_identity>=.8 and z.shorter_sequence_coverage>=.9:
                natural.append(dict(id=f'n{len(natural):02d}',kind='natural',intended=y['group_id'],
                    query_group=x['group_id'],accession=acc,sequence=x['sequence']));break
        if len(natural)==32:break
    queries+=natural
    write(root/'queries.json',queries)
    fasta(root/'references.fasta',[dict(id=r['group_id'],sequence=r['sequence']) for r in refs])
    fasta(root/'calibration.fasta',queries)
    executables={name:str((a.bin/name).resolve()) for name in ['blastp','makeblastdb']}
    lock=dict(v1_sources={n:sha(a.v1/n) for n in ['references.json','pool.json','screen_lock.json','screen_report.json']},
        queries_sha256=sha(root/'queries.json'),references_fasta_sha256=sha(root/'references.fasta'),
        source_sha256=sha(Path(__file__)),rule_sha256=sha(Path(__import__('fastglycan.sequence_isolation',fromlist=['x']).__file__)),
        protocol_sha256=sha(root/'code/docs/mini_isolation_calibration_v2.md'),
        sources={str(selection):sha(selection),str(sifts):sha(sifts)},
        tools={name:dict(path=f,sha256=sha(Path(f)),version=subprocess.check_output([f,'-version'],text=True)) for name,f in executables.items()},
        references=len(refs),parents=len(parents),natural_pairs=len(natural),geometry_modified=False)
    write(root/'lock.json',lock);commands=[];start=time.monotonic()
    def run(command,label):
        commands.append(command);write(root/'commands.json',commands)
        with (root/(label+'.log')).open('w') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
    run([executables['makeblastdb'],'-in',str(root/'references.fasta'),'-dbtype','prot','-parse_seqids','-out',str(root/'db')],'make_db')
    def search(query,db,out,count,dbsize=None):
        cmd=[executables['blastp'],'-task','blastp','-query',str(query),'-db',str(db),'-out',str(out),
             '-word_size','3','-matrix','BLOSUM62','-gapopen','11','-gapextend','1','-seg','yes',
             '-comp_based_stats','2','-evalue','.001','-max_target_seqs',str(count),'-num_threads','32',
             '-outfmt','6 qseqid sseqid qlen slen evalue qseq sseq']
        if dbsize is not None:cmd+=['-dbsize',str(dbsize)]
        run(cmd,out.stem)
    search(root/'calibration.fasta',root/'db',root/'calibration.tsv',len(refs))
    hits={}
    for h in read_hsps(root/'calibration.tsv'):
        if h.evidence()['excluded']:hits.setdefault(h.query,set()).add(h.subject)
    calibration=[]
    for q in queries:
        calibration.append(dict(id=q['id'],kind=q['kind'],intended=q['intended'],
            intended_recovered=q['intended'] in hits.get(q['id'],set()),any_exclusion=bool(hits.get(q['id'])),
            excluded_references=sorted(hits.get(q['id'],set()))))
    counts={kind:dict(total=sum(q['kind']==kind for q in calibration),
        recovered=sum(q['kind']==kind and q['intended_recovered'] for q in calibration),
        any_exclusion=sum(q['kind']==kind and q['any_exclusion'] for q in calibration))
        for kind in ['exact','crop','mutation20','mutation60','natural','shuffle']}
    passed=(counts['exact']['recovered']==32 and counts['crop']['recovered']==32 and
            counts['mutation20']['recovered']>=31 and counts['natural']['total']>=16 and
            counts['natural']['recovered']==counts['natural']['total'] and counts['shuffle']['any_exclusion']<=3)
    report=dict(complete=True,passed=passed,counts=counts,rows=calibration,seconds=time.monotonic()-start,
                lock_sha256=sha(root/'lock.json'),tsv_sha256=sha(root/'calibration.tsv'))
    write(root/'calibration_report.json',report);print(json.dumps(dict(passed=passed,counts=counts)),flush=True)
    if not passed:return
    fasta(root/'candidates.fasta',[dict(id=r['group_id'],sequence=r['sequence']) for r in pool])
    search(root/'candidates.fasta',root/'db',root/'candidates.tsv',len(refs))
    rejected={}
    for h in read_hsps(root/'candidates.tsv'):
        if h.evidence()['excluded']:rejected.setdefault(h.query,[]).append(dict(subject=h.subject,**h.evidence()))
    run([executables['makeblastdb'],'-in',str(root/'candidates.fasta'),'-dbtype','prot','-parse_seqids','-out',str(root/'candidate_db')],'make_candidate_db')
    # Fix E-value database length to the development reference size for comparable
    # decisions rather than making small-panel matches artificially significant.
    search(root/'candidates.fasta',root/'candidate_db',root/'pairs.tsv',len(pool),sum(len(r['sequence']) for r in refs))
    edges=set()
    for h in read_hsps(root/'pairs.tsv'):
        if h.query!=h.subject and h.evidence()['excluded']:edges.add(tuple(sorted((h.query,h.subject))))
    chosen=[];pair_rejected=[]
    for b in range(4):
        count=0
        for r in (r for r in pool if r['stratum']==b and r['group_id'] not in rejected):
            conflict=next((s['group_id'] for s in chosen if set(s['accessions']) & set(r['accessions']) or
                tuple(sorted((s['group_id'],r['group_id']))) in edges),None)
            if conflict:pair_rejected.append(dict(group_id=r['group_id'],conflict=conflict));continue
            chosen.append(r);count+=1
            if count==8:break
    write(root/'candidate_exclusions.json',rejected);write(root/'selection_provisional.json',chosen)
    write(root/'selection_report.json',dict(complete=True,panel_size_satisfied=len(chosen)==32,
        pool=len(pool),excluded_against_development=len(rejected),selected=len(chosen),
        strata_counts=[sum(r['stratum']==b for r in chosen) for b in range(4)],pair_rejected=pair_rejected,
        pair_edges=sorted(edges),seconds=time.monotonic()-start,calibration_sha256=sha(root/'calibration_report.json'),
        selection_sha256=sha(root/'selection_provisional.json'),gpu_inference_started=False,
        status='native chemical preflight and separate immutable inference lock still required'))


if __name__=='__main__':main()
