import json
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256,write_json
from analyze_folding_structure_extent import summarize_structure_extent
r=Path('/data/user/shuang886/Folding/noise_diversity_assessment_v1_20261001_retry1/original')
d=r/'extent';d.mkdir(exist_ok=False)
lock=json.loads((r/'lock.json').read_text());report=json.loads((r/'report.json').read_text());assert report['complete']
rmsd={}
for x in report['records']:rmsd.setdefault(x['group_id'],{}).setdefault(x['model'],{})[str(x['seed'])]=x['ca_aligned_rmsd']
hashes={str(p):sha256(p) for p in [r/'lock.json',r/'report.json',r/'execution.json']};hashes.update(lock['hashes'])
write_json(d/'manifest.json',dict(evaluation_root=str(r),evaluation_lock_sha256=sha256(r/'lock.json'),hashes=hashes,
 example_reports={x['group_id']:sha256(r/'examples'/x['group_id']/'report.json') for x in lock['rows']},rmsd=rmsd,
 diagnostic_candidate='diverse',diagnostic_reference='fixed'))
summarize_structure_extent(d,8)
