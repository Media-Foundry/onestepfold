#!/usr/bin/env python3
"""Preserve the27 existing records and fill only the five authorized source slots."""
import argparse,hashlib,json
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--previous',type=Path,required=True);a=p.parse_args()
r=a.root;assert not (r/'panel32.json').exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads(a.previous.read_text());assert len(old)==27
new=json.loads((r/'chemistry_selection.json').read_text());preflight=json.loads((r/'chemistry/report.json').read_text());assert preflight['complete']
chem={x['group_id']:x for x in preflight['rows']}
edges={tuple(x) for x in json.loads((r/'pair_edges.json').read_text())};chosen=list(old);rejections=[]
for b,target in [(2,8),(3,8)]:
    for row in new:
        if sum(x['stratum']==b for x in chosen)>=target:break
        g=row['group_id']
        if row['stratum']!=b or not chem[g]['passed']:continue
        conflict=next((x['group_id'] for x in chosen if set(x['accessions']) & set(row['accessions']) or tuple(sorted((g,x['group_id']))) in edges),None)
        if conflict:rejections.append(dict(group_id=g,conflict=conflict));continue
        chosen.append(dict(row,chemistry=dict(chem[g],packet_dir=str(r/'chemistry'/g)),source_data_root=str(r/'data')))
assert chosen[:27]==old
counts=[sum(x['stratum']==b for x in chosen) for b in range(4)]
complete=len(chosen)==32 and counts==[8,8,8,8]
file=r/('panel32.json' if complete else 'incomplete_panel.json')
file.write_text(json.dumps(chosen,indent=2)+'\n')
reserved=[dict(group_id=x['group_id'],sequence=x['sequence'],reason='reserved geometry validation; exclude from future correction training') for x in chosen]
(r/'validation_reservations.json').write_text(json.dumps(reserved,indent=2)+'\n')
(r/'panel_data_lock.json').write_text(json.dumps(dict(complete=complete,proteins=len(chosen),strata_counts=counts,
    retained27_exact=True,added=[dict(group_id=x['group_id'],pdb_id=x['pdb_id'],length=len(x['sequence'])) for x in chosen[27:]],
    peer_rejections=rejections,source_hashes={str(p):sha(p) for p in [a.previous,r/'source_lock.json',r/'search_report.json',r/'chemistry/report.json',r/'pair_edges.json']},
    panel_sha256=sha(file),reservation_sha256=sha(r/'validation_reservations.json'),source_sha256=sha(Path(__file__)),
    folding_started=False,runtime_lock_still_required=True),indent=2)+'\n')
print(complete,counts)
