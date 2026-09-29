#!/usr/bin/env python3
"""Read-only comparison of runtime, inputs, and weights with their frozen hashes."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
root = args.root
runtime = json.loads((root / 'runtime_lock.json').read_text())
data = json.loads((root / 'data_lock.json').read_text())
expected = {}
sources = {
    'runtime_sources': runtime['source_hashes'],
    'frozen_geometry': runtime['frozen_geometry'],
    'weights': runtime['weights_sha256'],
    'protocol': runtime['protocol_sha256'],
    'scoring_dependency': runtime['scoring_dependency']['files'],
    'native_and_gt_inputs': data['artifact_hashes'],
    'source_audit_code': data['source_hashes'],
    'panel_and_data_lock': {
        str(root / 'panel32.json'): runtime['panel_sha256'],
        str(root / 'data_lock.json'): runtime['data_lock_sha256'],
    },
}
for item in runtime['prepared']:
    sources['prepared_' + item['group_id']] = item['files']
for label, files in sources.items():
    for path, digest in files.items():
        if path in expected:
            assert expected[path] == digest, ('conflicting frozen hashes', path)
        expected[path] = digest

rows = []
for path, digest in sorted(expected.items()):
    row = dict(path=path, expected_sha256=digest)
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as handle:
            for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
                h.update(block)
        row.update(actual_sha256=h.hexdigest(), matched=h.hexdigest() == digest)
    except OSError as error:
        row.update(matched=False, error=str(error))
    rows.append(row)

output = dict(
    observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    complete=all(row['matched'] for row in rows), checked=len(rows),
    mismatches=[row for row in rows if not row['matched']], rows=rows,
    category_counts={label: len(files) for label, files in sources.items()},
    source_pipeline_terminal=(root / 'exit.json').exists(),
    scope='File integrity at the recorded time; not proof of scientific validity or model replay.',
)
args.out.parent.mkdir(parents=True, exist_ok=True)
with args.out.open('x') as handle:
    json.dump(output, handle, indent=2)
    handle.write('\n')
print(json.dumps({key: output[key] for key in ['complete', 'checked', 'mismatches']}))
raise SystemExit(0 if output['complete'] else 1)
