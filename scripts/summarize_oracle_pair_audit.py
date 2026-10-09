"""Coordinate-only paired summaries; all conditions and strata retained."""
import argparse,gzip,json
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.reference_editor_metrics import summarize_editor_sites,paired_parent_interval

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root
sites=[];outputs=[];sources={}
for shard in range(6):
    path=root/f'scores_{shard}.json.gz';sources[path.name]=sha256(path)
    with gzip.open(path,'rt') as f: data=json.load(f)
    assert data['complete'];sites.extend(data['sites']);outputs.extend(data['outputs'])
assert len(sites)==144 and len(outputs)==5472
assert len({(r['site_key'],r['arm']) for r in sites})==144
summary={};contrasts={};geometry=[]
for role in sorted({r['role'] for r in sites}):
    summary[role]={};contrasts[role]={}
    for arm in sorted({r['arm'] for r in sites}):
        ss=[r for r in sites if r['role']==role and r['arm']==arm]
        oo=[r for r in outputs if r['role']==role and r['arm']==arm]
        value=summarize_editor_sites(ss,oo)
        for field in ('disabled_pass_to_fail','disabled_fail_to_pass'):value[field]=sum(r[field] for r in oo)
        for field,key in (('severe_pairs','severe_pairs'),('wrong_centres','checked_chirality_wrong')):
            value[field]=sum(r['geometry'][key] for r in oo)
        summary[role][arm]=value
        for parent in sorted({r['parent'] for r in oo}):
            group=[r for r in oo if r['parent']==parent]
            geometry.append(dict(role=role,arm=arm,parent=parent,outputs=len(group),
                passed=sum(r['geometry']['zero_severe_strict_checked_chirality'] for r in group),
                severe_pairs=sum(r['geometry']['severe_pairs'] for r in group),
                wrong_centres=sum(r['geometry']['checked_chirality_wrong'] for r in group),
                new_failures=sum(r['disabled_pass_to_fail'] for r in group),repairs=sum(r['disabled_fail_to_pass'] for r in group)))
    for ref in ('disabled','exact'):
        contrasts[role]['oracle_pair-'+ref]={metric:paired_parent_interval(summary[role]['oracle_pair']['parent_summaries'],summary[role][ref]['parent_summaries'],metric) for metric in ('spearman','regret','centered_response_rmse')}
write_json(root/'summary.json',dict(complete=True,summary=summary,contrasts=contrasts,geometry_by_parent=geometry,
    score_hashes=sources,sites=sites,independent_confirmation=False,promoted=False))
print('SUMMARY_COMPLETE',len(sites),len(outputs),flush=True)
