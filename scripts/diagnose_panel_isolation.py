#!/usr/bin/env python3
"""Post-screen negative control, descriptive only; never admits candidates."""
import argparse
import hashlib
import json
import random
from pathlib import Path
from onestepfold.data.sequence_identity import _new_homology_aligner, calculate_pairwise_identity

p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True); a = p.parse_args()
root = a.root
refs = {r['group_id']: r for r in json.loads((root/'references.json').read_text())}
pool = {r['group_id']: r for r in json.loads((root/'pool.json').read_text())}
aligner = _new_homology_aligner(); rows = []
for result in sorted(json.loads((root/'homology.json').read_text()), key=lambda r: r['group_id']):
    if result['passed']: continue
    query = pool[result['group_id']]; reference = refs[result['first_near']]
    shuffled = list(reference['sequence'])
    random.Random(int(result['group_id'][:16], 16) ^ 20260929).shuffle(shuffled)
    row = dict(group_id=result['group_id'], reference=result['first_near'], stratum=query['stratum'],
               query_length=len(query['sequence']), reference_length=len(shuffled))
    for name, seq in [('original', reference['sequence']), ('shuffled', ''.join(shuffled))]:
        pair = calculate_pairwise_identity(query['sequence'], seq, aligner=aligner)
        row[name] = dict(identity=pair.residue_identity, coverage=pair.shorter_sequence_coverage,
                         aligned=pair.aligned_residue_count,
                         hit=pair.aligned_residue_count>=50 and pair.residue_identity>=.30 and pair.shorter_sequence_coverage>=.70)
    assert row['original']['hit']
    rows.append(row)
out = root/'null_alignment_diagnostic.json'
assert not out.exists()
out.write_text(json.dumps(dict(scope='post-hoc single-shuffle control; no selection or threshold change',
    original_hits=len(rows), shuffled_hits=sum(r['shuffled']['hit'] for r in rows), rows=rows,
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    screen_report_sha256=hashlib.sha256((root/'screen_report.json').read_bytes()).hexdigest()), indent=2)+'\n')
print(len(rows), sum(r['shuffled']['hit'] for r in rows))
