#!/usr/bin/env python3
"""Read-only manifest/FASTA inventory, without decompressing all mmCIF files."""
from pathlib import Path
import json,os,sys
r=Path(sys.argv[1])
manifest=set((r/'manifests/uniprot_accessions_with_pdb.txt').read_text().split())
fastas=sorted((r/'raw/uniprot/2026_03/mapped_fasta').glob('*.fasta'));accessions=[];empty=0;counts=[];headers=[]
for f in fastas:
 count=0;length=None
 for line in f.open():
  if line.startswith('>'):
   if length==0:empty+=1
   token=line[1:].split()[0];accessions.append(token.split('|')[1] if '|' in token else token);count+=1;length=0
   if len(headers)<2:headers.append(line.strip())
  elif length is not None:length+=len(line.strip())
 if length==0:empty+=1
 counts.append(count)
expected=set((r/'manifests/pdb_entry_ids.txt').read_text().lower().split());present=set();sample=[];partial=[]
for folder in (r/'raw/pdb_mmcif').iterdir():
 if not folder.is_dir():continue
 for entry in os.scandir(str(folder)):
  if entry.name.endswith('.cif.gz'):
   present.add(entry.name[:-7].lower())
   if len(sample)<3:sample.append(str(Path(entry.path).relative_to(r)))
  elif '.part' in entry.name:partial.append(entry.path)
print(json.dumps(dict(root=str(r),fasta_files=len(fastas),fasta_records=len(accessions),unique_accessions=len(set(accessions)),empty_records=empty,accession_manifest_exact=set(accessions)==manifest,batch_min=min(counts),batch_max=max(counts),header_examples=headers,pdb_manifest_count=len(expected),pdb_files=len(present),pdb_manifest_exact=present==expected,pdb_path_examples=sample,partial_files=len(partial),sifts_files=sorted(p.name for p in (r/'raw/sifts/2026-09-08').iterdir()),scope='SIFTS-linked subset, not complete UniProt; metadata/FASTA audit, no full gzip recheck'),indent=2))
