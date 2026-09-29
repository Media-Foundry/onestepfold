#!/usr/bin/env python3
"""All source variants under unchanged monomer/isolation/chemistry requirements."""
import argparse,collections,concurrent.futures,csv,gzip,hashlib,json,multiprocessing,subprocess
from pathlib import Path
from extend_raw_validation_sources import materialize,sha,write,jsonl
from fastglycan.sequence_isolation import read_hsps


def search_variants():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--base',type=Path,required=True)
    a=p.parse_args();r=a.root;b=a.base;r.mkdir(exist_ok=True);assert not (r/'source_lock.json').exists()
    v1=b/'anchored_independent_v1_20260929';v2=b/'isolation_calibration_v2_1_20260930'
    prior=b/'validation_source_extension_v1_1_20260930/incomplete_panel.json'
    old=json.loads((v1/'screen_lock.json').read_text());refs=json.loads((v1/'references.json').read_text());retained=json.loads(prior.read_text());assert len(retained)==28
    denied={x['group_id'] for x in refs+retained};denied_pdb=set(old['excluded_pdbs']);denied_acc=set(old['excluded_accessions'])
    for x in retained:denied_acc.update(x['accessions'])
    sifts=b/'Dataset/raw/sifts/2026-09-08/pdb_chain_uniprot.csv.gz';acc={}
    with gzip.open(sifts,'rt') as f:
        for x in csv.DictReader(line for line in f if not line.startswith('#')):acc.setdefault(x['PDB'].lower(),set()).add(x['SP_PRIMARY'])
    catalog=b/'catalog_v1/monomer_candidates.jsonl.gz';groups=collections.defaultdict(list);seen=set()
    for row in jsonl(catalog):
        seq=row['sequence'];g=hashlib.sha256(seq.encode()).hexdigest();pdb=row['pdb_id'].lower()
        if not row.get('initial_release_date') or row['initial_release_date']>'2021-09-30' or not 512<=len(seq)<=1024:continue
        if g in denied or pdb in denied_pdb or not acc.get(pdb) or acc[pdb]&denied_acc:continue
        if (not set(seq)<=set('ACDEFGHIKLMNPQRSTVWY') or row.get('model_count')!=1
            or not {'X-RAY DIFFRACTION','ELECTRON MICROSCOPY','NEUTRON DIFFRACTION'}.intersection(row.get('experimental_methods',[]))
            or row.get('assembly_definition_source') not in {'author_determined','author_and_software'}):continue
        key=(pdb,row['source_label_asym_id'],row['assembly_id']);assert key not in seen;seen.add(key)
        variant=hashlib.sha256(json.dumps(key).encode()).hexdigest()[:24]
        groups[g].append(dict(row,pdb_id=pdb,group_id=g,sequence_sha256=g,stratum=3,split='new_validation_reserved',accessions=sorted(acc[pdb]),variant_id=variant))
    gids=sorted(groups,key=lambda g:hashlib.sha256(('anchored-variants-v4:20260930:'+g).encode()).hexdigest())
    for g in gids:groups[g].sort(key=lambda x:(x.get('resolution_high_angstrom') or float('inf'),x['pdb_id'],x['source_label_asym_id'],x['assembly_id']))
    variants=[x for g in gids for x in groups[g]];queries=[groups[g][0] for g in gids]
    write(r/'variants.json',variants);write(r/'pool.json',queries)
    write(r/'source_lock.json',dict(groups=len(gids),records=len(variants),source_hashes={str(f):sha(f) for f in [catalog,sifts,v1/'screen_lock.json',v1/'references.json',prior,r/'variants.json',r/'code/docs/mini_validation_structure_variants_v4.md',Path(__file__)]},folding_started=False))
    print('groups,variants',len(gids),len(variants),flush=True)
    allrows=queries+retained;aliases={x['group_id'][:32]:x['group_id'] for x in refs+allrows};assert len(aliases)==len({x['group_id'] for x in refs+allrows});write(r/'aliases.json',aliases)
    def fasta(path,rows):path.write_text(''.join('>'+x['group_id'][:32]+'\n'+x['sequence']+'\n' for x in rows))
    fasta(r/'queries.fasta',queries);fasta(r/'peers.fasta',allrows)
    binary=b/'tools/blast_2.17.0/ncbi-blast-2.17.0+/bin';commands=[]
    def run(cmd,label):
        commands.append(cmd);write(r/'commands.json',commands)
        with (r/(label+'.log')).open('w') as f:subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT)
    def search(query,db,out,n,dbsize=None):
        cmd=[str(binary/'blastp'),'-task','blastp','-query',str(query),'-db',str(db),'-out',str(out),'-word_size','3','-matrix','BLOSUM62','-gapopen','11','-gapextend','1','-seg','yes','-comp_based_stats','2','-evalue','.001','-max_target_seqs',str(n),'-num_threads','32','-outfmt','6 qseqid sseqid qlen slen evalue qseq sseq']
        if dbsize is not None:cmd+=['-dbsize',str(dbsize)]
        run(cmd,out.stem)
    search(r/'queries.fasta',v2/'db',r/'development.tsv',len(refs));bad={aliases[h.query] for h in read_hsps(r/'development.tsv') if h.evidence()['excluded']}
    run([str(binary/'makeblastdb'),'-in',str(r/'peers.fasta'),'-dbtype','prot','-parse_seqids','-out',str(r/'peer_db')],'make_peer_db')
    search(r/'peers.fasta',r/'peer_db',r/'pairs.tsv',len(allrows),sum(len(x['sequence']) for x in refs))
    edges={tuple(sorted((aliases[h.query],aliases[h.subject]))) for h in read_hsps(r/'pairs.tsv') if h.query!=h.subject and h.evidence()['excluded']};write(r/'pair_edges.json',sorted(edges))
    eligible={g for g in gids if g not in bad and not any(tuple(sorted((g,x['group_id']))) in edges for x in retained)}
    candidates=[x for x in variants if x['group_id'] in eligible];write(r/'homology_eligible_variants.json',candidates)
    with concurrent.futures.ProcessPoolExecutor(max_workers=32,mp_context=multiprocessing.get_context('fork')) as ex:
        jobs=[ex.submit(materialize,x,b,r/'variants_data'/x['variant_id']) for x in candidates]
        outcomes=[dict(j.result(),variant_id=x['variant_id'],pdb_id=x['pdb_id'],length=len(x['sequence'])) for j,x in zip(jobs,candidates)]
    write(r/'materialization_report.json',outcomes)
    passed={x['variant_id'] for x in outcomes if x['passed']};ready=[x for x in candidates if x['variant_id'] in passed]
    write(r/'chemistry_candidates.json',ready)
    write(r/'search_report.json',dict(complete=True,groups=len(gids),variants=len(variants),isolated_groups=len(eligible),isolated_variants=len(candidates),source_passed_variants=len(ready),source_passed_groups=len({x['group_id'] for x in ready}),folding_started=False))
    print(json.dumps(json.loads((r/'search_report.json').read_text())),flush=True)


if __name__=='__main__':search_variants()
