#!/usr/bin/env python3
"""CPU metadata census of complete-looking long chains in the full PDB catalog.

Compatible with HPC3's Python3.6; no coordinate reads, inference or panel admission.
"""
import argparse,collections,concurrent.futures,csv,gzip,hashlib,json
from pathlib import Path

AA3=set('ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TRP TYR VAL'.split())
DENIED_GROUPS=set();DENIED_PDB=set();DENIED_ACC=set();ACCESSIONS={}


def scan_shard(path):
    rows=[];counts=collections.Counter()
    with gzip.open(str(path),'rt') as f:
        for line in f:
            x=json.loads(line);counts['catalog_entries']+=1;e=x['experimental'];pdb=x['pdb_id'].lower()
            if not e.get('initial_release_date') or e['initial_release_date']>'2021-09-30':continue
            counts['precutoff_entries']+=1
            if pdb in DENIED_PDB or e.get('model_count')!=1:continue
            if not set(e.get('methods',[])) & {'X-RAY DIFFRACTION','ELECTRON MICROSCOPY','NEUTRON DIFFRACTION'}:continue
            acc=ACCESSIONS.get(pdb,set())
            if not acc or acc&DENIED_ACC:continue
            comps={c['assembly_id']:c for c in x['assembly_compositions']}
            for chain in x['chains']:
                seq=chain.get('sequence','');n=len(seq);g=hashlib.sha256(seq.encode()).hexdigest()
                if not chain.get('is_protein') or not 512<=n<=1024 or not set(seq)<=set('ACDEFGHIKLMNPQRSTVWY'):continue
                counts['eligible_length_chains']+=1
                if g in DENIED_GROUPS:continue
                if chain.get('observed_residue_count')!=n:counts['incomplete_residue_metadata']+=1;continue
                if not set(chain.get('observed_comp_ids',[]))<=AA3:counts['nonstandard_observed_comp']+=1;continue
                source=chain['source_label_asym_id'];assemblies=[]
                for assembly in x['assemblies']:
                    if not assembly.get('author_determined'):continue
                    c=comps.get(assembly['assembly_id'],{})
                    if source not in c.get('source_asym_ids',[]):continue
                    assemblies.append(dict(assembly_id=assembly['assembly_id'],assembly_definition_source=assembly['definition_source'],composition=c))
                if not assemblies:counts['no_author_assembly']+=1;continue
                # Discovery only; preserve every author assembly and source context.
                rows.append(dict(group_id=g,pdb_id=pdb,source_label_asym_id=source,entity_id=chain['entity_id'],sequence=seq,sequence_length=n,
                    initial_release_date=e['initial_release_date'],experimental_methods=e['methods'],model_count=e['model_count'],resolution_high_angstrom=e.get('resolution_high_angstrom'),accessions=sorted(acc),assemblies=assemblies,
                    catalog_observed_residue_count=chain['observed_residue_count'],catalog_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return rows,dict(counts)


def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root;b=a.base
    global DENIED_GROUPS,DENIED_PDB,DENIED_ACC,ACCESSIONS
    old=json.loads((r/'screen_lock.json').read_text());refs=json.loads((r/'references.json').read_text());retained=json.loads((r/'retained28.json').read_text())
    DENIED_GROUPS={x['group_id'] for x in refs+retained};DENIED_PDB=set(old['excluded_pdbs']);DENIED_ACC=set(old['excluded_accessions'])
    for x in retained:DENIED_ACC.update(x['accessions'])
    sifts=b/'Dataset/raw/sifts/2026-09-08/pdb_chain_uniprot.csv.gz'
    with gzip.open(str(sifts),'rt') as f:
        for x in csv.DictReader(line for line in f if not line.startswith('#')):ACCESSIONS.setdefault(x['PDB'].lower(),set()).add(x['SP_PRIMARY'])
    paths=sorted((b/'catalog_v1').glob('shard-*.jsonl.gz'));assert len(paths)==256
    rows=[];counts=collections.Counter()
    with concurrent.futures.ProcessPoolExecutor(max_workers=16) as ex:
        for local,c in ex.map(scan_shard,paths):rows.extend(local);counts.update(c)
    rows.sort(key=lambda x:(x['group_id'],x['resolution_high_angstrom'] or float('inf'),x['pdb_id'],x['source_label_asym_id']))
    (r/'full_chain_candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
    summary=dict(counts=dict(counts),candidate_chains=len(rows),candidate_groups=len({x['group_id'] for x in rows}),candidate_pdbs=len({x['pdb_id'] for x in rows}),scope='metadata only; full backbone, chemistry, homology NOT yet certified; no panel admission',source_hashes={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths+[sifts,r/'screen_lock.json',r/'references.json',r/'retained28.json',Path(__file__)]})
    (r/'census.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='source_hashes'}),flush=True)


if __name__=='__main__':main()
