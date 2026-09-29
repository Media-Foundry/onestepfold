#!/usr/bin/env python3
"""Lock32 after explicit homooligomer-source authorization; no inference."""
import argparse,hashlib,json
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--root',type=Path,required=True);a=p.parse_args();b=a.base;r=a.root;r.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
oldpath=b/'validation_source_extension_v1_1_20260930/incomplete_panel.json';old=json.loads(oldpath.read_text());assert len(old)==28
source=b/'validation_homooligomer_v6_20260930';discovery=b/'validation_full_discovery_v5_20260930'
report=json.loads((source/'report.json').read_text());assert report['complete'];checks={x['group_id']:x for x in report['rows']}
shortlist=json.loads((source/'shortlist.json').read_text());edges={tuple(x) for x in json.loads((discovery/'pair_edges.json').read_text())}
chosen=list(old)
for row in shortlist:
 g=row['group_id']
 if not checks[g]['passed']:continue
 assert row['source_context']['homooligomer'] and not row['source_context']['unsupported_connections']
 assert not any(set(row['accessions'])&set(x['accessions']) or tuple(sorted((g,x['group_id']))) in edges for x in chosen)
 chosen.append(dict(row,split='new_validation_reserved',chemistry=dict(checks[g],packet_dir=str(source/'chemistry'/g)),source_data_root=str(discovery/'variants_data'/row['variant_id'])))
 if len(chosen)==32:break
assert len(chosen)==32 and chosen[:28]==old
assert [sum(x['stratum']==i for x in chosen) for i in range(4)]==[8]*4
artifacts={};contexts={}
for x in chosen:
 g=x['group_id'];chem=x['chemistry'];packet=Path(chem['packet_dir']);data=Path(x.get('source_data_root',str(b/'scratch_structure_data_v1_20260927')))/'examples'/g
 for n,h in chem['files'].items():assert sha(packet/n)==h;artifacts[str(packet/n)]=h
 for n,h in chem['source_hashes'].items():assert sha(data/n)==h;artifacts[str(data/n)]=h
 contexts[g]=dict(origin='homooligomer_chain' if g in checks else 'original_monomer_source',pdb_id=x['pdb_id'],source_context=x.get('source_context'),source_assembly_composition=x.get('source_assembly_composition'))
(r/'panel32.json').write_text(json.dumps(chosen,indent=2)+'\n');(r/'source_contexts.json').write_text(json.dumps(contexts,indent=2)+'\n')
(r/'validation_reservations.json').write_text(json.dumps([dict(group_id=x['group_id'],sequence=x['sequence'],accessions=x['accessions'],reason='reserved independent geometry validation; exclude exact and calibrated-near groups from correction training') for x in chosen],indent=2)+'\n')
lock=dict(complete=True,proteins=32,strata_counts=[8]*4,retained28_exact=True,source_context_counts=dict(original_monomer_source=28,homooligomer_chain=4),user_authorization='允许，优先同源多聚体中的完整单链',added=[dict(pdb_id=x['pdb_id'],length=len(x['sequence']),source_chain=x['source_label_asym_id'],protein_instances=x['source_context']['protein_instances']) for x in chosen[28:]],panel_sha256=sha(r/'panel32.json'),artifact_hashes=artifacts,source_hashes={str(p):sha(p) for p in [oldpath,source/'report.json',source/'shortlist.json',discovery/'pair_edges.json',Path(__file__)]},folding_started=False,runtime_lock_still_required=True)
(r/'data_lock.json').write_text(json.dumps(lock,indent=2)+'\n');print(json.dumps(lock['added']),flush=True)
