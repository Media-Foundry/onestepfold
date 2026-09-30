#!/usr/bin/env python3
"""Recheck source isolation and identity mapping without model/repair outputs."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
from fastglycan.paired_teacher_protocol import sha256, write_json
from onestepfold.data.gt_materializer import ATOM37_INDEX


def audit_fresh_contact_panel(root):
    lock = json.loads((root/'selection_lock.json').read_text())
    assert lock['complete'] and lock['selected'] == 8
    for name, key in [('selection.json','selection_sha256'), ('preflight.json','preflight_sha256'),
                      ('source_lock.json','source_lock_sha256'), ('data_manifest.json','manifest_sha256')]:
        assert sha256(root/name) == lock[key]
    source = json.loads((root/'source_lock.json').read_text())
    for path, digest in source['source_hashes'].items(): assert sha256(Path(path)) == digest
    manifest = json.loads((root/'data_manifest.json').read_text())
    for name, digest in manifest.items(): assert sha256(root/name) == digest
    base = root.parent; ext = base/'connection_calibration_extension_v1_20260930'
    old = base/'connection_calibration_v1_20260930'
    pool = json.loads((ext/'pool.json').read_text())
    peers = pool + json.loads((old/'selection.json').read_text())
    calibration = json.loads((ext/'selection.json').read_text())
    calibration_ids = {r['group_id'] for r in calibration}
    panel = json.loads((root/'selection.json').read_text()); indices = {r['pool_index'] for r in panel}
    # Independent parsing/formula instead of reusing selection's HSP.evidence().
    hsp_count = 0
    for file in ['references.tsv', 'pairs.tsv']:
        for line in (ext/file).read_text().splitlines():
            q,s,ql,sl,e,qa,sa = line.split('\t'); i,j=int(q[1:]),int(s[1:])
            assert len(qa)==len(sa)
            pairs=[(a,b) for a,b in zip(qa,sa) if a!='-' and b!='-']
            n=len(pairs); hsp_count += 1
            denied=n>=50 and (float(e)<=1e-5 or (float(e)<=.001 and
                n/min(int(ql),int(sl))>=.7 and sum(a==b for a,b in pairs)/n>=.3))
            if not denied or i not in indices: continue
            if file=='references.tsv': raise AssertionError(('historical homolog',q,s))
            if i!=j:
                assert j not in indices and peers[j]['group_id'] not in calibration_ids
    denied_rows = calibration + json.loads((base/'independent32_v2_20260930/panel32.json').read_text()) + json.loads((base/'local_fit_gt_source_v1_20260930/selection.json').read_text())
    pdbs={r['pdb_id'].lower() for r in denied_rows}; accs={a for r in denied_rows for a in r['accessions']}
    rows=[]
    for r in panel:
        assert r['group_id'] not in calibration_ids and r['pdb_id'].lower() not in pdbs
        assert not accs.intersection(r['accessions'])
        assert r['group_id']==pool[r['pool_index']]['group_id']
        g=r['group_id']; packet=root/'chemistry'/g
        chemistry=json.loads((packet/'report.json').read_text()); assert chemistry['passed']
        assert not chemistry['unsupported_source_connections']
        with np.load(packet/'mapping.npz') as m, np.load(root/'data/examples'/g/'gt.npz') as gt:
            ri=m['residue_ids'].astype(int)-1;ai=np.array([ATOM37_INDEX[str(n)] for n in m['atom_names']])
            assert m['mask'].all() and gt['residue_mask'][ri].all() and gt['atom37_mask'][ri,ai].all()
            assert np.array_equal(m['coordinates'],gt['atom37_positions'][ri,ai])
            assert len(set(zip(m['chain_ids'],m['residue_ids'],m['atom_names'])))==len(ri)
        rows.append(dict(pdb_id=r['pdb_id'],group_id=g,length=len(r['sequence']),
            native_atoms=chemistry['atom_count'],assembly_protein_instances=r['source_assembly_composition']['protein_chain_instance_count']))
    for a,b in itertools.combinations(panel,2):
        assert a['pdb_id']!=b['pdb_id'] and not set(a['accessions']).intersection(b['accessions'])
    candidates=json.loads((root/'candidates.json').read_text())
    preflight={r['group_id']:r for r in json.loads((root/'preflight.json').read_text())}
    # This panel has no peer conflicts: first eight fully qualified sources must match.
    expected=[r['group_id'] for r in candidates if preflight[r['group_id']]['passed']][:8]
    assert expected==[r['group_id'] for r in panel]
    write_json(root/'audit.json',dict(verified=True,proteins=len(rows),rows=rows,hsps_reparsed=hsp_count,
        data_files_verified=len(manifest),source_files_verified=len(source['source_hashes']),
        selection_lock_sha256=sha256(root/'selection_lock.json'),script_sha256=sha256(Path(__file__)),
        no_model_or_repair_outputs_read=True))
    print(json.dumps(dict(verified=True,proteins=len(rows),hsps=hsp_count)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    audit_fresh_contact_panel(p.parse_args().root)
